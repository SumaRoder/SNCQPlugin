"""
SNCQPlugin - NapCatQQ (OneBot V11) WebSocket 插件库
"""

from .plugin import Plugin
from .messenger import Messenger, MessengerBuilder
from .api import OneBotAPI
from .client import NapCatClient
from .sender import Sender
from .reload import HotReload
from .constants import (
    PostType,
    MessageType,
    NoticeType,
    RequestType,
    MetaEventType,
    CQCodeType,
    ImageType,
    MusicType,
    APIAction,
    ReconnectConfig,
    WebSocketConfig,
    PluginConfig,
    Priority,
    GroupDecreaseSubType,
    GroupAdminSubType,
    MemberBanSubType,
    GroupAddRequestSubType,
    CQCodePrefix,
    DefaultValue
)

__version__ = '0.3.0'
__all__ = [
    'Plugin',
    'Messenger',
    'MessengerBuilder',
    'OneBotAPI',
    'NapCatClient',
    'Sender',
    'HotReload',
    'PostType',
    'MessageType',
    'NoticeType',
    'RequestType',
    'MetaEventType',
    'CQCodeType',
    'ImageType',
    'MusicType',
    'APIAction',
    'ReconnectConfig',
    'WebSocketConfig',
    'PluginConfig',
    'Priority',
    'GroupDecreaseSubType',
    'GroupAdminSubType',
    'MemberBanSubType',
    'GroupAddRequestSubType',
    'CQCodePrefix',
    'DefaultValue'
]