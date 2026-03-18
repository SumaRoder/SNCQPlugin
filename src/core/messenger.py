"""
消息传递器
"""

from typing import Dict, Any, Optional, List, Union
from .constants import MessageType, PostType, CQCodePrefix, CQCodeType


class MessengerBuilder:
    """消息构建器，支持链式调用构建消息体"""
    
    def __init__(self):
        """初始化消息构建器"""
        self._segments: List[Dict[str, Any]] = []
    
    def text(self, content: str) -> 'MessengerBuilder':
        """
        添加文本消息
        
        Args:
            content: 文本内容
        
        Returns:
            self，支持链式调用
        """
        if content:
            self._segments.append({
                'type': CQCodeType.TEXT.value,
                'data': {'text': content}
            })
        return self
    
    def image(self, uri: str, cache: bool = True) -> 'MessengerBuilder':
        """
        添加图片消息
        
        Args:
            uri: 图片 URI (file://, http://, base64://)
            cache: 是否使用缓存
        
        Returns:
            self，支持链式调用
        """
        self._segments.append({
            'type': CQCodeType.IMAGE.value,
            'data': {'file': uri, 'cache': 1 if cache else 0}
        })
        return self
    
    def video(self, uri: str, cache: bool = True, proxy: bool = True) -> 'MessengerBuilder':
        """
        添加视频消息
        
        Args:
            uri: 视频 URI (file://, http://)
            cache: 是否使用缓存
            proxy: 是否通过代理下载
        
        Returns:
            self，支持链式调用
        """
        self._segments.append({
            'type': CQCodeType.VIDEO.value,
            'data': {'file': uri, 'cache': 1 if cache else 0, 'proxy': 1 if proxy else 0}
        })
        return self
    
    def record(self, uri: str, cache: bool = True, proxy: bool = True) -> 'MessengerBuilder':
        """
        添加语音消息
        
        Args:
            uri: 语音 URI (file://, http://)
            cache: 是否使用缓存
            proxy: 是否通过代理下载
        
        Returns:
            self，支持链式调用
        """
        self._segments.append({
            'type': CQCodeType.RECORD.value,
            'data': {'file': uri, 'cache': 1 if cache else 0, 'proxy': 1 if proxy else 0}
        })
        return self
    
    def face(self, face_id: int) -> 'MessengerBuilder':
        """
        添加表情消息
        
        Args:
            face_id: 表情 ID
        
        Returns:
            self，支持链式调用
        """
        self._segments.append({
            'type': CQCodeType.FACE.value,
            'data': {'id': face_id}
        })
        return self
    
    def poke(self, qq: int) -> 'MessengerBuilder':
        """
        添加戳一戳消息（仅用于消息段，实际戳一戳需调用 API）
        
        Args:
            qq: 目标 QQ 号
        
        Returns:
            self，支持链式调用
        """
        self._segments.append({
            'type': CQCodeType.POKE.value,
            'data': {'qq': qq}
        })
        return self
    
    def at(self, user_id: Union[int, str]) -> 'MessengerBuilder':
        """
        添加 @ 消息
        
        Args:
            user_id: 用户 ID，支持数字或 'all'（全体成员）
        
        Returns:
            self，支持链式调用
        """
        self._segments.append({
            'type': CQCodeType.AT.value,
            'data': {'qq': str(user_id)}
        })
        return self
    
    def at_all(self) -> 'MessengerBuilder':
        """
        添加 @全体成员 消息
        
        Returns:
            self，支持链式调用
        """
        return self.at('all')
    
    def share(self, url: str, title: str, content: Optional[str] = None, image: Optional[str] = None) -> 'MessengerBuilder':
        """
        添加分享链接消息
        
        Args:
            url: 分享链接
            title: 标题
            content: 内容描述
            image: 图片 URL
        
        Returns:
            self，支持链式调用
        """
        data = {'url': url, 'title': title}
        if content:
            data['content'] = content
        if image:
            data['image'] = image
        
        self._segments.append({
            'type': CQCodeType.SHARE.value,
            'data': data
        })
        return self
    
    def music(self, music_type: str, music_id: Optional[int] = None, url: Optional[str] = None,
             audio: Optional[str] = None, title: Optional[str] = None, content: Optional[str] = None,
             image: Optional[str] = None) -> 'MessengerBuilder':
        """
        添加音乐消息
        
        Args:
            music_type: 音乐类型 ('qq', '163', 'custom')
            music_id: 音乐 ID（qq/163 使用）
            url: 音乐 URL（自定义音乐使用）
            audio: 音频 URL（自定义音乐使用）
            title: 标题（自定义音乐使用）
            content: 内容（自定义音乐使用）
            image: 封面图片 URL（自定义音乐使用）
        
        Returns:
            self，支持链式调用
        """
        data = {'type': music_type}
        
        if music_type in ('qq', '163'):
            if music_id is None:
                raise ValueError(f"{music_type} 音乐需要提供 music_id")
            data['id'] = music_id
        elif music_type == 'custom':
            if not url or not audio or not title:
                raise ValueError("自定义音乐需要提供 url, audio, title")
            data['url'] = url
            data['audio'] = audio
            data['title'] = title
            if content:
                data['content'] = content
            if image:
                data['image'] = image
        else:
            raise ValueError(f"不支持的音乐类型: {music_type}")
        
        self._segments.append({
            'type': CQCodeType.MUSIC.value,
            'data': data
        })
        return self
    
    def reply(self, message_id: int) -> 'MessengerBuilder':
        """
        添加回复消息
        
        Args:
            message_id: 回复的消息 ID
        
        Returns:
            self，支持链式调用
        """
        self._segments.append({
            'type': 'reply',
            'data': {'id': message_id}
        })
        return self
    
    def forward(self, messages: List[Dict[str, Any]]) -> 'MessengerBuilder':
        """
        添加转发消息
        
        Args:
            messages: 转发的消息列表
        
        Returns:
            self，支持链式调用
        """
        self._segments.append({
            'type': CQCodeType.FORWARD.value,
            'data': {'messages': messages}
        })
        return self
    
    def json(self, json_data: Union[str, Dict[str, Any]]) -> 'MessengerBuilder':
        """
        添加 JSON 消息
        
        Args:
            json_data: JSON 数据（字符串或字典）
        
        Returns:
            self，支持链式调用
        """
        if isinstance(json_data, dict):
            import json
            json_data = json.dumps(json_data, ensure_ascii=False)
        
        self._segments.append({
            'type': CQCodeType.JSON.value,
            'data': {'data': json_data}
        })
        return self
    
    def xml(self, xml_data: str) -> 'MessengerBuilder':
        """
        添加 XML 消息
        
        Args:
            xml_data: XML 数据
        
        Returns:
            self，支持链式调用
        """
        self._segments.append({
            'type': CQCodeType.XML.value,
            'data': {'data': xml_data}
        })
        return self
    
    def red_bag(self, title: str) -> 'MessengerBuilder':
        """
        添加红包消息
        
        Args:
            title: 红包标题
        
        Returns:
            self，支持链式调用
        """
        self._segments.append({
            'type': CQCodeType.RED_BAG.value,
            'data': {'title': title}
        })
        return self
    
    def contact(self, contact_type: str, user_id: Optional[int] = None, group_id: Optional[int] = None) -> 'MessengerBuilder':
        """
        添加推荐消息
        
        Args:
            contact_type: 类型 ('qq', 'group')
            user_id: 用户 ID（qq 类型使用）
            group_id: 群 ID（group 类型使用）
        
        Returns:
            self，支持链式调用
        """
        if contact_type == 'qq':
            if user_id is None:
                raise ValueError("qq 类型需要提供 user_id")
            data = {'type': 'qq', 'id': user_id}
        elif contact_type == 'group':
            if group_id is None:
                raise ValueError("group 类型需要提供 group_id")
            data = {'type': 'group', 'id': group_id}
        else:
            raise ValueError(f"不支持的联系人类型: {contact_type}")
        
        self._segments.append({
            'type': CQCodeType.CONTACT.value,
            'data': data
        })
        return self
    
    def location(self, lat: float, lon: float, title: Optional[str] = None, content: Optional[str] = None) -> 'MessengerBuilder':
        """
        添加位置消息
        
        Args:
            lat: 纬度
            lon: 经度
            title: 标题
            content: 内容描述
        
        Returns:
            self，支持链式调用
        """
        data = {'lat': lat, 'lon': lon}
        if title:
            data['title'] = title
        if content:
            data['content'] = content
        
        self._segments.append({
            'type': CQCodeType.LOCATION.value,
            'data': data
        })
        return self
    
    def build(self) -> List[Dict[str, Any]]:
        """
        构建消息段列表
        
        Returns:
            消息段列表
        """
        return self._segments.copy()
    
    def to_string(self) -> str:
        """
        将消息段列表转换为 CQ 码字符串
        
        Returns:
            CQ 码字符串
        """
        result = []
        for segment in self._segments:
            msg_type = segment['type']
            data = segment['data']
            
            if msg_type == CQCodeType.TEXT.value:
                result.append(data.get('text', ''))
            else:
                params = ','.join([f"{k}={v}" for k, v in data.items()])
                result.append(f"{CQCodePrefix.START}{msg_type},{params}{CQCodePrefix.END}")
        
        return ''.join(result)
    
    def __repr__(self) -> str:
        return f"MessengerBuilder(segments={len(self._segments)})"


