"""
美股数据源适配器

预留接口，M9 里程碑实现
"""
from datetime import datetime
from typing import AsyncIterator
import pandas as pd

from ..base import MarketDataProvider
from ..models import Ticker, OrderBook, Kline


class USStockProvider(MarketDataProvider):
    """美股数据提供者（预留）"""

    @property
    def name(self) -> str:
        return "us_stock"

    @property
    def market_type(self) -> str:
        return "stock"

    def get_klines(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime,
        limit: int = 1000
    ) -> pd.DataFrame:
        raise NotImplementedError("US stock provider not implemented yet (M9)")

    def get_ticker(self, symbol: str) -> Ticker:
        raise NotImplementedError("US stock provider not implemented yet (M9)")

    def get_orderbook(self, symbol: str, depth: int = 20) -> OrderBook:
        raise NotImplementedError("US stock provider not implemented yet (M9)")

    async def stream_klines(self, symbol: str, interval: str) -> AsyncIterator[Kline]:
        raise NotImplementedError("US stock provider not implemented yet (M9)")
        yield

    async def stream_ticker(self, symbol: str) -> AsyncIterator[Ticker]:
        raise NotImplementedError("US stock provider not implemented yet (M9)")
        yield

    def list_symbols(self) -> list[str]:
        raise NotImplementedError("US stock provider not implemented yet (M9)")

    def normalize_symbol(self, raw_symbol: str) -> str:
        return raw_symbol  # TODO: 根据实际数据源调整

    def denormalize_symbol(self, standard_symbol: str) -> str:
        return standard_symbol
