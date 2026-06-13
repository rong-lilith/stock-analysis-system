"""
测试数据源抽象层

使用 Mock 提供者进行单元测试，不依赖真实网络
"""
import pytest
from datetime import datetime, timedelta
from tests.mocks.mock_provider import MockProvider


def test_mock_provider_basic():
    """测试 Mock 提供者基础属性"""
    provider = MockProvider()
    assert provider.name == "mock"
    assert provider.market_type == "crypto"


def test_get_klines():
    """测试获取 K 线数据"""
    provider = MockProvider()

    end = datetime.now()
    start = end - timedelta(days=7)

    df = provider.get_klines(
        symbol="BTC/USDT",
        interval="1d",
        start=start,
        end=end,
        limit=100
    )

    # 验证返回的 DataFrame 结构
    assert not df.empty
    assert all(col in df.columns for col in ["open", "high", "low", "close", "volume"])
    assert df.index.tz is not None  # 确保有时区信息


def test_get_ticker():
    """测试获取 ticker"""
    provider = MockProvider()
    ticker = provider.get_ticker("BTC/USDT")

    assert ticker.symbol == "BTC/USDT"
    assert ticker.last_price > 0
    assert ticker.bid < ticker.ask


def test_get_orderbook():
    """测试获取订单簿"""
    provider = MockProvider()
    orderbook = provider.get_orderbook("BTC/USDT", depth=10)

    assert len(orderbook.bids) == 10
    assert len(orderbook.asks) == 10
    assert orderbook.bids[0][0] < orderbook.asks[0][0]  # bid < ask


def test_list_symbols():
    """测试列出交易对"""
    provider = MockProvider()
    symbols = provider.list_symbols()

    assert len(symbols) > 0
    assert "BTC/USDT" in symbols


@pytest.mark.asyncio
async def test_stream_klines():
    """测试实时 K 线流"""
    provider = MockProvider()

    count = 0
    async for kline in provider.stream_klines("BTC/USDT", "1m"):
        assert kline.symbol == "BTC/USDT"
        assert kline.interval == "1m"
        count += 1
        if count >= 3:
            break

    assert count == 3
