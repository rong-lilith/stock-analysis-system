"""
数据源异常定义
"""


class DataSourceError(Exception):
    """数据源基础异常"""
    pass


class RateLimitError(DataSourceError):
    """触发限流"""
    def __init__(self, retry_after: int = None):
        self.retry_after = retry_after
        super().__init__(f"Rate limit hit, retry after {retry_after}s")


class SymbolNotFoundError(DataSourceError):
    """交易对/股票代码不存在"""
    pass


class MarketClosedError(DataSourceError):
    """市场休市（仅适用于股票）"""
    pass


class AuthenticationError(DataSourceError):
    """API 密钥认证失败"""
    pass
