"""模型适配器异常类"""


class ConnectionError(Exception):
    """连接错误：表示无法连接到服务，应该立即停止处理"""
    pass


class ServiceUnavailableError(Exception):
    """服务不可用错误：表示服务暂时不可用，可能需要重试"""
    pass
