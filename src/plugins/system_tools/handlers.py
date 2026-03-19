from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from src.core.plugin import Plugin
from src.core.messenger import Messenger


def _is_self(messenger: Messenger) -> bool:
    return messenger.user_id == messenger.self_id


async def _build_nodes_from_forward(plugin: Plugin, forward_id: int) -> List[Dict[str, Any]]:
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

        if isinstance(content, str):
            m = re.search(r"\[CQ:forward,id=(\d+)\]", content)
            if m:
                nested_nodes = await _build_nodes_from_forward(plugin, int(m.group(1)))
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
                "content": content,
            },
        })
    return nodes


def register(plugin: Plugin) -> None:
    sender = plugin.get_sender()

    @plugin.on_msg(r"^/help$")
    async def _(messenger, matches):
        if _is_self(messenger):
            return
        menu = (
            "指令菜单：\n"
            "/help  查看帮助\n"
            "/ping  查看 WebSocket 延迟\n"
            "/status 查看 NapCatQQ 版本与 WS 延迟\n"
            "点歌+歌名  搜索歌曲\n",
            "选歌/我听+序号  选择歌曲\n",
            "可用节点 / 获取可用节点  查看可用音乐节点\n"
            "更改节点1 / 使用节点1  切换到指定音乐节点\n"
            "更改默认节点2 / 使用默认节点2  设置全局默认音乐节点\n"
            "获取消息体  回复一条消息(可带@)发送后获得该消息的原消息体"
        )
        await sender.reply(messenger, menu)

    @plugin.on_msg(r"^/ping$")
    async def _(messenger, matches):
        if _is_self(messenger):
            return
        latency = await plugin.check_latency()
        msg = f"WebSocket 延迟：{latency} ms" if latency >= 0 else "当前未连接，无法获取延迟"
        await sender.reply(messenger, msg)

    @plugin.on_msg(r"^/status$")
    async def _(messenger, matches):
        if _is_self(messenger):
            return
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
        message_id = int(matches.group(1))
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
                    if seg_type == "forward":
                        forward_id = seg.get("data", {}).get("id")
                        break
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
                nodes = await _build_nodes_from_forward(plugin, forward_id)
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
                    },
                }]

            if messenger.type.value == "group" and messenger.group_id:
                await plugin.api.send_group_forward_msg(messenger.group_id, nodes)
            elif messenger.type.value == "private" and messenger.user_id:
                await plugin.api.send_private_forward_msg(messenger.user_id, nodes)
            else:
                await sender.reply(messenger, "无法确定消息类型，发送失败")
        except Exception as e:
            await sender.reply(messenger, f"获取消息体失败：{e}")

    @plugin.on_msg(r"\[CQ:reply,id=(\d+).*?\].*撤回")
    async def _(messenger, matches):
        if _is_self(messenger):
            return
        target_id = int(matches.group(1))

        async def _bot_is_admin() -> bool:
            if messenger.group_id is None or messenger.self_id is None:
                return False
            try:
                resp = await plugin.api.get_group_member_info(messenger.group_id, messenger.self_id)
                if isinstance(resp, dict) and resp.get("retcode", 0) == 0:
                    data = resp.get("data", {}) if isinstance(resp.get("data"), dict) else {}
                    role = data.get("role", "")
                    return role in ("owner", "admin")
            except Exception:
                return False
            return False

        try:
            msg_resp = await plugin.api.get_msg(target_id)
            msg_data = msg_resp.get("data", {}) if isinstance(msg_resp, dict) else {}
            target_sender = msg_data.get("sender", {}) if isinstance(msg_data, dict) else {}
            target_user_id = target_sender.get("user_id")
            is_self_msg = messenger.self_id is not None and target_user_id == messenger.self_id

            if messenger.group_id is None:
                allowed = is_self_msg
            else:
                allowed = is_self_msg or await _bot_is_admin()

            if not allowed:
                await sender.reply(messenger, "无权限撤回该消息")
                return

            await plugin.api.delete_msg(target_id)
        except Exception as e:
            await sender.reply(messenger, f"撤回失败：{e}")
