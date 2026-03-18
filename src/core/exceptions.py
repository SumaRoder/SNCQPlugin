"""
自定义异常
"""


class SNCQPluginError(Exception):
    """基础异常"""
    pass


class ConnectionError(SNCQPluginError):
    """连接异常"""
    pass


class APIError(SNCQPluginError):
    """API 调用异常"""
    pass


class MessageHandlerError(SNCQPluginError):
    """消息处理器异常"""
    pass