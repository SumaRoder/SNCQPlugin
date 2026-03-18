"""
OneBot V11 API 封装
"""

from typing import Dict, Any, Optional, List
import json
import logging

logger = logging.getLogger(__name__)


class OneBotAPI:
    """OneBot V11 API 封装类"""
    
    def __init__(self, send_callback):
        """
        初始化 API
        
        Args:
            send_callback: 发送消息的回调函数
        """
        self._send_callback = send_callback
        self._echo_counter = 0
        self._pending_requests: Dict[int, Any] = {}
    
    async def _call(self, action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        调用 API
        
        Args:
            action: API 动作名
            params: 参数
        
        Returns:
            API 响应
        """
        self._echo_counter += 1
        payload = {
            'action': action,
            'params': params or {},
            'echo': self._echo_counter
        }
        
        logger.debug(f"调用 API: {action}, echo: {self._echo_counter}")
        return await self._send_callback(payload)
    
    # ========== 消息发送 ==========
    
    async def send_group_msg(self, group_id: int, message: str) -> Dict[str, Any]:
        """发送群消息"""
        return await self._call('send_group_msg', {
            'group_id': group_id,
            'message': message
        })
    
    async def send_private_msg(self, user_id: int, message: str) -> Dict[str, Any]:
        """发送私聊消息"""
        return await self._call('send_private_msg', {
            'user_id': user_id,
            'message': message
        })
    
    async def send_group_forward_msg(self, group_id: int, messages: list) -> Dict[str, Any]:
        """发送群合并转发消息"""
        return await self._call('send_group_forward_msg', {
            'group_id': group_id,
            'messages': messages
        })
    
    async def send_private_forward_msg(self, user_id: int, messages: list) -> Dict[str, Any]:
        """发送群合并转发消息"""
        return await self._call('send_private_forward_msg', {
            'user_id': user_id,
            'messages': messages
        })
    
    # ========== 消息操作 ==========
    
    async def delete_msg(self, message_id: int) -> Dict[str, Any]:
        """撤回消息"""
        return await self._call('delete_msg', {
            'message_id': message_id
        })
    
    async def get_msg(self, message_id: int) -> Dict[str, Any]:
        """获取消息"""
        return await self._call('get_msg', {
            'message_id': message_id
        })
    
    async def get_forward_msg(self, message_id: int) -> Dict[str, Any]:
        """获取合并转发消息"""
        return await self._call('get_forward_msg', {
            'message_id': message_id
        })

    async def get_file(self, file_id: str) -> Dict[str, Any]:
        """获取文件信息"""
        return await self._call('get_file', {
            'file_id': file_id
        })

    async def get_file_url(self, file_id: str) -> Dict[str, Any]:
        """获取文件下载链接"""
        return await self._call('get_file_url', {
            'file_id': file_id
        })
    
    # ========== 群组管理 ==========
    
    async def get_group_list(self) -> Dict[str, Any]:
        """获取群列表"""
        return await self._call('get_group_list')
    
    async def get_group_info(self, group_id: int) -> Dict[str, Any]:
        """获取群信息"""
        return await self._call('get_group_info', {
            'group_id': group_id
        })
    
    async def get_group_member_info(self, group_id: int, user_id: int) -> Dict[str, Any]:
        """获取群成员信息"""
        return await self._call('get_group_member_info', {
            'group_id': group_id,
            'user_id': user_id
        })
    
    async def get_group_member_list(self, group_id: int) -> Dict[str, Any]:
        """获取群成员列表"""
        return await self._call('get_group_member_list', {
            'group_id': group_id
        })
    
    async def get_group_honor_info(self, group_id: int, type: str = 'all') -> Dict[str, Any]:
        """获取群荣誉信息"""
        return await self._call('get_group_honor_info', {
            'group_id': group_id,
            'type': type
        })
    
    async def get_group_member_card(self, group_id: int, user_id: int) -> Dict[str, Any]:
        """获取群成员名片"""
        return await self.get_group_member_info(group_id, user_id)
    
    async def set_group_card(self, group_id: int, user_id: int, card: str) -> Dict[str, Any]:
        """设置群名片"""
        return await self._call('set_group_card', {
            'group_id': group_id,
            'user_id': user_id,
            'card': card
        })
    
    async def set_group_name(self, group_id: int, group_name: str) -> Dict[str, Any]:
        """设置群名"""
        return await self._call('set_group_name', {
            'group_id': group_id,
            'group_name': group_name
        })
    
    async def set_group_admin(self, group_id: int, user_id: int, enable: bool = True) -> Dict[str, Any]:
        """设置群管理员"""
        return await self._call('set_group_admin', {
            'group_id': group_id,
            'user_id': user_id,
            'enable': enable
        })
    
    async def set_group_special_title(self, group_id: int, user_id: int, special_title: str, duration: int = -1) -> Dict[str, Any]:
        """设置群成员专属头衔"""
        return await self._call('set_group_special_title', {
            'group_id': group_id,
            'user_id': user_id,
            'special_title': special_title,
            'duration': duration
        })
    
    async def set_group_kick(self, group_id: int, user_id: int, reject_add_request: bool = False) -> Dict[str, Any]:
        """群组踢人"""
        return await self._call('set_group_kick', {
            'group_id': group_id,
            'user_id': user_id,
            'reject_add_request': reject_add_request
        })
    
    async def set_group_ban(self, group_id: int, user_id: int, duration: int = 1800) -> Dict[str, Any]:
        """群组禁言"""
        return await self._call('set_group_ban', {
            'group_id': group_id,
            'user_id': user_id,
            'duration': duration
        })
    
    async def set_group_whole_ban(self, group_id: int, enable: bool = True) -> Dict[str, Any]:
        """群组全员禁言"""
        return await self._call('set_group_whole_ban', {
            'group_id': group_id,
            'enable': enable
        })
    
    async def set_group_leave(self, group_id: int, is_dismiss: bool = False) -> Dict[str, Any]:
        """退出群组"""
        return await self._call('set_group_leave', {
            'group_id': group_id,
            'is_dismiss': is_dismiss
        })
    
    async def get_group_msg_history(self, group_id: int, message_seq: int = 0, count: int = 20) -> Dict[str, Any]:
        """获取群消息历史"""
        return await self._call('get_group_msg_history', {
            'group_id': group_id,
            'message_seq': message_seq,
            'count': count
        })
    
    # ========== 好友管理 ==========
    
    async def get_friend_list(self) -> Dict[str, Any]:
        """获取好友列表"""
        return await self._call('get_friend_list')
    
    async def get_friend_info(self, user_id: int) -> Dict[str, Any]:
        """获取好友信息"""
        return await self._call('get_friend_info', {
            'user_id': user_id
        })
    
    async def delete_friend(self, user_id: int) -> Dict[str, Any]:
        """删除好友"""
        return await self._call('delete_friend', {
            'user_id': user_id
        })
    
    # ========== 用户信息 ==========
    
    async def get_stranger_info(self, user_id: int) -> Dict[str, Any]:
        """获取陌生人信息"""
        return await self._call('get_stranger_info', {
            'user_id': user_id
        })
    
    # ========== 状态查询 ==========
    
    async def get_status(self) -> Dict[str, Any]:
        """获取运行状态"""
        return await self._call('get_status')
    
    async def get_version_info(self) -> Dict[str, Any]:
        """获取版本信息"""
        return await self._call('get_version_info')
    
    async def can_send_image(self) -> Dict[str, Any]:
        """检查是否可以发送图片"""
        return await self._call('can_send_image')
    
    async def can_send_record(self) -> Dict[str, Any]:
        """检查是否可以发送语音"""
        return await self._call('can_send_record')
    
    # ========== 处理请求 ==========
    
    async def set_friend_add_request(self, flag: str, approve: bool = True, remark: str = '') -> Dict[str, Any]:
        """处理好友添加请求"""
        return await self._call('set_friend_add_request', {
            'flag': flag,
            'approve': approve,
            'remark': remark
        })
    
    async def set_group_add_request(self, flag: str, sub_type: str, approve: bool = True, reason: str = '') -> Dict[str, Any]:
        """处理加群请求"""
        return await self._call('set_group_add_request', {
            'flag': flag,
            'sub_type': sub_type,
            'approve': approve,
            'reason': reason
        })
    
    # ========== 戳一戳 ==========
    
    async def send_group_poke(self, group_id: int, user_id: int) -> Dict[str, Any]:
        """群戳一戳"""
        return await self._call('send_group_poke', {
            'group_id': group_id,
            'user_id': user_id
        })
    
    async def send_private_poke(self, user_id: int) -> Dict[str, Any]:
        """私聊戳一戳"""
        return await self._call('send_private_poke', {
            'user_id': user_id
        })
