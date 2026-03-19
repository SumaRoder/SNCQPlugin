from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.parse import urlparse

from src.core.messenger import Messenger, MessengerBuilder
from src.core.plugin import Plugin
from src.core.auth import is_admin


API_URL = "https://api.lolicon.app/setu/v2"
DEFAULT_SIZE = "regular"
DATA_ROOT = Path(__file__).resolve().parents[3] / "data"


def _is_self(messenger: Messenger) -> bool:
    return messenger.user_id == messenger.self_id


def _normalize_tags(keyword: str) -> List[str]:
    keyword = keyword.strip()
    if not keyword:
        return []
    parts = [part for part in re.split(r"\s+", keyword) if part]
    return parts[:3]


def _parse_count(text: str) -> int:
    text = (text or "").strip()
    if not text:
        return 1
    if text.isdigit():
        return int(text)
    mapping = {
        "零": 0,
        "一": 1,
        "二": 2,
        "两": 2,
        "俩": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
        "十": 10,
    }
    if text in mapping:
        return mapping[text]
    if "十" in text:
        left, _, right = text.partition("十")
        tens = mapping.get(left, 1) if left else 1
        ones = mapping.get(right, 0) if right else 0
        return tens * 10 + ones
    return 1


def _build_payload(
    keyword: Optional[str],
    *,
    r18: int = 0,
    exclude_ai: bool = False,
    num: int = 1,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "num": num,
        "r18": r18,
        "size": DEFAULT_SIZE,
    }
    if exclude_ai:
        payload["excludeAI"] = True
    if keyword:
        tags = _normalize_tags(keyword)
        if tags:
            payload["tag"] = tags[0] if len(tags) == 1 else tags
        else:
            payload["keyword"] = keyword
    return payload


def _get_scope_key(messenger: Messenger) -> str:
    if messenger.group_id is not None:
        return str(messenger.group_id)
    return f"private_{messenger.user_id}"


def _get_scope_config_path(scope_key: str) -> Path:
    return DATA_ROOT / scope_key / "picsearch.json"


