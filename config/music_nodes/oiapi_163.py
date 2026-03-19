from src.plugins.music.node import MusicAPINode, MusicInfo


class OiApiMusic163Node(MusicAPINode):
    """OiApi 网易云音乐节点
    
    该节点支持付费歌曲
    """

    api_url = "https://oiapi.net/api/Music_163"
    display_name = "oiapi_music_163"

    async def search_music_list(self, name: str):
        resp = await self._request({"name": name})
        items = resp.get("data") if isinstance(resp, dict) else resp
        if isinstance(items, dict):
            items = items.get("list") or items.get("songs") or items.get("data")
        if not isinstance(items, list):
            return tuple()
        result = []
        for item in items:
            if not isinstance(item, dict):
                continue
            result.append(_to_music_info(item))
        return tuple(result)

    async def get_music_info(self, name: str, n: int):
        resp = await self._request({
            "name": name,
            "n": n,
        })
        detail = resp.get("data") if isinstance(resp, dict) else resp
        if isinstance(detail, list):
            detail = detail[0] if detail else {}
        if isinstance(detail, dict):
            return _to_music_info(detail)
        return MusicInfo(name=str(detail), singers=tuple(), id="")


def _to_music_info(item: dict) -> MusicInfo:
    name = item.get("name") or "未知"
    _singers = item.get("singers")
    singers = []
    for singer in _singers:
        singers.append(singer["name"])
    music_id = item.get("id")
    picture = item.get("picUrl")
    jump_url = item.get("jumpurl")
    source_url = item.get("url")
    return MusicInfo(
        name=str(name),
        singers=tuple(s for s in singers if s),
        id=str(music_id),
        picture_url=str(picture) if picture else None,
        jump_url=str(jump_url) if jump_url else None,
        source_url=str(source_url) if source_url else None,
    )
