"""
插件主类和装饰器
"""

import asyncio
import logging
import re
from typing import Callable, Dict, Any, Optional, List, Pattern
from functools import wraps
from .client import NapCatClient
from .logger import Logger
from .messenger import Messenger, MessageType
from .api import OneBotAPI
from .sender import Sender
from .constants import (
    PostType,
    NoticeType,
    RequestType,
    Priority,
    DefaultValue,
    PluginConfig
)

logger = Logger(name=__name__, path="app.log")

class MessageHandler:
    """消息处理器"""
    
    def __init__(self, pattern: str, func: Callable, priority: int = 0, block: bool = True, plugin_instance=None):
        """
        初始化消息处理器
        
        Args:
            pattern: 正则表达式模式
            func: 处理函数
            priority: 优先级（数字越大优先级越高）
            block: 是否阻止后续处理器执行
            plugin_instance: 插件实例（用于检查启用状态）
        """
        self.pattern = pattern
        self.func = func
        self.priority = priority
        self.block = block
        self.plugin_instance = plugin_instance
        self._compiled_pattern: Optional[Pattern] = None
    
    @property
    def compiled_pattern(self) -> Pattern:
        """获取编译后的正则表达式"""
        if self._compiled_pattern is None:
            try:
                self._compiled_pattern = re.compile(self.pattern)
            except re.error as e:
                logger.error(f"正则表达式编译失败: {self.pattern}, 错误: {e}")
                raise
        return self._compiled_pattern
    
    def match(self, message: str) -> Optional[re.Match]:
        """
        匹配消息
        
        Args:
            message: 消息内容
        
        Returns:
            匹配结果
        """
        return self.compiled_pattern.search(message)
    
    def is_enabled(self) -> bool:
        """
        检查处理器是否启用
        
        Returns:
            如果插件实例存在且已启用返回True，否则返回True
        """
        if self.plugin_instance is None:
            return True
        return self.plugin_instance.is_enabled()
    
    async def handle(self, messenger: Messenger, matches: re.Match):
        """
        处理消息
        
        Args:
            messenger: 消息传递器
            matches: 正则匹配结果
        """
        try:
            # 检查插件是否启用
            if not self.is_enabled():
                return
            await self.func(messenger, matches)
        except Exception as e:
            logger.error(f"消息处理器执行失败: {self.func.__name__}, 错误: {e}\n{logger._format_exception(e)}")
            raise


