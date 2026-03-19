import asyncio
import os
import signal
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
