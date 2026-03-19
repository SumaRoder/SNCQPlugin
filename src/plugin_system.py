from __future__ import annotations

from typing import Callable, Iterable, List

from src.core.plugin import Plugin
from src.plugins.deer_checkin import register as register_deer_checkin
from src.plugins.music import register as register_music
from src.plugins.picsearcher import register as register_picsearcher
from src.plugins.system_tools import register as register_system_tools


RegisterFunc = Callable[[Plugin], None]


class PluginSystem:
    """统一管理插件注册流程。"""

    def __init__(self, registers: Iterable[RegisterFunc] | None = None) -> None:
        self._registers: List[RegisterFunc] = list(registers or [])

    def add(self, register_func: RegisterFunc) -> None:
        self._registers.append(register_func)

    def register_all(self, plugin: Plugin) -> None:
        for register_func in self._registers:
            register_func(plugin)


def setup_plugins(plugin: Plugin) -> PluginSystem:
    system = PluginSystem([
        register_system_tools,
        register_picsearcher,
        register_deer_checkin,
        register_music,
    ])
    system.register_all(plugin)
    return system
