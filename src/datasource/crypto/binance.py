"""
币安数据源适配器

TODO: M1 里程碑实现
"""
from datetime import datetime
from typing import AsyncIterator
import pandas as pd

from ..base import MarketDataProvider
from ..models import Ticker, OrderBook, Kline
from ..exceptions import RateLimitError


class BinanceProvider(MarketDataProvider):
    """币安交易所数据提供者"""

    def __init__(self, api_key: str = "", api_secret: str = ""):
        """
        初始化币安提供者

        Args:
            api_key: API 密钥（可选，公开数据不需要）
            api_secret: API 密钥（可选）
        """
        self.api_key = api_key
        self.api_secret = api_secret
        # TODO: 初始化 ccxt 或 python-binance 客户端

    @property
    def name(self) -> str:
        return "binance"

    @property
    def market_type(self) -> str:
        return "crypto"

    def get_klines(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime,
        limit: int = 1000
    ) -> pd.DataFrame:
        """获取历史 K 线 - TODO: M1 实现"""
        raise NotImplementedError("BinanceProvider.get_klines() not implemented yet")

    def get_ticker(self, symbol: str) -> Ticker:
        """获取 ticker - TODO: M1 实现"""
        raise NotImplementedError("BinanceProvider.get_ticker() not implemented yet")

    def get_orderbook(self, symbol: str, depth: int = 20) -> OrderBook:
        """获取订单簿 - TODO: M1 实现"""
        raise NotImplementedError("BinanceProvider.get_orderbook() not implemented yet")

    async def stream_klines(self, symbol: str, interval: str) -> AsyncIterator[Kline]:
        """实时 K 线流 - TODO: M3 实现"""
        raise NotImplementedError("BinanceProvider.stream_klines() not implemented yet")
        yield  # Make it a generator

    async def stream_ticker(self, symbol: str) -> AsyncIterator[Ticker]:
        """实时 ticker 流 - TODO: M3 实现"""
        raise NotImplementedError("BinanceProvider.stream_ticker() not implemented yet")
        yield  # Make it a generator

    def list_symbols(self) -> list[str]:
        """列出交易对 - TODO: M1 实现"""
        raise NotImplementedError("BinanceProvider.list_symbols() not implemented yet")

    def normalize_symbol(self, raw_symbol: str) -> str:
        """BTCUSDT → BTC/USDT"""
        # 简化实现，实际需要查询交易所的市场信息
        if "USDT" in raw_symbol:
            return raw_symbol.replace("USDT", "/USDT")
        return raw_symbol

    def denormalize_symbol(self, standard_symbol: str) -> str:
        """BTC/USDT → BTCUSDT"""
        return standard_symbol.replace("/", "")
