# 更新日志

## [1.1.1] - 2026-03-20

### Added
- 权限管理支持
  - 新增 `config/bot.toml` 配置文件
  - 支持指定多个 QQ 号作为 Bot 的主人账号
- system_tools 插件
  - 详见 Changed
- 回复撤回
  - 回复一条消息(可带@)发送"撤回"，如果被回复消息由 Bot 发送或 Bot 本身是群管理时，尝试撤回该消息

### Changed
- main.py 重构
  - 将位于`main.py`中的`/help`等功能更换至`system_tools`

### Fixed
  - picsearcher 图片反转功能无实际效果

### Security
- picsearcher 权限管理支持
  - 只有主人账号才可控制图片功能开关

### Known Issues
- 缺少 requirements.txt 依赖声明文件
- 临时文件夹 temp/ 未实现自动清理功能
- `/help`功能返回的指令列表不全面

---

## [1.1.0] - 2026-03-18

### Added
- 配置文件支持
  - 新增 `config/server.toml` 配置文件
  - 支持 WebSocket URL 和 Access Token 配置
  - 移除硬编码的凭证信息
- 为 codex-cli 提供的 coding 准则
  - 新增 `.codex/instructions.md` 文档
  - 提供完整的开发规范和项目说明
- README 文档完善
  - 添加功能介绍
  - 添加快速开始指南
  - 添加项目架构说明

### Changed
- main.py 重构
  - 移除硬编码的 WebSocket URL 和 Token
  - 新增 `_load_server_config()` 配置加载函数
  - 优化配置管理逻辑
- 插件系统修复
  - 修复 `src/plugin_system.py` 中插件引入问题
  - 取消 deer_checkin, music 的注释，并完成 picsearcher 完整实现
- 安全增强
  - 将 `config/server.toml` 添加到 .gitignore
  - 防止敏感配置信息被提交到版本控制

### Fixed
  - 修复 src 目录下插件引入出现的问题
  - 移除硬编码的 NapCatQQ WebSocket 服务端 URL 和 Token
  - 添加配置文件支持，提升安全性
  - 不应出现的 FTP 上传功能已移除

### Security
- 移除硬编码的敏感信息（WebSocket URL、Token）
- 配置文件已添加到 .gitignore

### Known Issues
- 缺少 requirements.txt 依赖声明文件
- 临时文件夹 temp/ 未实现自动清理功能

---

## [1.0.0] - 2026-03-18

### Added
- 初始版本发布
- 实现核心插件系统架构
- 实现完整的 OneBot V11 API 封装
- 实现 WebSocket 客户端与自动重连机制
- 实现消息解析器与链式消息构建器
- 实现日志系统（支持彩色输出和文件记录）
- 实现热重载机制（Debug 模式）
- 音乐搜索插件
  - 支持多音乐节点
  - 歌曲搜索与播放
  - 节点切换功能
- 鹿管签到插件
  - 签到系统
  - 签到日历渲染
  - 签到排行榜
  - 禁欲系统
- 图片搜索插件（占位）
- FTP 文件上传功能

### Fixed
- **错误的提交**
  - src 目录下插件引入出现问题
  - 硬编码暴露了 NapCatQQ 反向 WebSocket 服务端 URL 和 Token (Token 已修改)

### Known Issues
- WebSocket Token 和 FTP 凭证硬编码在代码中（已在 1.1.0 修复）
- 缺少 requirements.txt 依赖声明文件
- 临时文件夹 temp/ 未实现自动清理功能
- picsearcher 插件仅占位，暂无实际功能

---

## [Unreleased]

### Planned
- 添加 requirements.txt 依赖声明文件
- 完善插件配置管理系统
- 添加单元测试
- 优化临时文件清理机制
