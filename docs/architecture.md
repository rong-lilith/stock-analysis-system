# 系统架构设计文档

## 1. 架构概览

本系统采用**分层单体架构（Layered Monolith）**，优先支持加密货币市场（币安、OKX），通过统一数据源抽象层预留传统股票市场扩展能力。

### 1.1 设计原则

- **面向接口编程**：所有市场数据源实现统一接口 `MarketDataProvider`
- **关注点分离**：各层职责明确，层间通过接口通信
- **市场无关（Market-Agnostic）**：上层业务逻辑不感知底层是加密货币还是股票
- **可测试性**：依赖注入 + mock 适配器，单元测试不依赖外部 API
- **可观测性**：结构化日志 + 统一异常处理

### 1.2 架构分层

```
┌─────────────────────────────────────┐
│  Presentation Layer (展示层)         │  Web 仪表盘 / 告警面板
├─────────────────────────────────────┤
│  API Layer (接口层)                  │  FastAPI REST + WebSocket
├─────────────────────────────────────┤
│  Application Layer (应用层)          │  策略编排 / 回测调度 / 信号生成
├──────────────┬─────────────────────┤
│ Analytics    │ Backtest / Scheduler │  指标计算 / 回测引擎 / 定时任务
├──────────────┴─────────────────────┤
│  Storage Layer (存储层)              │  TimescaleDB + Redis
├─────────────────────────────────────┤
│  Data Source Abstraction (数据源层)  │  MarketDataProvider 接口
│  ┌──────────┬─────┬─────┬─────┐    │
│  │ Binance  │ OKX │ US  │ HK  │    │  交易所/市场适配器
│  └──────────┴─────┴─────┴─────┘    │
└─────────────────────────────────────┘
```

## 2. 数据流

### 2.1 历史数据回填流程

```
用户触发回填
    ↓
DataSourceFactory → BinanceProvider/OKXProvider
    ↓ (REST API 批量拉取)
归一化为标准 DataFrame
    ↓
Repository 去重写入 TimescaleDB
    ↓
触发指标计算任务 (Celery)
```

### 2.2 实时数据流

```
WebSocket 订阅 (Binance/OKX)
    ↓
自动重连 + 心跳保持
    ↓
数据归一化 → Redis 缓存 + TimescaleDB 持久化
    ↓
FastAPI WebSocket 推送到前端
    ↓
策略引擎实时评估 → 触发告警
```

## 3. 核心模块设计

### 3.1 数据源抽象层 (DataSource)

**目标**：屏蔽不同市场/交易所 API 差异，提供统一接口。

**契约** (详见 `datasource-contract.md`)：
```python
class MarketDataProvider(ABC):
    @abstractmethod
    def get_klines(...) -> pd.DataFrame: ...
    @abstractmethod
    def get_ticker(...) -> Ticker: ...
    @abstractmethod
    def get_orderbook(...) -> OrderBook: ...
    @abstractmethod
    async def stream_klines(...): ...
```

**实现**：
- `BinanceProvider`: 使用 ccxt 或 python-binance，处理权重制限流
- `OKXProvider`: 使用 ccxt 或 python-okx，注意 candle 9字段格式
- `USStockProvider` / `HKStockProvider`: 预留 (M9 阶段实现)

**工厂模式**：
```python
factory = DataSourceFactory()
provider = factory.get_provider("binance")  # 返回 BinanceProvider 实例
```

### 3.2 存储层 (Storage)

**时序数据库**：PostgreSQL + TimescaleDB 扩展
- Hypertable 按 `(symbol, interval, timestamp)` 分区
- 自动压缩历史数据（节省 90% 空间）
- Continuous Aggregates 预聚合（如小时线 → 日线）

**缓存**：Redis
- 最新行情 (TTL 10s)
- 计算结果缓存（指标值、回测结果）
- 限流计数器

**Repository 模式**：
```python
class KlineRepository:
    def bulk_insert(self, klines: List[Kline]) -> None: ...
    def get_range(self, symbol, interval, start, end) -> pd.DataFrame: ...
    def detect_gaps(self, symbol, interval) -> List[Gap]: ...
```

### 3.3 分析层 (Analytics)

**技术指标** (封装 TA-Lib)：
- 趋势类：SMA, EMA, MACD
- 震荡类：RSI, KDJ, Stochastic
- 波动类：Bollinger Bands, ATR
- 成交量：OBV, Volume Profile

**特征工程**：
- 价格变化率、成交量变化率
- 多周期指标融合（日线 RSI + 4小时 MACD）
- 市场情绪指标（持仓量、资金费率 - 仅适用于合约）

**缓存策略**：
- 指标结果存储到 TimescaleDB `indicators` 表
- 增量计算（仅计算新增 K 线）

### 3.4 回测层 (Backtest)

**双引擎策略**：

| 用途 | 引擎 | 优势 | 劣势 |
|------|------|------|------|
| 研究态 | **vectorbt** | 向量化，参数扫描快 100 倍 | 过于理想化（信号即成交） |
| 验证态 | **backtrader** | 真实撮合、手续费、滑点、持仓管理 | 慢，不适合大规模参数优化 |

