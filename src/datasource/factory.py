"""
数据源工厂

根据名称返回对应的市场数据提供者实例
"""
from typing import Dict, Type
from .base import MarketDataProvider


class DataSourceFactory:
    """数据源工厂类"""

    _providers: Dict[str, Type[MarketDataProvider]] = {}

    @classmethod
    def register_provider(cls, name: str, provider_class: Type[MarketDataProvider]):
        """注册新的数据源提供者"""
        cls._providers[name] = provider_class

    @classmethod
    def get_provider(cls, name: str, **kwargs) -> MarketDataProvider:
        """
        获取数据源提供者实例

        Args:
            name: 提供者名称，如 'binance', 'okx', 'us_stock'
            **kwargs: 传递给提供者构造函数的参数

        Returns:
            MarketDataProvider 实例

        Raises:
            ValueError: 未知的提供者名称
        """
        if name not in cls._providers:
            raise ValueError(
                f"Unknown provider: {name}. "
                f"Available: {list(cls._providers.keys())}"
            )
        return cls._providers[name](**kwargs)

    @classmethod
    def list_providers(cls) -> list[str]:
        """列出所有已注册的提供者"""
        return list(cls._providers.keys())


# TODO: 在各适配器实现后，在这里导入并注册
# from .crypto.binance import BinanceProvider
# from .crypto.okx import OKXProvider
# DataSourceFactory.register_provider("binance", BinanceProvider)
# DataSourceFactory.register_provider("okx", OKXProvider)
