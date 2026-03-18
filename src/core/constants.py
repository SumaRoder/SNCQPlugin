"""
常量定义 - 枚举和数据类
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional


# ========== 事件类型 ==========

class PostType(Enum):
    """事件类型"""
    MESSAGE = "message"
    MESSAGE_SENT = "message_sent"
    NOTICE = "notice"
    REQUEST = "request"
    META_EVENT = "meta_event"


# ========== 消息类型 ==========

class MessageType(Enum):
    """消息类型"""
    GROUP = "group"
    PRIVATE = "private"
    UNKNOWN = "unknown"


# ========== 通知类型 ==========

class NoticeType(Enum):
    """通知类型"""
    GROUP_INCREASE = "group_increase"  # 群成员增加
    GROUP_DECREASE = "group_decrease"  # 群成员减少
    GROUP_ADMIN = "group_admin"  # 群管理员变动
    MEMBER_BAN = "member_ban"  # 群成员禁言
    FRIEND_ADD = "friend_add"  # 好友添加
    GROUP_MSG_DELETE = "group_msg_delete"  # 群消息撤回
    PRIVATE_MSG_DELETE = "private_msg_delete"  # 私聊消息撤回
    GROUP_ESSENCE = "group_essence"  # 群精华消息
    GROUP_CARD = "group_card"  # 群名片更新
    OFFLINE_FILE = "offline_file"  # 离线文件上传
    CLIENT_STATUS = "client_status"  # 客户端状态
    ESSENCE = "essence"  # 精华消息
    NOTIFY = "notify"  # 提醒事件


# ========== 请求类型 ==========

class RequestType(Enum):
    """请求类型"""
    FRIEND = "friend"  # 好友请求
    GROUP = "group"  # 加群请求


# ========== 元事件类型 ==========

class MetaEventType(Enum):
    """元事件类型"""
    LIFECYCLE = "lifecycle"  # 生命周期
    HEARTBEAT = "heartbeat"  # 心跳


# ========== 生命周期子类型 ==========

class LifecycleSubType(Enum):
    """生命周期子类型"""
    ENABLE = "enable"  # 启用
    DISABLE = "disable"  # 禁用
    CONNECT = "connect"  # 连接


# ========== CQ 码类型 ==========

class CQCodeType(Enum):
    """CQ 码类型"""
    TEXT = "text"
    AT = "at"
    IMAGE = "image"
    RECORD = "record"
    VIDEO = "video"
    FACE = "face"
    SHARE = "share"
    MUSIC = "music"
    FORWARD = "forward"
    JSON = "json"
    XML = "xml"
    RED_BAG = "redbag"
    POKE = "poke"
    ANONYMOUS = "anonymous"
    CONTACT = "contact"
    LOCATION = "location"
    NODE = "node"
    CARD_IMAGE = "cardimage"
    TTS = "tts"


# ========== 图片类型 ==========

class ImageType(Enum):
    """图片类型"""
    FLASH = "flash"  # 闪图
    IMAGE = "image"  # 普通图片


# ========== 音乐类型 ==========

class MusicType(Enum):
    """音乐类型"""
    QQ = "qq"  # QQ 音乐
    NETEASE = "163"  # 网易云音乐
    CUSTOM = "custom"  # 自定义音乐


# ========== API 动作名 ==========

class APIAction(Enum):
    """OneBot API 动作名"""
    # ========== 消息发送 ==========
    SEND_GROUP_MSG = "send_group_msg"
    SEND_PRIVATE_MSG = "send_private_msg"
    SEND_GROUP_FORWARD_MSG = "send_group_forward_msg"
    
    # ========== 消息操作 ==========
    DELETE_MSG = "delete_msg"
    GET_MSG = "get_msg"
    GET_FORWARD_MSG = "get_forward_msg"
    
    # ========== 群组管理 ==========
    GET_GROUP_LIST = "get_group_list"
    GET_GROUP_INFO = "get_group_info"
    GET_GROUP_MEMBER_INFO = "get_group_member_info"
    GET_GROUP_MEMBER_LIST = "get_group_member_list"
    GET_GROUP_HONOR_INFO = "get_group_honor_info"
    SET_GROUP_CARD = "set_group_card"
    SET_GROUP_NAME = "set_group_name"
    SET_GROUP_ADMIN = "set_group_admin"
    SET_GROUP_SPECIAL_TITLE = "set_group_special_title"
    SET_GROUP_KICK = "set_group_kick"
    SET_GROUP_BAN = "set_group_ban"
    SET_GROUP_WHOLE_BAN = "set_group_whole_ban"
    SET_GROUP_LEAVE = "set_group_leave"
    GET_GROUP_MSG_HISTORY = "get_group_msg_history"
    
    # ========== 好友管理 ==========
    GET_FRIEND_LIST = "get_friend_list"
    GET_FRIEND_INFO = "get_friend_info"
    DELETE_FRIEND = "delete_friend"
    
    # ========== 用户信息 ==========
    GET_STRANGER_INFO = "get_stranger_info"
    
    # ========== 状态查询 ==========
    GET_STATUS = "get_status"
    GET_VERSION_INFO = "get_version_info"
    CAN_SEND_IMAGE = "can_send_image"
    CAN_SEND_RECORD = "can_send_record"
    
    # ========== 处理请求 ==========
    SET_FRIEND_ADD_REQUEST = "set_friend_add_request"
    SET_GROUP_ADD_REQUEST = "set_group_add_request"
    
    # ========== 戳一戳 ==========
    SEND_GROUP_POKE = "send_group_poke"
    SEND_PRIVATE_POKE = "send_private_poke"


# ========== 配置常量 ==========

@dataclass
class ReconnectConfig:
    """重连配置"""
    max_attempts: int = 10
    initial_delay: float = 1.0
    max_delay: float = 60.0
    
    def __post_init__(self):
        if self.max_attempts < -1:
            raise ValueError("max_attempts 必须 >= -1 (-1 表示无限重连)")
        if self.initial_delay <= 0:
            raise ValueError("initial_delay 必须 > 0")
        if self.max_delay <= 0:
            raise ValueError("max_delay 必须 > 0")


@dataclass
class WebSocketConfig:
    """WebSocket 配置"""
    ping_interval: int = 20
    ping_timeout: int = 60
    close_timeout: int = 10


@dataclass
class PluginConfig:
    """插件配置"""
    max_concurrent: int = 10
    reconnect: ReconnectConfig = None
    websocket: WebSocketConfig = None
    
    def __post_init__(self):
        if self.reconnect is None:
            self.reconnect = ReconnectConfig()
        if self.websocket is None:
            self.websocket = WebSocketConfig()


# ========== 消息优先级 ==========

@dataclass
class Priority:
    """消息优先级"""
    HIGHEST = 100
    HIGH = 80
    ABOVE_NORMAL = 60
    NORMAL = 50
    BELOW_NORMAL = 40
    LOW = 20
    LOWEST = 0


# ========== 群成员减少子类型 ==========

class GroupDecreaseSubType(Enum):
    """群成员减少子类型"""
    LEAVE = "leave"  # 主动退群
    KICK = "kick"  # 被踢出
    KICK_ME = "kick_me"  # 机器人被踢出


# ========== 群管理员变动子类型 ==========

class GroupAdminSubType(Enum):
    """群管理员变动子类型"""
    SET = "set"  # 设置管理员
    UNSET = "unset"  # 取消管理员


# ========== 群成员禁言子类型 ==========

class MemberBanSubType(Enum):
    """群成员禁言子类型"""
    BAN = "ban"  # 禁言
    UNBAN = "unban"  # 解禁


# ========== 群加群请求子类型 ==========

class GroupAddRequestSubType(Enum):
    """群加群请求子类型"""
    ADD = "add"  # 加群
    INVITE = "invite"  # 邀请


# ========== CQ 码前缀 ==========

class CQCodePrefix:
    """CQ 码前缀"""
    START = "[CQ:"
    END = "]"
    SEPARATOR = ","
    ASSIGN = "="


# ========== 默认值 ==========

class DefaultValue:
    """默认值"""
    MAX_RECONNECT_ATTEMPTS = 10
    INITIAL_RECONNECT_DELAY = 1.0
    MAX_RECONNECT_DELAY = 60.0
    MAX_CONCURRENT = 10
    PING_INTERVAL = 20
    PING_TIMEOUT = 60
    CLOSE_TIMEOUT = 10
    MESSAGE_PRIORITY = 50
    BAN_DURATION = 1800  # 30 分钟
    SPECIAL_TITLE_DURATION = -1  # 永久
    MSG_HISTORY_COUNT = 20
    LIKE_TIMES = 10