def _load_scope_config(scope_key: str) -> Dict[str, Any]:
    path = _get_scope_config_path(scope_key)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_scope_config(scope_key: str, config: Dict[str, Any]) -> None:
    path = _get_scope_config_path(scope_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def _is_r18_allowed(messenger: Messenger) -> bool:
    scope_key = _get_scope_key(messenger)
    config = _load_scope_config(scope_key)
    if "allow_r18" in config:
        return bool(config.get("allow_r18"))
    return messenger.group_id is None


def _is_ai_allowed(messenger: Messenger) -> bool:
    scope_key = _get_scope_key(messenger)
    config = _load_scope_config(scope_key)
    if "allow_ai" in config:
        return bool(config.get("allow_ai"))
    return True


def _is_picsearch_enabled(messenger: Messenger) -> bool:
    scope_key = _get_scope_key(messenger)
    config = _load_scope_config(scope_key)
    if "enable_picsearch" in config:
        return bool(config.get("enable_picsearch"))
    return messenger.group_id is None


def _is_invert_enabled(messenger: Messenger) -> bool:
    scope_key = _get_scope_key(messenger)
    config = _load_scope_config(scope_key)
    return bool(config.get("invert_image", False))


def _get_invert_dir(messenger: Messenger) -> Path:
    scope_key = _get_scope_key(messenger)
    return DATA_ROOT / scope_key / "picsearch_tmp"


def _download_image(url: str, dest_dir: Path) -> Optional[Path]:
    parsed = urlparse(url)
    suffix = Path(parsed.path).suffix or ".jpg"
    dest_dir.mkdir(parents=True, exist_ok=True)
    target = dest_dir / f"setu_{abs(hash(url))}{suffix}"
    try:
        req = Request(url, headers={"User-Agent": "SNCQPlugin/1.0"})
        with urlopen(req, timeout=20) as resp:
            data = resp.read()
            content_type = resp.headers.get("Content-Type", "")
        if suffix == ".jpg" and "image/png" in content_type:
            target = target.with_suffix(".png")
        elif suffix == ".jpg" and "image/webp" in content_type:
            target = target.with_suffix(".webp")
        with open(target, "wb") as f:
            f.write(data)
        return target
    except Exception:
        return None


def _invert_image(path: Path) -> Optional[Path]:
    try:
        from PIL import Image, ImageOps
    except Exception:
        return None
    try:
        img = Image.open(path)
        img.load()
        inverted = ImageOps.flip(img)
        target = path.with_name(path.stem + "_inv" + path.suffix)
        inverted.save(target)
        return target
    except Exception:
        return None


def _extract_image_url(item: Dict[str, Any]) -> Optional[str]:
    urls = item.get("urls", {}) if isinstance(item.get("urls"), dict) else {}
    return urls.get(DEFAULT_SIZE) or urls.get("original") or next(iter(urls.values()), None)


def _resolve_image_uri(messenger: Messenger, item: Dict[str, Any]) -> Optional[str]:
    img_url = _extract_image_url(item)
    if not img_url:
        return None
    if not _is_invert_enabled(messenger):
        return img_url
    local_path = _download_image(img_url, _get_invert_dir(messenger))
    if not local_path:
        return img_url
    inverted = _invert_image(local_path)
    if not inverted:
        return img_url
    return str(inverted)


def _format_caption(item: Dict[str, Any]) -> str:
    title = item.get("title") or "未知标题"
    author = item.get("author") or "未知作者"
    pid = item.get("pid")
    uid = item.get("uid")
    tags = item.get("tags") or []
    tag_text = "、".join(tags[:10]) if isinstance(tags, list) else str(tags)
    lines = [f"标题：{title}", f"作者：{author}"]
    if pid:
        lines.append(f"PID：{pid}")
    if uid:
        lines.append(f"UID：{uid}")
    if tag_text:
        lines.append(f"标签：{tag_text}")
    return "\n".join(lines)


def _is_r18_item(item: Dict[str, Any]) -> bool:
    if item.get("r18") is True:
        return True
    tags = item.get("tags") or []
    if isinstance(tags, list):
        return any(str(tag).upper() in ("R-18", "R18", "R-18G", "R18G") for tag in tags)
    return False


def _request_setu(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = Request(API_URL, data=data, headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


async def _fetch_setu(payload: Dict[str, Any]) -> Dict[str, Any]:
    return await asyncio.to_thread(_request_setu, payload)


def register(plugin: Plugin) -> None:
    sender = plugin.get_sender()

    async def _ensure_admin(messenger: Messenger) -> bool:
        if is_admin(messenger.user_id):
            return True
        await sender.reply(messenger, "无权限操作")
        return False

    @plugin.on_msg(r"(?i)^允许(r18|(涩|色|瑟)图)(功能)?$")
    async def allow_r18(messenger: Messenger, matches):
        if _is_self(messenger):
            return
        if not await _ensure_admin(messenger):
            return
        scope_key = _get_scope_key(messenger)
        config = _load_scope_config(scope_key)
        config["allow_r18"] = True
        _save_scope_config(scope_key, config)
        await sender.reply(messenger, "已开启色图功能")

    @plugin.on_msg(r"(?i)^关闭(r18|(涩|色|瑟)图)(功能)?$")
    async def disable_r18(messenger: Messenger, matches):
        if _is_self(messenger):
            return
        if not await _ensure_admin(messenger):
            return
        scope_key = _get_scope_key(messenger)
        config = _load_scope_config(scope_key)
        config["allow_r18"] = False
        _save_scope_config(scope_key, config)
        await sender.reply(messenger, "已关闭色图功能")

    @plugin.on_msg(r"^开启图片功能$")
    async def enable_picsearch(messenger: Messenger, matches):
        if _is_self(messenger):
            return
        if not await _ensure_admin(messenger):
            return
        scope_key = _get_scope_key(messenger)
        config = _load_scope_config(scope_key)
        config["enable_picsearch"] = True
        _save_scope_config(scope_key, config)
        await sender.reply(messenger, "已开启图片功能")

    @plugin.on_msg(r"^关闭图片功能$")
    async def disable_picsearch(messenger: Messenger, matches):
        if _is_self(messenger):
            return
        if not await _ensure_admin(messenger):
            return
        scope_key = _get_scope_key(messenger)
        config = _load_scope_config(scope_key)
        config["enable_picsearch"] = False
        _save_scope_config(scope_key, config)
        await sender.reply(messenger, "已关闭图片功能")

    @plugin.on_msg(r"^允许图片反转(功能)?$")
    async def enable_invert(messenger: Messenger, matches):
        if _is_self(messenger):
            return
        if not await _ensure_admin(messenger):
            return
        scope_key = _get_scope_key(messenger)
        config = _load_scope_config(scope_key)
        config["invert_image"] = True
        _save_scope_config(scope_key, config)
        await sender.reply(messenger, "已开启图片反转功能")

    @plugin.on_msg(r"^关闭图片反转(功能)?$")
    async def disable_invert(messenger: Messenger, matches):
        if _is_self(messenger):
            return
        if not await _ensure_admin(messenger):
            return
        scope_key = _get_scope_key(messenger)
        config = _load_scope_config(scope_key)
        config["invert_image"] = False
        _save_scope_config(scope_key, config)
        await sender.reply(messenger, "已关闭图片反转功能")

    @plugin.on_msg(r"^允许(包含)?AI图片(功能)?$")
    async def allow_ai(messenger: Messenger, matches):
        if _is_self(messenger):
            return
        if not await _ensure_admin(messenger):
            return
        scope_key = _get_scope_key(messenger)
        config = _load_scope_config(scope_key)
        config["allow_ai"] = True
        _save_scope_config(scope_key, config)
        await sender.reply(messenger, "已允许包含 AI 图片")

    @plugin.on_msg(r"(?i)^关闭(包含)?AI图片(功能)?$")
    async def disable_ai(messenger: Messenger, matches):
        if _is_self(messenger):
            return
        if not await _ensure_admin(messenger):
            return
        scope_key = _get_scope_key(messenger)
        config = _load_scope_config(scope_key)
        config["allow_ai"] = False
        _save_scope_config(scope_key, config)
        await sender.reply(messenger, "已关闭包含 AI 图片")

    @plugin.on_msg(r"^来([0-9一二三四五六七八九十两俩]+)?(点|张)(.*)美图$")
    async def random_sfw(messenger: Messenger, matches):
        if _is_self(messenger):
            return
        if not _is_picsearch_enabled(messenger):
            await sender.reply(messenger, "图片功能已关闭")
            return
        count_text = matches.group(1) or ""
        keyword = matches.group(3).strip()
        r18 = 0
        exclude_ai = not _is_ai_allowed(messenger)
        count = _parse_count(count_text)
        count = max(1, min(count, 20))
        payload = _build_payload(keyword or None, r18=r18, exclude_ai=exclude_ai, num=count)
        await _send_setu(plugin, sender, messenger, payload, keyword=keyword or None)

    @plugin.on_msg(r"^来([0-9一二三四五六七八九十两]+)?(点|张)(.*)(涩|色|瑟)图$")
    async def random_r18(messenger: Messenger, matches):
        if _is_self(messenger):
            return
        if not _is_picsearch_enabled(messenger):
            await sender.reply(messenger, "图片功能已关闭")
            return
        if not _is_r18_allowed(messenger):
            await sender.reply(messenger, "不可以色色！")
            return
        count_text = matches.group(1) or ""
        keyword = matches.group(3).strip()
        exclude_ai = not _is_ai_allowed(messenger)
        count = _parse_count(count_text)
        count = max(1, min(count, 20))
        payload = _build_payload(keyword or None, r18=1, exclude_ai=exclude_ai, num=count)
        await _send_setu(plugin, sender, messenger, payload, keyword=keyword or None)


async def _send_setu(
    plugin: Plugin,
    sender,
    messenger: Messenger,
    payload: Dict[str, Any],
    keyword: Optional[str] = None,
):
    max_attempts = 5
    for _ in range(max_attempts):
        try:
            resp = await _fetch_setu(payload)
        except Exception as e:
            await sender.reply(messenger, f"请求色图失败：{e}")
            return

        if not isinstance(resp, dict):
            await sender.reply(messenger, "色图接口返回异常")
            return

        error = resp.get("error")
        if error:
            await sender.reply(messenger, f"色图接口报错：{error}")
            return

        data = resp.get("data") or []
        if not data:
            tip = f"未找到与“{keyword}”相关的图片" if keyword else "未获取到图片"
            await sender.reply(messenger, tip)
            return
        if not _is_r18_allowed(messenger):
            if isinstance(data, list):
                data = [item for item in data if isinstance(item, dict) and not _is_r18_item(item)]
            elif isinstance(data, dict) and _is_r18_item(data):
                data = []
            if not data:
                continue
        break
    else:
        await sender.reply(messenger, "不可以色色！")
        return
    if isinstance(data, list) and len(data) > 1:
        nodes = []
        for item in data:
            if not isinstance(item, dict):
                continue
            img_url = _resolve_image_uri(messenger, item)
            caption = _format_caption(item)
            builder = MessengerBuilder()
            if img_url:
                builder.image(img_url).text("\n" + caption)
            else:
                builder.text(caption + "\n（未获取到图片地址）")
            nodes.append({
                "type": "node",
                "data": {
                    "name": "PicSearcher",
                    "uin": messenger.self_id,
                    "content": builder.to_string(),
                },
            })
        if not nodes:
            await sender.reply(messenger, "色图数据格式异常")
            return
        if messenger.type.value == "group" and messenger.group_id is not None:
            await plugin.api.send_group_forward_msg(messenger.group_id, nodes)
        elif messenger.type.value == "private" and messenger.user_id is not None:
            await plugin.api.send_private_forward_msg(messenger.user_id, nodes)
        else:
            await sender.reply(messenger, "无法确定消息类型，发送失败")
        return

    item = data[0] if isinstance(data, list) else data
    if not isinstance(item, dict):
        await sender.reply(messenger, "色图数据格式异常")
        return

    img_url = _resolve_image_uri(messenger, item)
    caption = _format_caption(item)
    builder = MessengerBuilder()
    if img_url:
        builder.image(img_url).text("\n" + caption)
    else:
        builder.text(caption + "\n（未获取到图片地址）")
    send_result = await sender.reply(messenger, builder)
    if send_result["status"] != "ok":
        await sender.reply(messenger, f"发送失败：{send_result['message']}")
