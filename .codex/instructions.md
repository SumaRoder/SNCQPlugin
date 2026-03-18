# SNCQPlugin

## 📋 项目概述

**项目名称**: SNCQPlugin  
**项目类型**: 基于 WebSocket 的 QQ 机器人插件系统  
**技术栈**: Python 3.12 + OneBot V11 + asyncio  
**核心功能**: 音乐搜索、鹿管签到、消息管理、文件上传

---

## 🏗️ 架构原则

### 核心架构
```
main.py (入口) → Plugin (插件系统) → NapCatClient (WebSocket) → OneBotAPI (API封装)
     ↓
PluginSystem (插件注册) → 插件层 (music, deer_checkin, picsearcher 等等)
     ↓
Messenger (消息解析) → MessageHandler (处理器) → Sender (消息发送)
```

### 关键设计模式
- **装饰器模式**: `@plugin.on_msg()`, `@plugin.on_group_msg()`, `@plugin.on_private_msg()`
- **建造者模式**: `MessengerBuilder` 链式构建消息
- **注册表模式**: `PluginSystem`, `MusicNodeRegistry`
- **策略模式**: 多音乐节点切换

---

## 💻 代码规范

### Python 风格
- ✅ **必须**: `from __future__ import annotations` (启用延迟类型注解)
- ✅ **必须**: 完整的类型注解 (`str`, `int`, `Optional`, `List`, `Dict`, `Callable`, `Awaitable`)
- ✅ **推荐**: 使用 `dataclass` 定义数据结构
- ✅ **推荐**: 使用 f-string 格式化字符串
- ✅ **推荐**: 异步函数优先使用 `async/await`
- ✅ **推荐**: 使用 `logger` 而非 `print`

### 命名约定
- **类名**: `PascalCase` (如 `MusicNodeRegistry`, `MessengerBuilder`)
- **函数/方法**: `snake_case` (如 `load_music_state`, `resolve_user_node`)
- **私有方法**: 前缀 `_` (如 `_is_self`, `_extract_file_segments`)
- **常量**: `UPPER_SNAKE_CASE` (如 `MAX_CONCURRENT`, `WS_URL`)
- **插件目录**: `snake_case` (如 `deer_checkin`, `picsearcher`)

### 导入顺序
```python
from __future__ import annotations

# 标准库
import asyncio
import json
from typing import Callable, Optional

# 第三方库
from ftpretty import ftpretty

# 项目模块
from src.core import Plugin
from src.core.messenger import Messenger
```

---

## 🔌 插件开发规范

### 插件结构
```
src/plugins/{plugin_name}/
├── __init__.py          # 导出 register 函数
├── handlers.py          # 消息处理器（主要逻辑）
├── storage.py           # 数据存储操作（可选）
├── render.py            # 图像渲染（可选）
├── utils.py             # 工具函数（可选）
└── node.py              # 节点管理（如适用）
```

### 插件注册模式
```python
# __init__.py
from __future__ import annotations

from src.core.plugin import Plugin

def register(plugin: Plugin) -> None:
    sender = plugin.get_sender()

    @plugin.on_msg(r"^指令\s*(.+)")
    async def handler(messenger, matches):
        # 处理逻辑
        pass

    @plugin.on_group_msg(r"^群指令")
    async def group_handler(messenger, matches):
        # 仅群消息
        pass

    @plugin.on_private_msg(r"^私聊指令")
    async def private_handler(messenger, matches):
        # 仅私聊
        pass
```

### 消息处理原则
1. **自检**: 使用 `_is_self(messenger)` 过滤自身消息
2. **错误处理**: 使用 `try-except` 捕获异常并友好提示
3. **响应反馈**: 所有操作都应给用户反馈（成功/失败）
4. **并发控制**: 装饰器自动使用 semaphore，无需手动控制

### 数据存储规范
- **路径**: `data/{group_id}/{user_id}/{plugin_name}.json`
- **格式**: UTF-8 编码的 JSON，缩进 4 格
- **操作**: 使用 `load_user_data()` 和 `save_user_data()` 工具函数

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

---

## 🎨 消息构建规范

