"""
OKX 数据源适配器

TODO: M1 里程碑实现
"""
from datetime import datetime
from typing import AsyncIterator
import pandas as pd

from ..base import MarketDataProvider
from ..models import Ticker, OrderBook, Kline


class OKXProvider(MarketDataProvider):
    """OKX 交易所数据提供者"""

    def __init__(self, api_key: str = "", api_secret: str = "", passphrase: str = ""):
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase
        # TODO: 初始化 ccxt 或 python-okx 客户端

    @property
    def name(self) -> str:
        return "okx"

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
        raise NotImplementedError("OKXProvider.get_klines() not implemented yet")

    def get_ticker(self, symbol: str) -> Ticker:
        raise NotImplementedError("OKXProvider.get_ticker() not implemented yet")

    def get_orderbook(self, symbol: str, depth: int = 20) -> OrderBook:
        raise NotImplementedError("OKXProvider.get_orderbook() not implemented yet")

    async def stream_klines(self, symbol: str, interval: str) -> AsyncIterator[Kline]:
        raise NotImplementedError("OKXProvider.stream_klines() not implemented yet")
        yield

    async def stream_ticker(self, symbol: str) -> AsyncIterator[Ticker]:
        raise NotImplementedError("OKXProvider.stream_ticker() not implemented yet")
        yield

    def list_symbols(self) -> list[str]:
        raise NotImplementedError("OKXProvider.list_symbols() not implemented yet")

    def normalize_symbol(self, raw_symbol: str) -> str:
        """BTC-USDT → BTC/USDT"""
        return raw_symbol.replace("-", "/")

    def denormalize_symbol(self, standard_symbol: str) -> str:
        """BTC/USDT → BTC-USDT"""
        return standard_symbol.replace("/", "-")
