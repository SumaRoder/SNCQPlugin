"""
消息发送器
"""

from typing import Dict, Any, Optional, List, Union
import logging
from .api import OneBotAPI
from .messenger import Messenger, MessengerBuilder, MessageType
from .constants import (
    CQCodeType,
    ImageType,
    MusicType,
    CQCodePrefix,
    DefaultValue
)

logger = logging.getLogger(__name__)


class Sender:
    """消息发送器，提供各种发送方法"""
    
    def __init__(self, api: OneBotAPI):
        """
        初始化发送器
        
        Args:
            api: OneBot API 实例
        """
        self.api = api
    
    # ========== 群消息发送 ==========
    
    async def send_group_message(
        self,
        group_id: int,
        message: Union[str, MessengerBuilder, List[Dict[str, Any]]],
        auto_escape: bool = False
    ) -> Dict[str, Any]:
        """
        发送群消息
        
        Args:
            group_id: 群号
            message: 消息内容（字符串、MessengerBuilder 或消息段列表）
            auto_escape: 是否发送纯文本（不解析 CQ 码）
        
        Returns:
            API 响应
        """
        if isinstance(message, MessengerBuilder):
            message = message.to_string()
        elif isinstance(message, list):
            import json
            message = json.dumps(message, ensure_ascii=False)
        return await self.api.send_group_msg(group_id, message)
    
    async def send_group_forward_message(
        self,
        group_id: int,
        messages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        发送群合并转发消息
        
        Args:
            group_id: 群号
            messages: 消息列表
        
        Returns:
            API 响应
        """
        return await self.api.send_group_forward_msg(group_id, messages)
    
    # ========== 私聊消息发送 ==========
    
    async def send_private_message(
        self,
        user_id: int,
        message: Union[str, MessengerBuilder, List[Dict[str, Any]]],
        auto_escape: bool = False
    ) -> Dict[str, Any]:
        """
        发送私聊消息
        
        Args:
            user_id: 用户 QQ 号
            message: 消息内容（字符串、MessengerBuilder 或消息段列表）
            auto_escape: 是否发送纯文本（不解析 CQ 码）
        
        Returns:
            API 响应
        """
        if isinstance(message, MessengerBuilder):
            message = message.to_string()
        elif isinstance(message, list):
            import json
            message = json.dumps(message, ensure_ascii=False)
        return await self.api.send_private_msg(user_id, message)
    
    # ========== 基于 MessengerBuilder 的便捷发送方法 ==========
    
    async def send_group_builder(
        self,
        group_id: int,
        builder: MessengerBuilder,
        auto_escape: bool = False
    ) -> Dict[str, Any]:
        """
        使用 MessengerBuilder 发送群消息
        
        Args:
            group_id: 群号
            builder: MessengerBuilder 实例
            auto_escape: 是否发送纯文本（不解析 CQ 码）
        
        Returns:
            API 响应
        """
        return await self.send_group_message(group_id, builder, auto_escape)
    
    async def send_private_builder(
        self,
        user_id: int,
        builder: MessengerBuilder,
        auto_escape: bool = False
    ) -> Dict[str, Any]:
        """
        使用 MessengerBuilder 发送私聊消息
        
        Args:
            user_id: 用户 QQ 号
            builder: MessengerBuilder 实例
            auto_escape: 是否发送纯文本（不解析 CQ 码）
        
        Returns:
            API 响应
        """
        return await self.send_private_message(user_id, builder, auto_escape)
    
    async def reply_builder(
        self,
        messenger: Messenger,
        builder: MessengerBuilder,
        at: bool = False,
        auto_escape: bool = False
    ) -> Dict[str, Any]:
        """
        使用 MessengerBuilder 回复消息（根据 Messenger 类型自适应）
        
        Args:
            messenger: Messenger 实例
            builder: MessengerBuilder 实例
            at: 是否 @ 发送者（仅群消息有效）
            auto_escape: 是否发送纯文本
        
        Returns:
            API 响应
        """
        return await self.reply(messenger, builder, at, auto_escape)

    # ========== 基于 Messenger 的自适应发送 ==========
    
    async def reply(
        self,
        messenger: Messenger,
        message: Union[str, MessengerBuilder, List[Dict[str, Any]]],
        at: bool = False,
        auto_escape: bool = False
    ) -> Dict[str, Any]:
        """
        回复消息（根据 Messenger 类型自适应）
        
        Args:
            messenger: Messenger 实例
            message: 回复内容（字符串、MessengerBuilder 或消息段列表）
            at: 是否 @ 发送者（仅群消息有效）
            auto_escape: 是否发送纯文本
        
        Returns:
            API 响应
        """
        if isinstance(message, MessengerBuilder):
            # 如果需要 @ 且是群消息，在 MessengerBuilder 前添加
            if at and messenger.type == MessageType.GROUP:
                message = MessengerBuilder().at(messenger.user_id).text(" ")
                # 注意：这里需要重新构建，因为 MessengerBuilder 返回新实例
                # 实际使用时应该先调用 at，再继续链式调用
            message = message.to_string() if isinstance(message, MessengerBuilder) else message
        elif isinstance(message, list):
            import json
            message = json.dumps(message, ensure_ascii=False)
        
        if messenger.type == MessageType.GROUP:
            # 群消息，可选择 @ 发送者
            if at and not isinstance(message, MessengerBuilder):
                message = f"[CQ:at,qq={messenger.user_id}] {message}"
            return await self.send_group_message(messenger.group_id, message, auto_escape)
        
        elif messenger.type == MessageType.PRIVATE:
            # 私聊消息
            return await self.send_private_message(messenger.user_id, message, auto_escape)
        
        else:
            raise ValueError(f"不支持的消息类型: {messenger.type}")
    
    async def reply_with_image(
        self,
        messenger: Messenger,
        image: Union[str, MessengerBuilder],
        at: bool = False
    ) -> Dict[str, Any]:
        """
        回复图片
        
        Args:
            messenger: Messenger 实例
            image: 图片路径或 URL，或 MessengerBuilder
            at: 是否 @ 发送者（仅群消息有效）
        
        Returns:
            API 响应
        """
        if isinstance(image, MessengerBuilder):
            message = image
        else:
            message = MessengerBuilder().image(image)
        return await self.reply(messenger, message, at=at)
    
    async def reply_with_record(
        self,
        messenger: Messenger,
        record: Union[str, MessengerBuilder],
        at: bool = False
    ) -> Dict[str, Any]:
        """
        回复语音
        
        Args:
            messenger: Messenger 实例
            record: 语音路径或 URL，或 MessengerBuilder
            at: 是否 @ 发送者（仅群消息有效）
        
        Returns:
            API 响应
        """
        if isinstance(record, MessengerBuilder):
            message = record
        else:
            message = MessengerBuilder().record(record)
        return await self.reply(messenger, message, at=at)
    
    async def reply_with_video(
        self,
        messenger: Messenger,
        video: Union[str, MessengerBuilder],
        at: bool = False
    ) -> Dict[str, Any]:
        """
        回复视频
        
        Args:
            messenger: Messenger 实例
            video: 视频路径或 URL，或 MessengerBuilder
            at: 是否 @ 发送者（仅群消息有效）
        
        Returns:
            API 响应
        """
        if isinstance(video, MessengerBuilder):
            message = video
        else:
            message = MessengerBuilder().video(video)
        return await self.reply(messenger, message, at=at)
    
    async def reply_with_at(
        self,
        messenger: Messenger,
        message: Union[str, MessengerBuilder],
        qq_list: List[int]
    ) -> Dict[str, Any]:
        """
        回复并 @ 多人
        
        Args:
            messenger: Messenger 实例
            message: 消息内容（字符串或 MessengerBuilder）
            qq_list: 要 @ 的 QQ 号列表
        
        Returns:
            API 响应
        """
        if isinstance(message, MessengerBuilder):
            builder = message
        else:
            builder = MessengerBuilder().text(message)
        
        # 在消息前添加 @ 列表
        for qq in qq_list:
            builder._segments.insert(0, {
                'type': CQCodeType.AT.value,
                'data': {'qq': qq}
            })
        
        return await self.reply(messenger, builder)
    
    # ========== 戳一戳 ==========
    
    async def send_group_poke(
        self,
        group_id: int,
        user_id: int
    ) -> Dict[str, Any]:
        """
        群戳一戳
        
        Args:
            group_id: 群号
            user_id: 目标用户 QQ 号
        
        Returns:
            API 响应
        """
        return await self.api.send_group_poke(group_id, user_id)
    
    async def send_private_poke(
        self,
        user_id: int
    ) -> Dict[str, Any]:
        """
        私聊戳一戳
        
        Args:
            user_id: 目标用户 QQ 号
        
        Returns:
            API 响应
        """
        return await self.api.send_private_poke(user_id)
    
    async def poke(
        self,
        messenger: Messenger
    ) -> Dict[str, Any]:
        """
        戳发送者（根据 Messenger 类型自适应）
        
        Args:
            messenger: Messenger 实例
        
        Returns:
            API 响应
        """
        if messenger.type == MessageType.GROUP:
            return await self.send_group_poke(messenger.group_id, messenger.user_id)
        elif messenger.type == MessageType.PRIVATE:
            return await self.send_private_poke(messenger.user_id)
        else:
            raise ValueError(f"不支持的消息类型: {messenger.type}")
    
    # ========== 消息操作 ==========
    
    async def delete_message(
        self,
        message_id: int
    ) -> Dict[str, Any]:
        """
        撤回消息
        
        Args:
            message_id: 消息 ID
        
        Returns:
            API 响应
        """
        return await self.api.delete_msg(message_id)
    
    async def recall(
        self,
        messenger: Messenger
    ) -> Dict[str, Any]:
        """
        撤回消息
        
        Args:
            messenger: Messenger 实例
        
        Returns:
            API 响应
        """
        if messenger.message_id is None:
            raise ValueError("无法撤回：消息 ID 不存在")
        return await self.delete_message(messenger.message_id)
    
    # ========== CQ 码构建辅助方法 ==========
    
    @staticmethod
    def cq_at(qq: Union[int, str]) -> str:
        """
        生成 @ CQ 码
        
        Args:
            qq: QQ 号，'all' 表示 @ 全体
        
        Returns:
            CQ 码字符串
        """
        return f"{CQCodePrefix.START}{CQCodeType.AT.value}{CQCodePrefix.SEPARATOR}qq={qq}{CQCodePrefix.END}"
    
    @staticmethod
    def cq_image(file: str, type: ImageType = ImageType.FLASH) -> str:
        """
        生成图片 CQ 码
        
        Args:
            file: 图片路径或 URL
            type: 类型（flash 闪图，image 普通图片）
        
        Returns:
            CQ 码字符串
        """
        return f"{CQCodePrefix.START}{CQCodeType.IMAGE.value}{CQCodePrefix.SEPARATOR}file={file}{CQCodePrefix.SEPARATOR}type={type.value}{CQCodePrefix.END}"
    
    @staticmethod
    def cq_record(file: str) -> str:
        """
        生成语音 CQ 码
        
        Args:
            file: 语音路径或 URL
        
        Returns:
            CQ 码字符串
        """
        return f"{CQCodePrefix.START}{CQCodeType.RECORD.value}{CQCodePrefix.SEPARATOR}file={file}{CQCodePrefix.END}"
    
    @staticmethod
    def cq_video(file: str) -> str:
        """
        生成视频 CQ 码
        
        Args:
            file: 视频路径或 URL
        
        Returns:
            CQ 码字符串
        """
        return f"{CQCodePrefix.START}{CQCodeType.VIDEO.value}{CQCodePrefix.SEPARATOR}file={file}{CQCodePrefix.END}"
    
    @staticmethod
    def cq_face(id: int) -> str:
        """
        生成表情 CQ 码
        
        Args:
            id: 表情 ID
        
        Returns:
            CQ 码字符串
        """
        return f"{CQCodePrefix.START}{CQCodeType.FACE.value}{CQCodePrefix.SEPARATOR}id={id}{CQCodePrefix.END}"
    
    @staticmethod
    def cq_share(url: str, title: str, content: str = '', image: str = '') -> str:
        """
        生成分享链接 CQ 码
        
        Args:
            url: 分享链接
            title: 标题
            content: 内容描述
            image: 图片 URL
        
        Returns:
            CQ 码字符串
        """
        return f"{CQCodePrefix.START}{CQCodeType.SHARE.value}{CQCodePrefix.SEPARATOR}url={url}{CQCodePrefix.SEPARATOR}title={title}{CQCodePrefix.SEPARATOR}content={content}{CQCodePrefix.SEPARATOR}image={image}{CQCodePrefix.END}"
    
    @staticmethod
    def cq_music(type: MusicType, id: Union[int, str]) -> str:
        """
        生成音乐 CQ 码
        
        Args:
            type: 音乐类型（qq, netease, custom）
            id: 歌曲 ID
        
        Returns:
            CQ 码字符串
        """
        return f"{CQCodePrefix.START}{CQCodeType.MUSIC.value}{CQCodePrefix.SEPARATOR}type={type.value}{CQCodePrefix.SEPARATOR}id={id}{CQCodePrefix.END}"
    
    @staticmethod
    def cq_forward(id: int) -> str:
        """
        生成转发消息 CQ 码
        
        Args:
            id: 转发消息 ID
        
        Returns:
            CQ 码字符串
        """
        return f"{CQCodePrefix.START}{CQCodeType.FORWARD.value}{CQCodePrefix.SEPARATOR}id={id}{CQCodePrefix.END}"
    
    @staticmethod
    def cq_json(data: str) -> str:
        """
        生成 JSON CQ 码
        
        Args:
            data: JSON 数据
        
        Returns:
            CQ 码字符串
        """
        return f"{CQCodePrefix.START}{CQCodeType.JSON.value}{CQCodePrefix.SEPARATOR}data={data}{CQCodePrefix.END}"
    
    @staticmethod
    def cq_xml(data: str) -> str:
        """
        生成 XML CQ 码
        
        Args:
            data: XML 数据
        
        Returns:
            CQ 码字符串
        """
        return f"{CQCodePrefix.START}{CQCodeType.XML.value}{CQCodePrefix.SEPARATOR}data={data}{CQCodePrefix.END}"