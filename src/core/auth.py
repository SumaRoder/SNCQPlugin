from __future__ import annotations

import os
import tomllib
from functools import lru_cache
from typing import Iterable, Set


_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "config", "bot.toml")


@lru_cache(maxsize=1)
def _load_admins() -> Set[int]:
    if not os.path.exists(_CONFIG_PATH):
        return set()
    with open(_CONFIG_PATH, "rb") as f:
        data = f.read().strip()
    if not data:
        return set()
    try:
        config = tomllib.loads(data.decode("utf-8"))
    except Exception:
        return set()
    raw_list: Iterable = config.get("admin_qq_list", []) or []
    admins: Set[int] = set()
    for item in raw_list:
        try:
            admins.add(int(item))
        except Exception:
            continue
    return admins


def is_admin(user_id: int | None) -> bool:
    if user_id is None:
        return False
    return user_id in _load_admins()


def reload_admins() -> None:
    _load_admins.cache_clear()
