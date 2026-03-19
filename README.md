# SNCQPlugin

基于 WebSocket 的 QQ 机器人插件系统，遵循 OneBot V11 标准。

## ✨ 功能

-    **辅助功能** - 支持回复撤回、获取消息体等辅助功能
- 🎵 **音乐搜索** - 支持自定义音乐节点搜索和播放
- 🦌 **鹿管签到/禁欲系统** - 图片签到/禁欲系统与排行榜
-    **图片功能** - 从三方 API 中获取来自 Pixiv 的美图/色图
- 🔧 **插件系统** - 模块化设计，易于扩展
- 📝 **消息管理** - 支持获取消息体、合并转发解析
- 🔔 **通知处理** - 支持群成员变动、好友请求等事件

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

- Python 3.8+
- NapCatQQ (或基于 OneBot V11 实现的其他框架的反向 WebSocket 服务端)

### 安装依赖

```bash
pip install websockets Pillow watchdog colorlog python-dateutil
```

或使用 requirements.txt（如果存在）：
```bash
pip install -r requirements.txt
```

### 运行

```bash
python main.py
```

## 📜 更新日志

查看 [CHANGELOG.md](CHANGELOG.md) 获取详细更新记录。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

本项目采用 Apache License 2.0 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

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