### MessengerBuilder 使用
```python
from src.core.messenger import MessengerBuilder

# 链式构建
builder = (MessengerBuilder()
    .at(user_id)
    .text("你好")
    .image("http://example.com/img.jpg")
    .record("http://example.com/audio.mp3"))

# 转换为 CQ 码字符串
message = builder.to_string()

# 获取消息段列表
segments = builder.build()

# 发送
await sender.reply(messenger, builder)
```

### CQ 码类型
- **文本**: `.text("内容")`
- **@**: `.at(user_id)`
- **图片**: `.image(url)`
- **语音**: `.record(url)`
- **音乐**: `.music("163", url=url, audio=audio, title=title)`
- **视频**: `.video(url)`
- **JSON**: `.json(json_data)`

### Sender 使用
```python
sender = plugin.get_sender()

# 回复消息
await sender.reply(messenger, "回复内容")

# 回复图片
await sender.reply_with_image(messenger, "http://example.com/img.jpg")

# 发送群消息
await sender.send_group_msg(group_id, "消息内容")

# 发送私聊消息
await sender.send_private_msg(user_id, "消息内容")

# 一种组合消息推荐用法: 相见上方 MessengerBuilder 用法介绍
await sender.reply(messenger, builder)
```

---

## 🔐 安全规范

### ❌ 禁止事项
1. **硬编码凭证**: 绝不允许在代码中硬编码密钥、Token、密码
2. **日志泄露**: 绝不在日志中输出敏感信息（Token、密码、Cookie）
3. **SQL 注入**: 如涉及数据库，必须使用参数化查询
4. **命令注入**: 绝不直接拼接用户输入到 shell 命令

### ✅ 推荐做法
```python
# ❌ 错误
WS_TOKEN = "NightMareMoon"

# ✅ 正确
import os
WS_TOKEN = os.getenv("SNCQ_WS_TOKEN", "")

# ❌ 错误
logger.info(f"用户密码: {password}")

# ✅ 正确
logger.info(f"用户登录成功，密码长度: {len(password)}")
```

---

## 🧪 测试规范

### 测试优先级
1. **核心模块优先**: `client.py`, `api.py`, `messenger.py`
2. **插件逻辑**: 各插件的 `handlers.py`
3. **边界情况**: 异常处理、并发控制

### 测试要求
- ✅ 使用 `pytest` 框架
- ✅ 异步函数使用 `pytest-asyncio`
- ✅ Mock 外部依赖（WebSocket、API、文件系统）
- ✅ 覆盖率目标: 80%+

---

## 📚 文档规范

### 代码文档
- **模块**: 模块开头添加文档字符串说明功能
- **类**: 说明类的用途和设计意图
- **函数**: 使用 Google 风格或 Sphinx 风格

```python
def resolve_user_node(messenger: Messenger, registry: MusicNodeRegistry) -> Optional[MusicAPINode]:
    """
    解析用户偏好的音乐节点
    
    优先级: 用户偏好 > 全局默认 > 系统默认
    
    Args:
        messenger: 消息传递器
        registry: 节点注册表
    
    Returns:
        音乐节点实例，如果未找到返回 None
    """
    pass
```

### 注释原则
- ✅ 注释"为什么"而非"是什么"
- ✅ 复杂逻辑必须注释
- ✅ 临时标记使用 `# TODO:`, `# FIXME:`, `# HACK:`
- ❌ 避免无意义的注释

---

## 🚀 性能规范

### 异步编程
- ✅ 所有 I/O 操作必须使用异步 (`async/await`)
- ✅ CPU 密集型任务使用 `asyncio.to_thread()`
- ✅ 避免在异步函数中使用阻塞操作

```python
# ✅ 正确
async def fetch_data():
    data = await plugin.api.get_file(file_id)
    return data

# ✅ 正确（阻塞任务）
async def process_image(img_path):
    def _process():
        return PIL.Image.open(img_path).resize((100, 100))
    return await asyncio.to_thread(_process)
```

### 资源管理
- ✅ 及时关闭文件、FTP 连接
- ✅ 使用 `async with` 管理资源
- ✅ 限制并发数（默认 `max_concurrent=10`）

---

## 🗂️ 文件组织规范

