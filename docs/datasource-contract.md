# 数据源接口契约（DataSource Contract）

## 1. 设计目标

**统一抽象层**，使上层业务逻辑（指标计算、回测、可视化）完全不感知底层数据来自币安、OKX、美股还是港股。

核心原则：
1. **标准化数据模型**：所有市场返回相同结构的 DataFrame / Pydantic 模型
2. **时区统一**：内部一律 UTC，适配器负责转换
3. **符号统一**：内部用 `BTC/USDT` 格式，适配器转换为交易所格式（`BTCUSDT` / `BTC-USDT`）
4. **错误处理一致**：统一异常类型（`DataSourceError` / `RateLimitError` / `SymbolNotFoundError`）

---

## 2. 抽象基类定义

```python
# src/datasource/base.py
from abc import ABC, abstractmethod
from datetime import datetime
from typing import AsyncIterator
import pandas as pd
from .models import Ticker, OrderBook, Kline

class MarketDataProvider(ABC):
    """所有市场数据源必须实现此接口"""
    
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
        symbol: str,           # 标准格式：'BTC/USDT'
        interval: str,         # 统一枚举：'1m'/'5m'/'1h'/'1d'...
        start: datetime,       # UTC 时间
        end: datetime,         # UTC 时间
        limit: int = 1000      # 单次最大条数
    ) -> pd.DataFrame:
        """
        获取历史 K 线数据
        
        返回 DataFrame 列：
        - timestamp (datetime64[ns, UTC])
        - open (float64)
        - high (float64)
        - low (float64)
        - close (float64)
        - volume (float64)  # 基础货币成交量（BTC/USDT 中的 BTC 数量）
        
        索引：DatetimeIndex (UTC)
        """
        pass
    
    @abstractmethod
    def get_ticker(self, symbol: str) -> Ticker:
        """
        获取最新 ticker（24h 统计）
        
        返回：
        - symbol: str
        - last_price: float
        - bid: float
        - ask: float
        - volume_24h: float
        - change_24h_percent: float
        - high_24h: float
        - low_24h: float
        - timestamp: datetime (UTC)
        """
        pass
    
    @abstractmethod
    def get_orderbook(self, symbol: str, depth: int = 20) -> OrderBook:
        """
        获取订单簿快照
        
        返回：
        - symbol: str
        - bids: List[Tuple[float, float]]  # [(price, quantity), ...]
        - asks: List[Tuple[float, float]]
        - timestamp: datetime (UTC)
        """
        pass
    
    # ===== WebSocket 方法 =====
    
    @abstractmethod
    async def stream_klines(
        self,
        symbol: str,
        interval: str
    ) -> AsyncIterator[Kline]:
        """
        实时 K 线流（WebSocket）
        
        Yields:
        - Kline 模型（每根 K 线更新时推送）
        """
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
        """
        交易所原始符号 → 内部标准格式
        例如：'BTCUSDT' → 'BTC/USDT'
        """
        pass
    
    @abstractmethod
    def denormalize_symbol(self, standard_symbol: str) -> str:
        """
        内部标准格式 → 交易所原始符号
        例如：'BTC/USDT' → 'BTCUSDT'
        """
        pass
```

---

## 3. 标准数据模型

```python
# src/datasource/models.py
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
```

---

## 4. 时间周期统一枚举

```python
# src/datasource/enums.py
from enum import Enum

class Interval(str, Enum):
    """统一时间周期"""
    MINUTE_1 = "1m"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    MINUTE_30 = "30m"
    HOUR_1 = "1h"
    HOUR_4 = "4h"
    HOUR_6 = "6h"
    HOUR_12 = "12h"
    DAY_1 = "1d"
    WEEK_1 = "1w"
    MONTH_1 = "1M"
```

各适配器需映射到自己的周期格式：
- 币安：`1m` / `1h` / `1d` (与标准一致)
- OKX：`1m` / `1H` / `1D` / `1W` / `1M` (小时/天/周/月大写)
- 股票：可能是 `1min` / `1hour` / `1day`

