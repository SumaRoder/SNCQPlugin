"""
WebSocket 客户端
"""

import asyncio
import websockets
import json
import logging
from typing import Callable, Optional, Dict, Any, List
from .api import OneBotAPI
from .logger import Logger
from .exceptions import ConnectionError
from .constants import (
    PostType,
    ReconnectConfig,
    WebSocketConfig,
    DefaultValue
)

logger = Logger(name=__name__, path="client.log")


class NapCatClient:
    """NapCatQQ WebSocket 客户端"""
    
    def __init__(
        self,
        url: str,
        access_token: str = '',
        max_reconnect_attempts: int = DefaultValue.MAX_RECONNECT_ATTEMPTS,
        initial_reconnect_delay: float = DefaultValue.INITIAL_RECONNECT_DELAY,
        max_reconnect_delay: float = DefaultValue.MAX_RECONNECT_DELAY
    ):
        """
        初始化客户端
        
        Args:
            url: WebSocket 服务器地址
            access_token: 访问令牌
            max_reconnect_attempts: 最大重连次数（-1 表示无限重连）
            initial_reconnect_delay: 初始重连延迟（秒）
            max_reconnect_delay: 最大重连延迟（秒）
        """
        self.url = url
        self.access_token = access_token
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.connected = False
        self.reconnect_attempts = 0
        
        # 重连配置
        self.reconnect_config = ReconnectConfig(
            max_attempts=max_reconnect_attempts,
            initial_delay=initial_reconnect_delay,
            max_delay=max_reconnect_delay
        )
        
        # WebSocket 配置
        self.ws_config = WebSocketConfig()
        
        # 事件处理器
        self._event_handlers: Dict[PostType, List[Callable]] = {
            PostType.MESSAGE: [],
            PostType.MESSAGE_SENT: [],
            PostType.NOTICE: [],
            PostType.REQUEST: [],
            PostType.META_EVENT: []
        }
        
        # API 响应等待器: {echo: asyncio.Future}
        self._api_waiters: Dict[int, asyncio.Future] = {}
        
        # API 实例
        self.api = OneBotAPI(self._send_payload)
        
        # 运行状态
        self._running = False
        self._listen_task: Optional[asyncio.Task] = None
    
    async def connect(self) -> bool:
        """
        连接到服务器
        
        Returns:
            是否连接成功
        """
        try:
            # 添加 access_token 到 URL
            if self.access_token:
                url_with_token = f"{self.url}?access_token={self.access_token}"
            else:
                url_with_token = self.url
            
            self.websocket = await websockets.connect(
                url_with_token,
                ping_interval=self.ws_config.ping_interval,
                ping_timeout=self.ws_config.ping_timeout,
                close_timeout=self.ws_config.close_timeout
            )
            self.connected = True
            self.reconnect_attempts = 0
            logger.info(f"成功连接到 NapCatQQ: {self.url}")
            return True
            
        except Exception as e:
            logger.error(f"连接失败: {e}")
            self.connected = False
            return False
    
    async def disconnect(self):
        """断开连接"""
        if self.websocket:
            try:
                await self.websocket.close()
            except Exception as e:
                logger.error(f"关闭连接时出错: {e}")
            finally:
                self.connected = False
                self.websocket = None
                logger.info("已断开与 NapCatQQ 的连接")
    
    async def reconnect(self) -> bool:
        """
        重连（指数退避）
        
        Returns:
            是否重连成功
        """
        if self.reconnect_config.max_attempts != -1 and self.reconnect_attempts >= self.reconnect_config.max_attempts:
            logger.error(f"达到最大重连次数 ({self.reconnect_config.max_attempts})，放弃重连")
            return False
        
        self.reconnect_attempts += 1
        
        # 指数退避：delay = initial_delay * 2^(attempts-1)
        delay = self.reconnect_config.initial_delay * (2 ** (self.reconnect_attempts - 1))
        wait_time = min(delay, self.reconnect_config.max_delay)
        
        logger.info(f"等待 {wait_time:.1f} 秒后尝试第 {self.reconnect_attempts} 次重连...")
        
        await asyncio.sleep(wait_time)
        return await self.connect()
    
    async def _send_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        发送消息载荷并等待响应
        
        Args:
            payload: 消息载荷
        
        Returns:
            API 响应
        """
        if not self.connected or not self.websocket:
            raise ConnectionError("未连接到服务器")
        
        echo = payload.get('echo')
        if echo is None:
            raise ValueError("Payload 必须包含 echo 字段")
        
        # 创建一个 Future 来等待响应
        future = asyncio.Future()
        self._api_waiters[echo] = future
        
        # 先发送消息
        await self.websocket.send(json.dumps(payload))
        logger.debug(f"已发送: {payload.get('action')}, echo: {echo}")
        
        # 等待响应，超时时间 30 秒
        # 使用 asyncio.shield 保护 future 不被取消
        try:
            # 创建一个后台任务来检查 future，这样即使当前协程被阻塞，
            # listen 协程仍然可以接收消息并设置 future
            response = await asyncio.wait_for(
                asyncio.shield(future),
                timeout=30.0
            )
            return response
        except asyncio.TimeoutError:
            logger.error(f"API 响应超时: echo={echo}")
            raise TimeoutError(f"API 响应超时: {payload.get('action')}")
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            raise ConnectionError(f"发送消息失败: {e}")
        finally:
            # 清理等待器
            self._api_waiters.pop(echo, None)
    
    def register_event_handler(self, event_type: str, handler: Callable):
        """
        注册事件处理器
        
        Args:
            event_type: 事件类型 (message, notice, request, meta_event)
            handler: 处理器函数
        """
        try:
            post_type = PostType(event_type)
        except ValueError:
            logger.warning(f"未知的事件类型: {event_type}")
            return
        
        self._event_handlers[post_type].append(handler)
        logger.info(f"已注册 {post_type.value} 事件处理器: {handler.__name__}")
    
    async def _dispatch_event(self, post_type: PostType, data: Dict[str, Any]):
        """
        分发事件到处理器（非阻塞）
        
        Args:
            post_type: 事件类型
            data: 事件数据
        """
        handlers = self._event_handlers.get(post_type, [])
        if not handlers:
            return
        
        # 使用 create_task 非阻塞地执行所有处理器
        # 这样即使处理器调用 API 并等待响应，也不会阻塞事件分发
        for handler in handlers:
            try:
                asyncio.create_task(handler(data))
            except Exception as e:
                logger.error(f"创建处理器任务时出错: {e}")
    
    async def _handle_message(self, message: str):
        """
        处理接收到的消息
        
        Args:
            message: JSON 消息字符串
        """
        try:
            data = json.loads(message)
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {e}")
            return
        
        # 处理 API 响应
        if 'echo' in data and 'retcode' in data:
            echo = data.get('echo')
            logger.debug(f"收到 API 响应: echo={echo}, retcode={data.get('retcode')}")
            
            # 检查是否有等待的 Future
            if echo in self._api_waiters:
                future = self._api_waiters[echo]
                if not future.done():
                    # 设置 Future 的结果
                    future.set_result(data)
                else:
                    logger.warning(f"Echo {echo} 的 Future 已经完成")
            else:
                logger.warning(f"没有找到 echo {echo} 对应的等待器")
            return
        
        # 处理事件消息
        post_type_str = data.get('post_type')
        if post_type_str:
            try:
                post_type = PostType(post_type_str)
                
                event_detail = f"账号[{data['self_id']}]"
                log_level = logging.INFO
                
                if post_type == PostType.MESSAGE:
                    msg_type = data.get('message_type')
                    user_id = data.get('user_id')
                    group_id = data.get('group_id')
                    raw_message = data.get('raw_message', '')
                    if msg_type == 'group':
                        event_detail += f"收到群聊[{data['group_name']}]消息: {raw_message[:50]}"
                    else:
                        event_detail += f"收到私聊[{data['sender']['nickname'] or user_id}]消息: {raw_message[:50]}"
                
                elif post_type == PostType.MESSAGE_SENT:
                    msg_type = data.get('message_type')
                    user_id = data.get('user_id')
                    group_id = data.get('group_id')
                    raw_message = data.get('raw_message', '')
                    if msg_type == 'group':
                        event_detail += f"发送群聊[{data['group_name']}]消息: {raw_message[:50]}"
                    else:
                        event_detail += f"发送私聊[{data['sender']['nickname'] or user_id}]消息: {raw_message[:50]}"
                    log_level = logging.DEBUG
                
                elif post_type == PostType.NOTICE:
                    notice_type = data.get('notice_type')
                    group_id = data.get('group_id')
                    group_name = data.get("group_name")
                    user_id = data.get('user_id')
                    if notice_type == 'group_increase':
                        event_detail += f"监听群聊[{group_name}]新用户入群: {user_id}"
                    elif notice_type == 'group_decrease':
                        event_detail += f"监听群聊[{group_name}]有用户退群: {user_id}"
                    else:
                        event_detail += f"监听群聊[{group_name}]用户: {user_id}"
                        log_level = logging.DEBUG
                
                elif post_type == PostType.REQUEST:
                    request_type = data.get('request_type')
                    user_id = data.get('user_id')
                    comment = data.get('comment', '')
                    if request_type == 'friend':
                        event_detail += f"监听好友[{user_id}]添加请求 验证信息: {comment[:30]}"
                    elif request_type == 'group':
                        event_detail += f"监听群聊[{data.get("group_name")}]入群请求 验证信息: {comment[:30]}"
                    else:
                        event_detail += f"监听用户: {user_id}"
                        log_level = logging.DEBUG
                
                elif post_type == PostType.META_EVENT:
                    meta_type = data.get('meta_event_type')
                    if meta_type == 'heartbeat':
                        self_id = data.get('self_id', 'unknown')
                        event_detail += f"发生一次心跳"
                    else:
                        event_detail += f"监听元事件:{meta_type}"
                    log_level = logging.DEBUG
                
                logger.log(event_detail, tag=post_type_str, level=log_level)
                await self._dispatch_event(post_type, data)
            except ValueError:
                logger.warning(f"未知的事件类型: {post_type_str}")
    
    async def listen(self):
        """监听消息事件"""
        if not self.websocket:
            logger.error("WebSocket 未连接")
            return
        
        try:
            async for message in self.websocket:
                try:
                    await self._handle_message(message)
                except Exception as e:
                    logger.error(f"处理消息时出错: {e}")
                    
        except websockets.exceptions.ConnectionClosed as e:
            logger.warning(f"WebSocket 连接已关闭: {e}")
            self.connected = False
        except asyncio.CancelledError:
            logger.info("监听任务被取消")
            self.connected = False
            raise
        except Exception as e:
            logger.error(f"监听消息时出错: {e}")
            self.connected = False
    
    async def start(self):
        """启动客户端（连接并开始监听）"""
        self._running = True
        
        while self._running:
            try:
                # 连接服务器
                if not await self.connect():
                    logger.error("连接失败，等待 10 秒后重试...")
                    await asyncio.sleep(10)
                    continue
                
                # 开始监听
                self._listen_task = asyncio.create_task(self.listen())
                await self._listen_task
                
            except asyncio.CancelledError:
                logger.info("客户端启动被取消")
                break
            except Exception as e:
                logger.error(f"客户端运行时出错: {e}")
                self.connected = False
                
                # 尝试重连
                if not await self.reconnect():
                    logger.error("重连失败，停止客户端")
                    break
            
            await asyncio.sleep(1)
    
    async def stop(self):
        """停止客户端"""
        logger.info("正在停止客户端...")
        self._running = False
        
        # 取消监听任务
        if self._listen_task and not self._listen_task.done():
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
        
        # 断开连接
        await self.disconnect()
        logger.info("客户端已停止")
    
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self.connected and self.websocket is not None