**工作流**：
1. vectorbt 快速筛选参数区间（如 RSI 阈值 20-80，步长 5）
2. backtrader 精确验证筛出的 Top 10 参数组合
3. 风险指标：年化收益、最大回撤、夏普比率、胜率、盈亏比

### 3.5 API 层 (FastAPI)

**REST 接口**：
- `GET /api/v1/markets` - 可用市场/交易对列表
- `GET /api/v1/klines` - 历史 K 线查询
- `GET /api/v1/indicators/{symbol}` - 指标查询
- `POST /api/v1/backtest` - 触发回测任务
- `GET /api/v1/backtest/{task_id}` - 查询回测结果

**WebSocket**：
- `/ws/klines/{symbol}` - 实时 K 线推送
- `/ws/signals` - 策略信号推送

**鉴权**：
- 本地使用：API Key (X-API-Key header)
- 生产环境：可扩展为 JWT

### 3.6 任务调度 (Celery)

**定时任务**：
- 每分钟：拉取最新分钟线
- 每小时：计算小时级指标
- 每日：数据完整性校验、生成日报

**异步任务**：
- 历史数据回填（长时间运行）
- 批量指标计算
- 回测任务执行

## 4. 技术选型理由

| 组件 | 选型 | 原因 |
|------|------|------|
| 多交易所对接 | **ccxt** | 统一 API，支持 100+ 交易所，社区活跃 |
| 技术指标 | **TA-Lib** | C 实现，性能最佳，158 个内置指标 |
| 时序数据库 | **TimescaleDB** | SQL 友好 + 时序优化，单机百万级 QPS |
| 回测(研究) | **vectorbt** | 向量化，参数优化快百倍 |
| 回测(验证) | **backtrader** | 真实撮合逻辑，贴近实盘 |
| 后端框架 | **FastAPI** | 原生异步，自动文档，WebSocket 支持 |
| 任务队列 | **Celery + Redis** | 成熟稳定，Python 生态标配 |

## 5. 部署架构

### 5.1 开发环境

```yaml
# docker-compose.yml
services:
  postgres:
    image: timescale/timescaledb:latest-pg16
    environment:
      POSTGRES_DB: market_data
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  app:
    build: .
    environment:
      DATABASE_URL: postgresql://admin:${DB_PASSWORD}@postgres/market_data
      REDIS_URL: redis://redis:6379
    depends_on:
      - postgres
      - redis
    ports:
      - "8000:8000"

  celery-worker:
    build: .
    command: celery -A src.tasks worker -l info
    depends_on:
      - redis
      - postgres
```

### 5.2 生产环境考虑

- **数据库**：TimescaleDB 云服务 或 自建（主从复制 + 定时备份）
- **缓存**：Redis 持久化（AOF + RDB）
- **应用**：Docker + Kubernetes（可选）或 单机 Supervisor
- **监控**：Prometheus + Grafana（指标监控） + Sentry（错误追踪）

## 6. 扩展性设计

### 6.1 添加新交易所（币安 → FTX → Kraken）

1. 新建 `src/datasource/crypto/ftx.py`
2. 实现 `MarketDataProvider` 接口
3. 在 `DataSourceFactory` 注册
4. **上层代码零改动**

### 6.2 添加股票市场（美股 / 港股）

1. 实现 `USStockProvider`（数据源如 yfinance / Polygon）
2. 处理市场特有逻辑：
   - 交易时段（非 24/7，需处理盘前盘后）
   - 停牌/除权除息
   - 复权处理（前复权/后复权）
3. 策略/回测层因为依赖抽象接口，**无需改动**

### 6.3 从单体到微服务（未来）

当单机瓶颈出现时，可按业务拆分：
- **数据采集服务**：负责实时流消费 + 历史回填
- **计算服务**：指标计算 + 特征工程
- **回测服务**：独立资源池执行回测任务
- **API 网关**：统一入口

因为已经分层清晰，拆分时只需：
1. 各层独立打包为服务
2. 层间通信改为 gRPC / REST
3. 共享数据库或改为服务间消息传递

## 7. 安全与合规

- **API 密钥管理**：环境变量 + 密钥管理服务（AWS Secrets Manager / HashiCorp Vault）
- **限流**：遵守交易所限流规则，避免封 IP
- **数据合规**：确认数据使用符合交易所 ToS，特别是付费数据
- **风控**：实盘交易需增加风控模块（仓位管理、止损止盈）

---

## 附录：参考资料

- [币安 API 文档](https://binance-docs.github.io/apidocs/spot/en/)
- [OKX API 文档](https://www.okx.com/docs-v5/en/)
- [ccxt 文档](https://docs.ccxt.com/)
- [TimescaleDB 最佳实践](https://docs.timescale.com/timescaledb/latest/)
- [vectorbt 文档](https://vectorbt.dev/)
- [backtrader 文档](https://www.backtrader.com/docu/)