---

## 5. 异常处理

```python
# src/datasource/exceptions.py
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
```

---

## 6. 适配器实现示例

### 6.1 币安适配器

```python
# src/datasource/crypto/binance.py
import ccxt
import pandas as pd
from datetime import datetime
from ..base import MarketDataProvider
from ..models import Ticker, OrderBook, Kline
from ..exceptions import RateLimitError

class BinanceProvider(MarketDataProvider):
    def __init__(self, api_key: str = None, api_secret: str = None):
        self.exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,  # 自动限流
        })
    
    @property
    def name(self) -> str:
        return "binance"
    
    @property
    def market_type(self) -> str:
        return "crypto"
    
    def get_klines(self, symbol: str, interval: str, 
                   start: datetime, end: datetime, limit: int = 1000) -> pd.DataFrame:
        try:
            # 标准格式 'BTC/USDT' 可直接用于 ccxt
            ohlcv = self.exchange.fetch_ohlcv(
                symbol=symbol,
                timeframe=interval,
                since=int(start.timestamp() * 1000),
                limit=limit
            )
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
            df.set_index('timestamp', inplace=True)
            return df[df.index <= end]
        except ccxt.RateLimitExceeded as e:
            raise RateLimitError(retry_after=60)
    
    def normalize_symbol(self, raw_symbol: str) -> str:
        # 币安：BTCUSDT → BTC/USDT
        return raw_symbol.replace('USDT', '/USDT')  # 简化示例
    
    def denormalize_symbol(self, standard_symbol: str) -> str:
        return standard_symbol.replace('/', '')
    
    # ... 其他方法实现
```

### 6.2 美股适配器（预留）

```python
# src/datasource/stock/us.py
from ..base import MarketDataProvider
from ..exceptions import MarketClosedError
import pandas as pd

class USStockProvider(MarketDataProvider):
    @property
    def name(self) -> str:
        return "us_stock"
    
    @property
    def market_type(self) -> str:
        return "stock"
    
    def get_klines(self, symbol: str, interval: str, 
                   start: datetime, end: datetime, limit: int = 1000) -> pd.DataFrame:
        # TODO: 实现（可用 yfinance / Alpha Vantage / Polygon）
        raise NotImplementedError("US stock provider not implemented yet")
    
    # ... 其他方法同样 raise NotImplementedError
```

---

## 7. 工厂模式使用

```python
# src/datasource/factory.py
from .base import MarketDataProvider
from .crypto.binance import BinanceProvider
from .crypto.okx import OKXProvider
from .stock.us import USStockProvider

class DataSourceFactory:
    _providers = {
        "binance": BinanceProvider,
        "okx": OKXProvider,
        "us_stock": USStockProvider,
    }
    
    @classmethod
    def get_provider(cls, name: str, **kwargs) -> MarketDataProvider:
        if name not in cls._providers:
            raise ValueError(f"Unknown provider: {name}")
        return cls._providers[name](**kwargs)
    
    @classmethod
    def register_provider(cls, name: str, provider_class: type):
        """动态注册新适配器"""
        cls._providers[name] = provider_class
```

**使用示例**：
```python
from src.datasource.factory import DataSourceFactory
from datetime import datetime, timedelta

# 创建币安提供者
binance = DataSourceFactory.get_provider("binance")

# 获取 BTC/USDT 日线（上层代码对交易所无感）
df = binance.get_klines(
    symbol="BTC/USDT",
    interval="1d",
    start=datetime.now() - timedelta(days=30),
    end=datetime.now()
)

# 后续切换到 OKX，只需改一行
okx = DataSourceFactory.get_provider("okx")
df = okx.get_klines(...)  # 接口完全一致
```

---

## 8. 测试策略

### 8.1 Mock 适配器（用于单元测试）