class Plugin:
    """插件主类"""
    
    def __init__(
        self,
        url: str,
        token: str = '',
        debug: bool = False,
        max_concurrent: int = DefaultValue.MAX_CONCURRENT,
        max_reconnect_attempts: int = DefaultValue.MAX_RECONNECT_ATTEMPTS,
        initial_reconnect_delay: float = DefaultValue.INITIAL_RECONNECT_DELAY,
        max_reconnect_delay: float = DefaultValue.MAX_RECONNECT_DELAY
    ):
        """
        初始化插件
        
        Args:
            url: WebSocket 服务器地址
            token: 访问令牌
            debug: 调试模式（显示 debug 日志并启用热重载）
            max_concurrent: 最大并发数
            max_reconnect_attempts: 最大重连次数（-1 表示无限重连）
            initial_reconnect_delay: 初始重连延迟（秒）
            max_reconnect_delay: 最大重连延迟（秒）
        """
        self.url = url
        self.token = token
        self.debug = debug
        
        self.client = NapCatClient(
            url,
            token,
            max_reconnect_attempts=max_reconnect_attempts,
            initial_reconnect_delay=initial_reconnect_delay,
            max_reconnect_delay=max_reconnect_delay
        )
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
        # Sender 实例
        self._sender = Sender(self.client.api)
        
        # 消息处理器
        self._message_handlers: List[MessageHandler] = []
        
        # 运行状态
        self._running = False
        
        # 热重载
        self._hotreload_enabled = False
        
        # 注册事件处理器
        self.client.register_event_handler(PostType.MESSAGE.value, self._on_message)
        self.client.register_event_handler(PostType.NOTICE.value, self._on_notice)
        self.client.register_event_handler(PostType.REQUEST.value, self._on_request)
    
    def on_msg(self, pattern: str, priority: int = 0, block: bool = True):
        """
        消息处理装饰器
        
        Args:
            pattern: 正则表达式模式
            priority: 优先级（数字越大优先级越高）
            block: 是否阻止后续处理器执行
        """
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(messenger: Messenger, matches: re.Match):
                # 检查插件是否启用（通过 func.__self__ 获取插件实例）
                if hasattr(func, '__self__') and hasattr(func.__self__, 'is_enabled'):
                    if not func.__self__.is_enabled():
                        return
                async with self.semaphore:
                    await func(messenger, matches)
            
            handler = MessageHandler(pattern, wrapper, priority, block, plugin_instance=None)
            self._message_handlers.append(handler)
            self._message_handlers.sort(key=lambda h: h.priority, reverse=True)
            
            logger.info(f"注册消息处理器: {func.__name__}, pattern: {pattern}, priority: {priority}")
            return func
        
        return decorator
    
    def on_group_msg(self, pattern: str, priority: int = 0, block: bool = True):
        """
        群消息处理装饰器
        
        Args:
            pattern: 正则表达式模式
            priority: 优先级
            block: 是否阻止后续处理器
        """
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(messenger: Messenger, matches: re.Match):
                if messenger.type != MessageType.GROUP:
                    return
                # 检查插件是否启用
                if hasattr(func, '__self__') and hasattr(func.__self__, 'is_enabled'):
                    if not func.__self__.is_enabled():
                        return
                async with self.semaphore:
                    await func(messenger, matches)
            
            handler = MessageHandler(pattern, wrapper, priority, block, plugin_instance=None)
            self._message_handlers.append(handler)
            self._message_handlers.sort(key=lambda h: h.priority, reverse=True)
            
            logger.info(f"注册群消息处理器: {func.__name__}, pattern: {pattern}, priority: {priority}")
            return func
        
        return decorator
    
    def on_private_msg(self, pattern: str, priority: int = 0, block: bool = True):
        """
        私聊消息处理装饰器
        
        Args:
            pattern: 正则表达式模式
            priority: 优先级
            block: 是否阻止后续处理器
        """
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(messenger: Messenger, matches: re.Match):
                if messenger.type != MessageType.PRIVATE:
                    return
                # 检查是否启用
                if hasattr(func, '__self__') and hasattr(func.__self__, 'is_enabled'):
                    if not func.__self__.is_enabled():
                        return
                async with self.semaphore:
                    await func(messenger, matches)
            
            handler = MessageHandler(pattern, wrapper, priority, block, plugin_instance=None)
            self._message_handlers.append(handler)
            self._message_handlers.sort(key=lambda h: h.priority, reverse=True)
            
            logger.info(f"注册私聊消息处理器: {func.__name__}, pattern: {pattern}, priority: {priority}")
            return func
        
        return decorator
    
    def on_notice(self, func: Callable = None, notice_type: Optional[str] = None):
        """
        通知事件处理装饰器
        
        Args:
            func: 处理函数
            notice_type: 通知类型（可选）
        """
        def decorator(f: Callable):
            @wraps(f)
            async def wrapper(data: Dict[str, Any]):
                if notice_type and data.get('notice_type') != notice_type:
                    return
                async with self.semaphore:
                    await f(data)
            
            self.client.register_event_handler(PostType.NOTICE.value, wrapper)
            logger.info(f"注册通知处理器: {f.__name__}, type: {notice_type or 'all'}")
            return f
        
        if func is not None:
            return decorator(func)
        return decorator
    
    def on_request(self, func: Callable = None, request_type: Optional[str] = None):
        """
        请求事件处理装饰器
        
        Args:
            func: 处理函数
            request_type: 请求类型（可选）
        """
        def decorator(f: Callable):
            @wraps(f)
            async def wrapper(data: Dict[str, Any]):
                if request_type and data.get('request_type') != request_type:
                    return
                async with self.semaphore:
                    await f(data)
            
            self.client.register_event_handler(PostType.REQUEST.value, wrapper)
            logger.info(f"注册请求处理器: {f.__name__}, type: {request_type or 'all'}")
            return f
        
        if func is not None:
            return decorator(func)
        return decorator
    
    async def _on_message(self, data: Dict[str, Any]):
        """
        处理消息事件
        
        Args:
            data: 事件数据
        """
        # 创建 Messenger
        messenger = Messenger(data)
        
        # 提取消息文本
        message_text = messenger.raw_message
        
        # 匹配处理器
        for handler in self._message_handlers:
            matches = handler.match(message_text)
            if matches:
                try:
                    await handler.handle(messenger, matches)
                    
                    # 如果需要阻止后续处理器，则退出
                    if handler.block:
                        break
                except Exception as e:
                    logger.error(f"处理消息时出错: {e}\n{logger._format_exception(e)}")
    
    async def _on_notice(self, data: Dict[str, Any]):
        """
        处理通知事件
        
        Args:
            data: 事件数据
        """
        notice_type = data.get('notice_type')
        logger.debug(f"收到通知事件: {notice_type}")
    
    async def _on_request(self, data: Dict[str, Any]):
        """
        处理请求事件
        
        Args:
            data: 事件数据
        """
        request_type = data.get('request_type')
        logger.debug(f"收到请求事件: {request_type}")
    
    @property
    def api(self) -> OneBotAPI:
        """获取 API 实例"""
        return self.client.api
    
    def get_sender(self) -> Sender:
        """
        获取消息发送器
        
        Returns:
            Sender 实例
        """
        return self._sender
    
    async def run(self):
        """
        运行插件（启动并保持运行）
        
        注意：此方法会阻塞，直到调用 stop()
        """
        self._running = True
        
        # 启用热重载（debug 模式）
        if self.debug and not self._hotreload_enabled:
            try:
                from .reload import HotReload
                if HotReload.enable():
                    self._hotreload_enabled = True
                    logger.info("热重载已启用", tag="reload")
                else:
                    logger.warning("热重载不可用，请安装 watchdog: pip install watchdog", tag="reload")
            except ImportError:
                logger.warning("热重载不可用，请安装 watchdog: pip install watchdog", tag="reload")
        
        try:
            logger.info("正在启动插件...")
            logger.info(f"WebSocket URL: {self.url}")
            logger.info(f"Debug 模式: {self.debug}")
            await self.client.start()
        except asyncio.CancelledError:
            logger.info("插件运行被取消")
        except Exception as e:
            logger.error(f"插件运行时出错: {e}")
            raise
        finally:
            self._running = False
            # 停用热重载
            if self._hotreload_enabled:
                try:
                    from .reload import HotReload
                    HotReload.disable()
                    self._hotreload_enabled = False
                except ImportError:
                    pass
            logger.info("插件已停止")
    
    async def start(self):
        """
        启动插件（非阻塞）
        
        Returns:
            运行任务
        """
        self._running = True
        return asyncio.create_task(self.client.start())
    
    async def stop(self):
        """停止插件"""
        if not self._running:
            logger.info("插件未在运行")
            return
        
        logger.info("正在停止插件...")
        self._running = False
        await self.client.stop()
    
    def is_running(self) -> bool:
        """检查插件是否在运行"""
        return self._running
    
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self.client.is_connected()
    
    async def check_latency(self) -> int:
        """
        检查 WebSocket 延迟
        
        Returns:
            延迟时间（毫秒），如果未连接返回 -1
        """
        if not self.is_connected():
            return -1
        
        try:
            start_time = asyncio.get_event_loop().time()
            # 发送一个简单的 API 请求来测试延迟
            await self.api.get_status()
            end_time = asyncio.get_event_loop().time()
            return int((end_time - start_time) * 1000)
        except Exception:
            return -1