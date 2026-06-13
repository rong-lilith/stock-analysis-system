"""
标准数据模型

所有市场数据源返回统一的数据结构
"""
from pydantic import BaseModel, Field
from datetime import datetime


class Kline(BaseModel):
    """K 线标准模型"""
    symbol: str
    interval: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    closed: bool = False  # 是否已收盘（实时流需要）


class Ticker(BaseModel):
    """行情快照标准模型"""
    symbol: str
    last_price: float
    bid: float
    ask: float
    volume_24h: float
    change_24h_percent: float
    high_24h: float
    low_24h: float
    timestamp: datetime


class OrderBook(BaseModel):
    """订单簿标准模型"""
    symbol: str
    bids: list[tuple[float, float]]  # [(price, quantity), ...]
    asks: list[tuple[float, float]]
    timestamp: datetime
