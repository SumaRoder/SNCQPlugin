"""
音乐 API 节点
"""

from __future__ import annotations

import asyncio
import json
import inspect
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Type
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import importlib.util

ROOT_DIR = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class MusicInfo:
    name: str
    singers: Tuple[str, ...]
    id: str
    picture_url: Optional[str] = None
    jump_url: Optional[str] = None
    source_url: Optional[str] = None


class MusicAPINode:
    """音乐 API 节点基类"""

    api_url: str = ""
    display_name: str = ""

    def __init__(self, node_id: int):
        self.node_id = node_id
        self.display_name = self.display_name or self.__class__.__name__

    async def _request(self, params: Dict[str, Any]) -> Any:
        query = urlencode(params)
        url = f"{self.api_url}?{query}"

        def _do_request() -> Any:
            req = Request(url, headers={"User-Agent": "SNCQPlugin/0.3"})
            with urlopen(req, timeout=15) as resp:
                raw = resp.read()
            try:
                return json.loads(raw)
            except Exception:
                return {"raw": raw.decode("utf-8", errors="ignore")}

        return await asyncio.to_thread(_do_request)

    async def search_music_list(self, name: str) -> Tuple[MusicInfo, ...]:
        raise NotImplementedError

    async def get_music_info(self, name: str, n: int) -> MusicInfo:
        raise NotImplementedError


class MusicNodeRegistry:
    """音乐节点注册表"""

    def __init__(self, nodes_path: Optional[Path] = None):
        self.nodes_path = nodes_path or _default_nodes_path()
        self.nodes: Tuple[MusicAPINode, ...] = tuple(_load_nodes(self.nodes_path))

    def get_node(self, node_id: int) -> Optional[MusicAPINode]:
        if 0 <= node_id < len(self.nodes):
            return self.nodes[node_id]
        return None

    def default_node(self) -> Optional[MusicAPINode]:
        return self.nodes[0] if self.nodes else None


def _default_nodes_path() -> Path:
    return ROOT_DIR / "config" / "music_nodes"


def _load_nodes(path: Path) -> List[MusicAPINode]:
    if not path.exists():
        return []
    nodes: List[MusicAPINode] = []
    py_files = sorted(p for p in path.glob("*.py") if p.is_file())
    for file_path in py_files:
        module = _load_module_from_path(file_path)
        if not module:
            continue
        classes = _collect_music_node_classes(module)
        for cls in classes:
            try:
                nodes.append(cls(len(nodes)))
            except Exception:
                continue
    return nodes


def _load_module_from_path(path: Path):
    module_name = f"music_nodes_{path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _collect_music_node_classes(module) -> List[Type[MusicAPINode]]:
    classes: List[Type[MusicAPINode]] = []
    for _, obj in inspect.getmembers(module, inspect.isclass):
        if obj.__module__ != module.__name__:
            continue
        if _is_music_api_node_subclass(obj):
            classes.append(obj)
    return classes


def _is_music_api_node_subclass(cls: Type[Any]) -> bool:
    for base in cls.__mro__[1:]:
        if "MusicAPINode" in base.__name__:
            return True
    return False


def get_music_state_path(group_id: Optional[int], user_id: int) -> Path:
    gid = str(group_id) if group_id is not None else "0"
    return ROOT_DIR / "data" / gid / str(user_id) / "music.json"


def load_music_state(group_id: Optional[int], user_id: int) -> Dict[str, Any]:
    path = get_music_state_path(group_id, user_id)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_music_state(group_id: Optional[int], user_id: int, state: Dict[str, Any]) -> None:
    path = get_music_state_path(group_id, user_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


PREFERRED_NODE_KEY = "preferred_node_id"
GLOBAL_DEFAULT_NODE_KEY = "default_node_id"


def _global_music_state_path() -> Path:
    return ROOT_DIR / "data" / "music.json"


def load_global_music_state() -> Dict[str, Any]:
    path = _global_music_state_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_global_music_state(state: Dict[str, Any]) -> None:
    path = _global_music_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def load_global_default_node_id() -> Optional[int]:
    state = load_global_music_state()
    value = state.get(GLOBAL_DEFAULT_NODE_KEY)
    return value if isinstance(value, int) else None


def save_global_default_node_id(node_id: Optional[int]) -> None:
    state = load_global_music_state()
    if node_id is None:
        state.pop(GLOBAL_DEFAULT_NODE_KEY, None)
    else:
        state[GLOBAL_DEFAULT_NODE_KEY] = int(node_id)
    save_global_music_state(state)


def load_preferred_node_id(group_id: Optional[int], user_id: int) -> Optional[int]:
    state = load_music_state(group_id, user_id)
    value = state.get(PREFERRED_NODE_KEY)
    return value if isinstance(value, int) else None


def save_preferred_node_id(group_id: Optional[int], user_id: int, node_id: Optional[int]) -> None:
    state = load_music_state(group_id, user_id)
    if node_id is None:
        state.pop(PREFERRED_NODE_KEY, None)
    else:
        state[PREFERRED_NODE_KEY] = int(node_id)
    save_music_state(group_id, user_id, state)