### 目录结构
```
SNCQPlugin/
├── main.py                    # 入口文件（配置 WebSocket 和 FTP）
├── src/
│   ├── __init__.py
│   ├── plugin_system.py       # 插件注册系统
│   └── core/
│       ├── __init__.py
│       ├── plugin.py          # Plugin 主类和装饰器
│       ├── client.py          # NapCatClient WebSocket 客户端
│       ├── api.py             # OneBot V11 API 完整封装
│       ├── messenger.py       # 消息解析与 MessengerBuilder
│       ├── sender.py          # 消息发送封装
│       ├── constants.py       # 常量与枚举定义
│       ├── logger.py          # 日志系统
│       ├── exceptions.py      # 自定义异常
│       └── reload.py          # 热重载机制
├── src/plugins/               # 插件目录
│   ├── music/                 # 音乐插件
│   ├── deer_checkin/          # 鹿管签到插件
│   └── picsearcher/           # 图片搜索插件
├── config/
│   └── music_nodes/           # 音乐节点配置
├── data/                      # 数据存储
│   └── {group_id}/{user_id}/  # 用户数据
├── res/                       # 资源文件
│   ├── *.ttf                  # 字体文件
│   └── deer_check_in/         # 签到图片资源
├── temp/                      # 临时文件（运行时生成）
└── requirements.txt           # 依赖声明（建议添加）
```

---

## 🔧 常见任务指南

### 添加新插件
1. 在 `src/plugins/` 创建插件目录
2. 实现插件逻辑和 `register()` 函数
3. 在 `src/plugin_system.py` 中注册插件
4. 在 `data/` 目录下设计数据存储结构
5. 如需资源文件，添加到 `res/` 目录

### 添加音乐节点
1. 在 `config/music_nodes/` 创建 Python 文件
2. 继承 `MusicAPINode` 基类
3. 实现 `search_music_list()` 和 `get_music_info()`
4. 设置 `api_url` 和 `display_name` 属性

### 添加 API 方法
1. 在 `src/core/api.py` 的 `OneBotAPI` 类中添加方法
2. 使用 `await self.client._api_call(action, params)`
3. 添加类型注解和文档字符串
4. 考虑添加便捷方法到 `Sender` 类

### 添加日志
```python
from src.core.logger import Logger

logger = Logger(name=__name__, path="plugin.log")

logger.info("信息日志", tag="startup")
logger.warning("警告日志", tag="config")
logger.error("错误日志", tag="network")
logger.debug("调试日志", messenger)
```

---

## ⚠️ 注意事项

### 硬编码凭证问题
**当前问题**: `main.py` 中 WebSocket Token 和 FTP 凭证直接硬编码  
**影响**: 安全风险，不适合生产环境  
**解决方案**: 使用环境变量或配置文件

### 插件启用状态
**当前状态**: 只有 `picsearcher` 插件启用，其他插件被注释  
**建议**: 完善所有插件实现或移除空插件

### 依赖管理
**缺失**: 项目没有 `requirements.txt`  
**建议**: 添加依赖声明文件

### 临时文件清理
**问题**: `temp/` 目录会不断生成图片文件  
**建议**: 添加定时清理机制或使用 `tempfile` 自动管理

---

## 📝 提交规范

### Commit Message 格式
```
<type>(<scope>): <subject>

<body>

<footer>
```

### 类型 (type)
- `feat`: 新功能
- `fix`: 修复 Bug
- `refactor`: 重构
- `docs`: 文档
- `style`: 代码格式
- `test`: 测试
- `chore`: 构建/工具

### 示例
```
feat(music): 添加 QQ 音乐节点支持

- 实现 QQ 音乐 API 封装
- 支持搜索和播放功能
- 添加节点切换逻辑

Closes #123
```

---

## 🎯 开发流程

1. **理解需求**: 明确功能需求和边界条件
2. **设计方案**: 选择合适的设计模式和技术方案
3. **编写代码**: 遵循代码规范和最佳实践
4. **测试验证**: 单元测试 + 集成测试
5. **代码审查**: 自查代码质量和安全性
6. **提交代码**: 遵循提交规范
7. **文档更新**: 更新相关文档

---

## 📚 参考资料

- **OneBot V11 标准**: https://onebot.dev/
- **CQ 码文档**: https://docs.go-cqhttp.org/cqcode/
- **Python 异步编程**: https://docs.python.org/3/library/asyncio.html
- **NapCatQQ 服务端 API 文档**: https://napcat.apifox.cn/
- **项目 GitHub**: https://github.com/SumaRoder/SNCQPlugin

