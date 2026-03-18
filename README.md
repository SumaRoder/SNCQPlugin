# SNCQPlugin

基于 WebSocket 的 QQ 机器人插件系统，遵循 OneBot V11 标准。

## ✨ 功能

- 🎵 **音乐搜索** - 支持多音乐节点搜索和播放
- 🦌 **鹿管签到** - 签到系统与排行榜
- 🔧 **插件系统** - 模块化设计，易于扩展
- 📝 **消息管理** - 支持获取消息体、合并转发解析
- 🔔 **通知处理** - 支持群成员变动、好友请求等事件

## 🏗️ 项目架构

```
SNCQPlugin/
├── main.py                    # 应用入口
├── src/
│   ├── plugin_system.py       # 插件注册系统
│   └── core/                  # 核心框架
│       ├── plugin.py          # Plugin 主类和装饰器
│       ├── client.py          # NapCatClient WebSocket 客户端
│       ├── api.py             # OneBot V11 API 封装
│       ├── messenger.py       # 消息解析与 MessengerBuilder
│       ├── sender.py          # 消息发送封装
│       ├── constants.py       # 常量与枚举定义
│       ├── logger.py          # 日志系统
│       ├── exceptions.py      # 自定义异常
│       └── reload.py          # 热重载机制
├── src/plugins/               # 插件目录
│   ├── music/                 # 音乐搜索插件
│   ├── deer_checkin/          # 鹿管签到插件
│   └── picsearcher/           # 图片搜索插件（占位）
├── config/
│   ├── server.toml            # 服务器配置（WS URL、Token）
│   └── music_nodes/           # 音乐节点配置
├── data/                      # 数据存储（用户数据、签到记录等）
├── res/                       # 资源文件（字体、图片等）
└── temp/                      # 临时文件（运行时生成）
```

### 核心特性

- **装饰器模式**: 使用 `@plugin.on_msg()` 注册消息处理器
- **建造者模式**: `MessengerBuilder` 链式构建消息
- **注册表模式**: `PluginSystem` 统一管理插件
- **异步架构**: 完整的 async/await 支持
- **并发控制**: Semaphore 限制并发请求
- **自动重连**: WebSocket 断线自动重连
- **热重载**: Debug 模式下支持代码热重载

## 🚀 快速开始

### 环境要求

- Python 3.12+
- NapCatQQ (或基于 OneBot V11 实现的其他框架的反向 WebSocket 服务端)

### 安装依赖

```bash
pip install websockets Pillow watchdog colorlog python-dateutil
```

或使用 requirements.txt（如果存在）：
```bash
pip install -r requirements.txt
```

### 配置

1. 复制配置文件模板（如果不存在）：
```bash
cp config/server.toml.example config/server.toml
```

2. 编辑 `config/server.toml`：
```toml
ws_url = "ws://your-server:port"      # WebSocket 地址
access_token = "your_token"            # 访问令牌
```

**注意**: `config/server.toml` 已添加到 `.gitignore`，不会提交到版本控制。

### 运行

```bash
python main.py
```

### 内置指令

- `/help` - 查看帮助菜单
- `/ping` - 查看 WebSocket 延迟
- `/status` - 查看 NapCatQQ 版本与 WS 延迟
- `[CQ:reply,id=xxx]获取消息体` - 获取消息内容并格式化返回

## 🔌 插件开发

### 创建新插件

1. 在 `src/plugins/` 下创建插件目录
2. 创建 `__init__.py` 并实现 `register()` 函数

```python
# src/plugins/myplugin/__init__.py
from __future__ import annotations

from src.core.plugin import Plugin

def register(plugin: Plugin) -> None:
    sender = plugin.get_sender()

    @plugin.on_msg(r"^指令\s*(.+)")
    async def handler(messenger, matches):
        keyword = matches.group(1)
        await sender.reply(messenger, f"收到指令: {keyword}")
```

3. 在 `src/plugin_system.py` 中注册插件

```python
from src.plugins.myplugin import register as register_myplugin

def setup_plugins(plugin: Plugin) -> PluginSystem:
    system = PluginSystem([register_myplugin])
    system.register_all(plugin)
    return system
```

### 消息构建

```python
from src.core.messenger import MessengerBuilder

builder = (MessengerBuilder()
    .at(user_id)
    .text("你好")
    .image("http://example.com/img.jpg"))

message = builder.to_string()  # 转换为 CQ 码
```

### 数据存储

```python
import json
from pathlib import Path

def load_user_data(user_dir: Path) -> Dict:
    data_file = user_dir / "plugin_data.json"
    if data_file.exists():
        with open(data_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_user_data(user_dir: Path, data: Dict) -> None:
    user_dir.mkdir(parents=True, exist_ok=True)
    data_file = user_dir / "plugin_data.json"
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
```

## 📜 更新日志

查看 [CHANGELOG.md](CHANGELOG.md) 获取详细更新记录。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- [OneBot](https://onebot.dev/) - OneBot 标准
- [NapCatQQ](https://github.com/NapNeko/NapCatQQ) - NapCatQQ 框架
- [go-cqhttp](https://github.com/Mrs4s/go-cqhttp) - CQ 码参考
- [NapCatQQ APIFox](https://napcat.apifox.cn/) - NapCatQQ API 参考

## 📚 相关文档

- [CodexCLI 行为准则](.codex/instructions.md) - 开发规范和最佳实践
- [OneBot V11 标准](https://onebot.dev/)
- [CQ 码文档](https://docs.go-cqhttp.org/cqcode/)

---

**作者**: SumaRoder  
**GitHub**: https://github.com/SumaRoder/SNCQPlugin