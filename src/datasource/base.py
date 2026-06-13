"""
数据源抽象基类

定义所有市场数据提供者必须实现的接口
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import AsyncIterator
import pandas as pd

from .models import Ticker, OrderBook, Kline


class MarketDataProvider(ABC):
    """市场数据提供者抽象基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """数据源名称，如 'binance' / 'okx' / 'us_stock'"""
        pass

    @property
    @abstractmethod
    def market_type(self) -> str:
        """市场类型：'crypto' / 'stock'"""
        pass

    # ===== REST API 方法 =====

    @abstractmethod
    def get_klines(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime,
        limit: int = 1000
    ) -> pd.DataFrame:
        """
        获取历史 K 线数据

        Args:
            symbol: 标准格式交易对，如 'BTC/USDT'
            interval: 时间周期，如 '1m', '1h', '1d'
            start: 开始时间 (UTC)
            end: 结束时间 (UTC)
            limit: 单次最大条数

        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
            Index: DatetimeIndex (UTC)
        """
        pass

    @abstractmethod
    def get_ticker(self, symbol: str) -> Ticker:
        """获取最新 ticker（24h 统计）"""
        pass

    @abstractmethod
    def get_orderbook(self, symbol: str, depth: int = 20) -> OrderBook:
        """获取订单簿快照"""
        pass

    # ===== WebSocket 方法 =====

    @abstractmethod
    async def stream_klines(
        self,
        symbol: str,
        interval: str
    ) -> AsyncIterator[Kline]:
        """实时 K 线流（WebSocket）"""
        pass

    @abstractmethod
    async def stream_ticker(self, symbol: str) -> AsyncIterator[Ticker]:
        """实时 ticker 流"""
        pass

    # ===== 元数据方法 =====

    @abstractmethod
    def list_symbols(self) -> list[str]:
        """列出所有可用交易对/股票代码（标准格式）"""
        pass

    @abstractmethod
    def normalize_symbol(self, raw_symbol: str) -> str:
        """交易所原始符号 → 内部标准格式"""
        pass

    @abstractmethod
    def denormalize_symbol(self, standard_symbol: str) -> str:
        """内部标准格式 → 交易所原始符号"""
        pass