```python
# tests/mocks/mock_provider.py
from src.datasource.base import MarketDataProvider
import pandas as pd
from datetime import datetime

class MockProvider(MarketDataProvider):
    """返回固定数据，不访问网络"""
    
    def get_klines(self, symbol: str, interval: str, 
                   start: datetime, end: datetime, limit: int = 1000) -> pd.DataFrame:
        # 返回合成数据
        dates = pd.date_range(start, end, freq='1D', tz='UTC')
        return pd.DataFrame({
            'open': [100.0] * len(dates),
            'high': [105.0] * len(dates),
            'low': [95.0] * len(dates),
            'close': [102.0] * len(dates),
            'volume': [1000.0] * len(dates),
        }, index=dates)
```

### 8.2 集成测试（可选，需真实 API）

```python
# tests/integration/test_binance_live.py
import pytest
from src.datasource.factory import DataSourceFactory
from datetime import datetime, timedelta

@pytest.mark.integration  # 标记为集成测试，CI 可跳过
def test_binance_live():
    provider = DataSourceFactory.get_provider("binance")
    df = provider.get_klines(
        "BTC/USDT", "1d",
        datetime.now() - timedelta(days=7),
        datetime.now()
    )
    assert len(df) == 7
    assert all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume'])
```

---

## 9. 扩展指南

### 添加新交易所（如 Kraken）

1. 创建 `src/datasource/crypto/kraken.py`
2. 继承 `MarketDataProvider`，实现所有抽象方法
3. 在 `DataSourceFactory` 注册：
   ```python
   from .crypto.kraken import KrakenProvider
   DataSourceFactory.register_provider("kraken", KrakenProvider)
   ```
4. **上层代码零改动**

### 添加股票市场

1. 实现 `USStockProvider` / `HKStockProvider`
2. 处理市场特有逻辑：
   - **交易时段**：非 24/7，需判断是否休市
   - **停牌**：返回 `None` 或抛出 `MarketClosedError`
   - **复权**：提供前复权/后复权选项
3. 符号格式：统一用 `AAPL` / `00700.HK`（内部约定）

---

## 10. 注意事项

### 10.1 限流处理
- 各交易所限流规则不同：
  - 币安：权重制（每接口不同权重，累计超限封禁）
  - OKX：20 req / 2s
- 适配器内部实现退避重试（exponential backoff）
- 抛出 `RateLimitError` 时携带 `retry_after` 参数

### 10.2 时区陷阱
- **内部一律 UTC**，适配器负责转换
- 币安/OKX API 返回的是 UTC 毫秒时间戳（无歧义）
- 股票可能返回本地时间（需转 UTC）

### 10.3 精度问题
- 浮点数存储用 `float64`（Python `float`）
- 涉及资金计算时转 `Decimal`（避免精度误差）

### 10.4 WebSocket 稳定性
- 币安：24 小时强制断连，需自动重连
- OKX：需每 30s 发送 ping
- 使用成熟库（unicorn-binance-suite / python-okx）而非手写

---

## 附录：完整类图

```
┌─────────────────────────────┐
│  MarketDataProvider (ABC)   │
│  + get_klines()             │
│  + get_ticker()             │
│  + get_orderbook()          │
│  + stream_klines()          │
│  + list_symbols()           │
└──────────────┬──────────────┘
               │ implements
       ┌───────┴────────┬──────────────┐
       │                │              │
┌──────▼──────┐  ┌─────▼─────┐  ┌────▼─────────┐
│ Binance     │  │    OKX    │  │  USStock     │
│ Provider    │  │ Provider  │  │  Provider    │
└─────────────┘  └───────────┘  └──────────────┘
       │                │              │
       └────────┬───────┴──────────────┘
                │ created by
       ┌────────▼────────┐
       │ DataSource      │
       │ Factory         │
       └─────────────────┘
```

---

通过这套契约，**上层代码与底层数据源完全解耦**，未来无论添加任何新市场，只需实现接口，业务逻辑无需改动。
