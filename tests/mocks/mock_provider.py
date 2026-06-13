"""
Mock 数据源提供者（用于测试）

返回固定的合成数据，不访问真实网络
"""
from datetime import datetime, timedelta
from typing import AsyncIterator
import pandas as pd

from src.datasource.base import MarketDataProvider
from src.datasource.models import Ticker, OrderBook, Kline


class MockProvider(MarketDataProvider):
    """Mock 数据提供者，用于单元测试"""

    @property
    def name(self) -> str:
        return "mock"

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
        """返回合成的 K 线数据"""
        # 生成日期范围
        freq_map = {
            "1m": "1min",
            "5m": "5min",
            "15m": "15min",
            "1h": "1H",
            "4h": "4H",
            "1d": "1D",
        }
        freq = freq_map.get(interval, "1D")

        dates = pd.date_range(start, end, freq=freq, tz="UTC")

        # 生成简单的价格数据（随机游走）
        import numpy as np
        np.random.seed(42)  # 可复现

        base_price = 100.0
        returns = np.random.normal(0.001, 0.02, len(dates))
        closes = base_price * np.exp(np.cumsum(returns))

        df = pd.DataFrame({
            "open": closes * 0.99,
            "high": closes * 1.02,
            "low": closes * 0.98,
            "close": closes,
            "volume": np.random.uniform(1000, 5000, len(dates)),
        }, index=dates)

        return df[:limit]

    def get_ticker(self, symbol: str) -> Ticker:
        """返回固定的 ticker 数据"""
        return Ticker(
            symbol=symbol,
            last_price=100.0,
            bid=99.9,
            ask=100.1,
            volume_24h=50000.0,
            change_24h_percent=2.5,
            high_24h=105.0,
            low_24h=95.0,
            timestamp=datetime.now()
        )

    def get_orderbook(self, symbol: str, depth: int = 20) -> OrderBook:
        """返回固定的订单簿"""
        bids = [(100.0 - i * 0.1, 10.0 + i) for i in range(depth)]
        asks = [(100.0 + i * 0.1, 10.0 + i) for i in range(depth)]

        return OrderBook(
            symbol=symbol,
            bids=bids,
            asks=asks,
            timestamp=datetime.now()
        )

    async def stream_klines(self, symbol: str, interval: str) -> AsyncIterator[Kline]:
        """Mock 实时 K 线流"""
        for i in range(5):  # 只返回 5 条数据
            yield Kline(
                symbol=symbol,
                interval=interval,
                timestamp=datetime.now(),
                open=100.0,
                high=105.0,
                low=95.0,
                close=102.0,
                volume=1000.0,
                closed=False
            )

    async def stream_ticker(self, symbol: str) -> AsyncIterator[Ticker]:
        """Mock 实时 ticker 流"""
        for i in range(5):
            yield self.get_ticker(symbol)

    def list_symbols(self) -> list[str]:
        """返回模拟的交易对列表"""
        return ["BTC/USDT", "ETH/USDT", "BNB/USDT"]

    def normalize_symbol(self, raw_symbol: str) -> str:
        return raw_symbol

    def denormalize_symbol(self, standard_symbol: str) -> str:
        return standard_symbol
