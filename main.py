import asyncio
import signal
import json
import re
import os
import tempfile
import posixpath
from urllib.request import urlopen
from urllib.parse import urlparse

from ftpretty import ftpretty

from src.core import Plugin
from src.plugin_system import setup_plugins

WS_URL = "ws://jp.5.frp.one:40760"
ACCESS_TOKEN = "NightMareMoon"

plugin = Plugin(url=WS_URL, token=ACCESS_TOKEN, debug=True)
setup_plugins(plugin)

FTP_HOST = "38.76.204.119"
FTP_USER = "9ws7h3xr"
FTP_PASS = "pMA0JAka"


def _is_self(messenger) -> bool:
    return messenger.user_id == messenger.self_id




def _extract_file_segments(message_segments):
    if not isinstance(message_segments, list):
        return []
    targets = []
    for seg in message_segments:
        if not isinstance(seg, dict):
            continue
        seg_type = seg.get("type")
        if seg_type not in ("file", "video", "record"):
            continue
        data = seg.get("data", {}) if isinstance(seg.get("data"), dict) else {}
        file_id = data.get("file_id") or data.get("id")
        file_name = data.get("file") or data.get("name")
        targets.append({
            "type": seg_type,
            "file_id": file_id,
            "file_name": file_name,
        })
    return targets


async def _fetch_local_file(file_id, fallback_name: str):
    if not file_id:
        return None, "缺少 file_id"
    if isinstance(file_id, str) and os.path.exists(file_id):
        return file_id, None
    file_id_str = str(file_id)
    resp = await plugin.api.get_file(file_id_str)
    if isinstance(resp, dict) and resp.get("retcode", 0) != 0 and file_id_str.startswith("/"):
        resp = await plugin.api.get_file(file_id_str.lstrip("/"))
    if isinstance(resp, dict) and resp.get("retcode", 0) != 0:
        return None, f"get_file retcode={resp.get('retcode')}"
    data = resp.get("data", {}) if isinstance(resp, dict) else {}
    file_path = data.get("file") or data.get("path") or data.get("file_path")
    if file_path and os.path.exists(file_path):
        return file_path, None
    if file_path and not os.path.exists(file_path):
        file_url_resp = await plugin.api.get_file_url(file_id_str)
        if isinstance(file_url_resp, dict) and file_url_resp.get("retcode", 0) == 0:
            file_url_data = file_url_resp.get("data", {}) if isinstance(file_url_resp, dict) else {}
            url = file_url_data.get("url")
            if url:
                return await _download_from_url(url, fallback_name)
        if file_id_str.startswith("/"):
            file_url_resp = await plugin.api.get_file_url(file_id_str.lstrip("/"))
            if isinstance(file_url_resp, dict) and file_url_resp.get("retcode", 0) == 0:
                file_url_data = file_url_resp.get("data", {}) if isinstance(file_url_resp, dict) else {}
                url = file_url_data.get("url")
                if url:
                    return await _download_from_url(url, fallback_name)
        return None, f"file_path 不存在: {file_path}"
    url = data.get("url")
    if url:
        return await _download_from_url(url, fallback_name)
    return None, "get_file 未返回路径或 url"


async def _download_from_url(url: str, fallback_name: str):
    parsed = urlparse(url)
    if parsed.scheme in ("", "file"):
        local_candidate = parsed.path if parsed.scheme == "file" else url
        if os.path.exists(local_candidate):
            return local_candidate, None
        return None, f"本地路径不存在: {local_candidate}"
    if len(parsed.scheme) == 1 and url[1:3] in (":\\", ":/"):
        if os.path.exists(url):
            return url, None
        return None, "本地路径不存在"
    if parsed.scheme not in ("http", "https"):
        return None, f"不支持的 url scheme: {parsed.scheme}"
    suffix = ""
    if fallback_name and "." in fallback_name:
        suffix = "." + fallback_name.split(".")[-1]
    fd, tmp_path = tempfile.mkstemp(prefix="sncq_", suffix=suffix)
    os.close(fd)
    def _download():
        with urlopen(url, timeout=20) as resp_obj, open(tmp_path, "wb") as f:
            f.write(resp_obj.read())
    await asyncio.to_thread(_download)
    if os.path.exists(tmp_path):
        return tmp_path, None
    return None, "下载失败"


FTP_REMOTE_DIR = "/public/static"


async def _upload_file_to_ftp(local_path: str, remote_name: str) -> str:
    remote_path = posixpath.join(FTP_REMOTE_DIR.rstrip("/"), remote_name)
    def _do_upload():
        ftp = ftpretty(FTP_HOST, FTP_USER, FTP_PASS)
        try:
            ftp.put(local_path, remote_path)
        finally:
            try:
                ftp.close()
            except Exception:
                pass
    await asyncio.to_thread(_do_upload)
    return remote_path


async def _upload_segments_to_ftp(message_id: int, message_segments):
    uploads = []
    for idx, seg in enumerate(_extract_file_segments(message_segments), start=1):
        file_id = seg.get("file_id")
        file_name = seg.get("file_name") or f"file_{idx}"
        local_path, reason = await _fetch_local_file(file_id, file_name)
        if not local_path:
            detail = f"（{reason}）" if reason else ""
            uploads.append(f"{file_name}: 获取本地文件失败{detail}")
            continue
        safe_name = os.path.basename(file_name)
        remote_name = f"{message_id}_{idx}_{safe_name}"
        try:
            remote_path = await _upload_file_to_ftp(local_path, remote_name)
            public_path = remote_path.replace("/public/static/", "").lstrip("/")
            uploads.append(
                f"{file_name}: 上传成功 -> {public_path}\n"
                f"访问地址：https://nightmare.rsuo.xyz/static/{public_path}"
            )
        except Exception as e:
            uploads.append(f"{file_name}: 上传失败 ({e})")
    return uploads


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
                uploads = []
                if isinstance(content, dict):
                    uploads = await _upload_segments_to_ftp(
                        content.get("message_id", 0) or forward_id,
                        content.get("message"),
                    )
                content = json.dumps(content, ensure_ascii=False, indent=2)
                if uploads:
                    content += "\n\n附件上传结果：\n" + "\n".join(uploads)

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
            uploads = await _upload_segments_to_ftp(message_id, data.get("message"))
            content = json.dumps(data, ensure_ascii=False, indent=2)
            if uploads:
                content += "\n\n附件上传结果：\n" + "\n".join(uploads)
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
