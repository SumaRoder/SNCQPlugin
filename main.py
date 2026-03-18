import asyncio
import signal
import json
import re
import os
import tomllib

from src.core import Plugin
from src.plugin_system import setup_plugins

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config", "server.toml")


def _load_server_config():
    if not os.path.exists(_CONFIG_PATH):
        raise FileNotFoundError(f"配置文件不存在: {_CONFIG_PATH}")
    with open(_CONFIG_PATH, "rb") as f:
        config_data = f.read().strip()
    if not config_data:
        raise ValueError(f"配置文件为空: {_CONFIG_PATH}")
    config = tomllib.loads(config_data.decode("utf-8"))
    ws_url = config.get("ws_url")
    access_token = config.get("access_token")
    if not ws_url:
        raise ValueError("config/server.toml 缺少 ws_url")
    return ws_url, access_token or ""


WS_URL, ACCESS_TOKEN = _load_server_config()

plugin = Plugin(url=WS_URL, token=ACCESS_TOKEN, debug=True)
setup_plugins(plugin)

def _is_self(messenger) -> bool:
    return messenger.user_id == messenger.self_id


@plugin.on_msg(r"^/help$")
async def _(messenger, matches):
    if _is_self(messenger):
        return
    menu = (
        "指令菜单：\n"
        "/help  查看帮助\n"
        "/ping  查看 WebSocket 延迟\n"
        "/status 查看 NapCatQQ 版本与 WS 延迟\n"
        "可用节点 / 获取可用节点  查看可用音乐节点\n"
        "更改节点1 / 使用节点1  切换到指定节点\n"
        "更改默认节点2 / 使用默认节点2  设置全局默认节点"
    )
    sender = plugin.get_sender()
    await sender.reply(messenger, menu)


@plugin.on_msg(r"^/ping$")
async def _(messenger, matches):
    if _is_self(messenger):
        return
    latency = await plugin.check_latency()
    msg = f"WebSocket 延迟：{latency} ms" if latency >= 0 else "当前未连接，无法获取延迟"
    sender = plugin.get_sender()
    await sender.reply(messenger, msg)


@plugin.on_msg(r"^/status$")
async def _(messenger, matches):
    if _is_self(messenger):
        return
    sender = plugin.get_sender()
    latency = await plugin.check_latency()
    latency_text = f"{latency} ms" if latency >= 0 else "未知"
    try:
        version_resp = await plugin.api.get_version_info()
        version_data = version_resp.get("data", {}) if isinstance(version_resp, dict) else {}
        app_name = version_data.get("app_name", "NapCatQQ")
        app_version = version_data.get("app_version") or version_data.get("version") or "未知"
        protocol_version = version_data.get("protocol_version", "未知")
        status = (
            f"{app_name} 版本：{app_version}\n"
            f"协议版本：{protocol_version}\n"
            f"WebSocket 延迟：{latency_text}"
        )
    except Exception:
        status = f"获取版本信息失败\nWebSocket 延迟：{latency_text}"
    await sender.reply(messenger, status)



@plugin.on_msg(r"\[CQ:reply,id=(\d+).*?\].*获取消息体")
async def _(messenger, matches):
    if _is_self(messenger):
        return

    sender = plugin.get_sender()
    message_id = int(matches.group(1))

    async def build_nodes_from_forward(forward_id):
        resp = await plugin.api.get_forward_msg(forward_id)
        if isinstance(resp, dict) and resp.get("retcode", 0) != 0:
            raise ValueError(f"get_forward_msg failed: retcode={resp.get('retcode')}")
        data = resp.get("data", {}) if isinstance(resp, dict) else {}
        messages = data.get("messages", []) if isinstance(data, dict) else []
        nodes = []
        for msg in messages:
            node_data = msg.get("data", msg) if isinstance(msg, dict) else {}
            name = node_data.get("name", "未知")
            uin = node_data.get("uin", 0)
            content = node_data

            # 如果内容里仍包含合并转发，递归展开
            if isinstance(content, str):
                m = re.search(r"\[CQ:forward,id=(\d+)\]", content)
                if m:
                    nested_nodes = await build_nodes_from_forward(int(m.group(1)))
                    nodes.extend(nested_nodes)
                    continue
            elif isinstance(content, (dict, list)):
                content.pop("raw_message", None)
                content = json.dumps(content, ensure_ascii=False, indent=2)

            nodes.append({
                "type": "node",
                "data": {
                    "name": name,
                    "uin": uin,
                    "content": content
                }
            })
        return nodes

    try:
        resp = await plugin.api.get_msg(message_id)
        data = resp.get("data", {}) if isinstance(resp, dict) else {}
        forward_id = None
        message_segments = data.get("message")
        if isinstance(message_segments, list):
            for seg in message_segments:
                if not isinstance(seg, dict):
                    continue
                seg_type = seg.get("type")
                # 常规 forward 段
                if seg_type == "forward":
                    forward_id = seg.get("data", {}).get("id")
                    break
                # NapCat 合并转发通常是 json 段，app=com.tencent.multimsg
                if seg_type == "json":
                    raw_json = seg.get("data", {}).get("data")
                    if isinstance(raw_json, str):
                        try:
                            parsed = json.loads(raw_json)
                            if parsed.get("app") == "com.tencent.multimsg":
                                forward_id = data.get("message_id")
                        except Exception:
                            pass
        
        if forward_id:
            nodes = await build_nodes_from_forward(forward_id)
        else:
            original_sender = data.get("sender", {}) or {}
            nickname = original_sender.get("nickname") or str(original_sender.get("user_id", "未知"))
            uin = original_sender.get("user_id") or 0
            data.pop("raw_message", None)
            content = json.dumps(data, ensure_ascii=False, indent=2)
            nodes = [{
                "type": "node",
                "data": {
                    "name": nickname,
                    "uin": uin,
                    "content": content,
                }
            }]

        if messenger.type.value == "group" and messenger.group_id:
            await plugin.api.send_group_forward_msg(messenger.group_id, nodes)
        elif messenger.type.value == "private" and messenger.user_id:
            await plugin.api.send_private_forward_msg(messenger.user_id, nodes)
        else:
            await sender.reply(messenger, "无法确定消息类型，发送失败")
    except Exception as e:
        await sender.reply(messenger, f"获取消息体失败：{e}")


async def main():
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _stop(*_):
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _stop)
        except NotImplementedError:
            pass

    run_task = asyncio.create_task(plugin.run())
    def _consume_task_result(task: asyncio.Task):
        try:
            task.result()
        except SystemExit:
            pass
        except asyncio.CancelledError:
            pass
        except Exception:
            pass
    run_task.add_done_callback(_consume_task_result)
    await stop_event.wait()
    await plugin.stop()
    run_task.cancel()
    try:
        await run_task
    except asyncio.CancelledError:
        pass


if __name__ == "__main__":
    asyncio.run(main())