class Messenger:
    """消息传递器，用于处理和解析消息"""
    
    def __init__(self, raw_data: Dict[str, Any]):
        """
        初始化 Messenger
        
        Args:
            raw_data: 原始消息数据
        """
        self._raw_data = raw_data
        self._message_type = self._determine_message_type()
    
    def _determine_message_type(self) -> MessageType:
        """确定消息类型"""
        post_type = self._raw_data.get('post_type')
        if post_type == PostType.MESSAGE.value:
            message_type = self._raw_data.get('message_type')
            if message_type == MessageType.GROUP.value:
                return MessageType.GROUP
            elif message_type == MessageType.PRIVATE.value:
                return MessageType.PRIVATE
        return MessageType.UNKNOWN
    
    @property
    def type(self) -> MessageType:
        """消息类型"""
        return self._message_type
    
    @property
    def raw_data(self) -> Dict[str, Any]:
        """原始消息数据"""
        return self._raw_data
    
    @property
    def user_id(self) -> Optional[int]:
        """发送者用户 ID"""
        return self._raw_data.get('user_id')
    
    @property
    def group_id(self) -> Optional[int]:
        """群组 ID"""
        return self._raw_data.get('group_id')
    
    @property
    def message_id(self) -> Optional[int]:
        """消息 ID"""
        return self._raw_data.get('message_id')
    
    @property
    def sender(self) -> Dict[str, Any]:
        """发送者信息"""
        return self._raw_data.get('sender', {})
    
    @property
    def nickname(self) -> str:
        """发送者昵称"""
        return self.sender.get('nickname', '')
    
    @property
    def raw_message(self) -> str:
        """原始消息内容（纯文本）"""
        return self._raw_data.get('raw_message', '')
    
    @property
    def message(self) -> List[Dict[str, Any]]:
        """消息段列表"""
        return self._raw_data.get('message', [])
    
    @property
    def self_id(self) -> Optional[int]:
        """机器人自身 ID"""
        return self._raw_data.get('self_id')
    
    @property
    def time(self) -> Optional[int]:
        """消息时间戳"""
        return self._raw_data.get('time')
    
    def extract_text(self) -> str:
        """
        提取消息中的纯文本内容
        
        Returns:
            纯文本内容
        """
        text_parts = []
        for segment in self.message:
            if segment.get('type') == 'text':
                text_parts.append(segment.get('data', {}).get('text', ''))
        return ''.join(text_parts)
    
    def extract_at_qq(self) -> List[int]:
        """
        提取消息中 @ 的 QQ 号列表
        
        Returns:
            QQ 号列表
        """
        qq_list = []
        for segment in self.message:
            if segment.get('type') == 'at':
                qq = segment.get('data', {}).get('qq')
                if qq and qq != 'all':
                    qq_list.append(int(qq))
        return qq_list
    
    def extract_image_urls(self) -> List[str]:
        """
        提取消息中的图片 URL 列表
        
        Returns:
            图片 URL 列表
        """
        urls = []
        for segment in self.message:
            if segment.get('type') == 'image':
                url = segment.get('data', {}).get('url')
                if url:
                    urls.append(url)
        return urls
    
    def __repr__(self) -> str:
        return f"Messenger(type={self.type.value}, user_id={self.user_id}, group_id={self.group_id})"