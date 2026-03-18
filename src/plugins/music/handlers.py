from __future__ import annotations

from src.core.messenger import Messenger, MessengerBuilder
from src.core.plugin import Plugin

from .node import (
    MusicNodeRegistry,
    load_music_state,
    save_music_state,
    load_preferred_node_id,
    save_preferred_node_id,
    load_global_default_node_id,
    save_global_default_node_id,
)


def _is_self(messenger: Messenger) -> bool:
    return messenger.user_id == messenger.self_id


def _resolve_user_node(messenger: Messenger, registry: MusicNodeRegistry):
    preferred_id = load_preferred_node_id(messenger.group_id, messenger.user_id)
    if preferred_id is not None:
        node = registry.get_node(preferred_id)
        if node:
            return node
    global_default_id = load_global_default_node_id()
    if global_default_id is not None:
        node = registry.get_node(global_default_id)
        if node:
            return node
    return registry.default_node()


def register(plugin: Plugin) -> None:
    sender = plugin.get_sender()
    registry = MusicNodeRegistry()

    @plugin.on_msg(r"点歌\s*(.+)")
    async def music_search(messenger, matches):
        if _is_self(messenger):
            return
        keyword = matches.group(1).strip()
        if not keyword:
            await sender.reply(messenger, "请提供歌曲名称，例如：点歌 稻香")
            return
        node = _resolve_user_node(messenger, registry)
        if not node:
            await sender.reply(messenger, "未配置音乐节点，请检查 config/music_nodes/ 目录")
            return
        try:
            items = await node.search_music_list(keyword)
        except Exception as e:
            await sender.reply(messenger, f"搜索歌曲失败：{e}")
            return
        if not items:
            await sender.reply(messenger, f"未找到与“{keyword}”相关的歌曲")
            return
        lines = []
        for idx, item in enumerate(items[:10], start=1):
            singers = ", ".join(item.singers) if item.singers else "未知"
            lines.append(f"{idx}. {item.name} - {singers}")
        msg = "搜索结果：\n" + "\n".join(lines) + "\n发送 选歌 1 / 我听 1 进行播放"
        save_music_state(
            messenger.group_id,
            messenger.user_id,
            {"node_id": int(node.node_id), "last_query": keyword, "list_count": len(items)},
        )
        await sender.reply(messenger, msg)

    @plugin.on_msg(r"(选歌|我听\s*#?)\s*(\d+)")
    async def music_pick(messenger, matches):
        if _is_self(messenger):
            return
        index = int(matches.group(2))
        state = load_music_state(messenger.group_id, messenger.user_id)
        if not state or "last_query" not in state:
            await sender.reply(messenger, "请先使用“点歌 歌名”搜索歌曲")
            return
        node_id = state.get("node_id")
        if not isinstance(node_id, int):
            await sender.reply(messenger, "音乐节点配置异常，请重新点歌")
            return
        node = registry.get_node(node_id)
        if not node:
            await sender.reply(messenger, "音乐节点未找到，请检查配置")
            return
        try:
            detail = await node.get_music_info(state["last_query"], index)
        except Exception as e:
            await sender.reply(messenger, f"获取歌曲信息失败：{e}")
            return
        builder = MessengerBuilder()
        jump_url = detail.jump_url or ""
        source_url = detail.source_url or ""
        music_id = detail.id or ""
        if detail.name and source_url and jump_url:
            builder.music(
                "163",
                url=str(jump_url),
                audio=str(source_url),
                title=str(detail.name),
                content=", ".join(detail.singers),
                image=str(detail.picture_url or ""),
                music_id=music_id,
            )
        else:
            singers = ", ".join(detail.singers) if detail.singers else "未知"
            extra = f"\n播放地址：{jump_url}" if jump_url else ""
            await sender.reply(messenger, f"歌曲：{detail.name}\n歌手：{singers}{extra}")
            return
        await sender.reply(messenger, builder)

    @plugin.on_msg(r"(获取)?可用节点")
    async def list_nodes(messenger, matches):
        if _is_self(messenger):
            return
        nodes = registry.nodes
        if not nodes:
            await sender.reply(messenger, "未配置音乐节点，请检查 config/music_nodes/ 目录")
            return
        preferred_id = load_preferred_node_id(messenger.group_id, messenger.user_id)
        global_default_id = load_global_default_node_id()
        default_node = registry.default_node()
        default_id = global_default_id
        fallback_default_id = default_node.node_id if default_node else None
        lines = ["可用节点："]
        for node in nodes:
            tag = []
            if default_id is not None and node.node_id == default_id:
                tag.append("全局默认")
            elif default_id is None and fallback_default_id is not None and node.node_id == fallback_default_id:
                tag.append("默认")
            if preferred_id is not None and node.node_id == preferred_id:
                tag.append("当前")
            tag_text = f"（{'/'.join(tag)}）" if tag else ""
            lines.append(f"{node.node_id}. {node.display_name}{tag_text}")
        if preferred_id is None:
            lines.append("当前使用：默认节点")
        await sender.reply(messenger, "\n".join(lines))

    @plugin.on_msg(r"(更改|使用)节点\s*(\d+)")
    async def change_node(messenger, matches):
        if _is_self(messenger):
            return
        node_id = int(matches.group(2))
        node = registry.get_node(node_id)
        if not node:
            await sender.reply(messenger, f"节点 {node_id} 不存在，请先发送“可用节点”查看列表")
            return
        save_preferred_node_id(messenger.group_id, messenger.user_id, node_id)
        await sender.reply(messenger, f"已切换到节点 {node_id}（{node.display_name}），仅对你生效")

    @plugin.on_msg(r"(更改|使用)默认节点\s*(\d+)")
    async def change_default_node(messenger, matches):
        if _is_self(messenger):
            return
        node_id = int(matches.group(2))
        node = registry.get_node(node_id)
        if not node:
            await sender.reply(messenger, f"节点 {node_id} 不存在，请先发送“可用节点”查看列表")
            return
        save_global_default_node_id(node_id)
        await sender.reply(messenger, f"已设置全局默认节点为 {node_id}（{node.display_name}）")
