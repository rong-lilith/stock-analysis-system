# 行情分析系统（Crypto-First 多市场分析平台）

## 项目简介

一套面向**虚拟货币优先、可扩展至传统股票**的综合行情分析系统。

第一阶段聚焦加密货币市场（币安 Binance、欧易 OKX），实现行情采集、技术指标计算、策略回测与可视化；
通过**统一的数据源抽象层**预留美股、港股等市场的接入接口，后续无需改动上层逻辑即可扩展。

核心设计原则：**面向接口编程、市场无关（market-agnostic）、分层解耦、研究与生产分离**。

---

## 一、整体架构

采用**分层单体（Layered Monolith）**架构 —— 对单人/小团队开发最友好，避免微服务的运维开销，同时通过清晰分层保证后续可拆分为独立服务。

```text
┌─────────────────────────────────────────────────────────┐
│  展示层 Presentation     Web 仪表盘 / 图表 / 告警面板        │
├─────────────────────────────────────────────────────────┤
│  接口层 API              FastAPI REST + WebSocket 推送       │
├─────────────────────────────────────────────────────────┤
│  应用层 Application       策略编排 / 回测调度 / 信号生成        │
├──────────────┬──────────────┬───────────────────────────┤
│ 分析层        │ 回测层        │ 任务调度                    │
│ Analytics    │ Backtest     │ Scheduler (Celery)         │
│ 技术指标/特征 │ vectorbt 研究 │ 定时拉取 / 实时消费          │
│              │ backtrader验证│                            │
├──────────────┴──────────────┴───────────────────────────┤
│  存储层 Storage          TimescaleDB(时序) + Redis(缓存)     │
├─────────────────────────────────────────────────────────┤
│  数据源抽象层 DataSource  ★核心★ 统一接口 MarketDataProvider │
│  ┌──────────┬──────────┬─────────────┬─────────────────┐ │
│  │ Binance  │   OKX    │ [预留]美股   │ [预留]港股        │ │
│  │ Adapter  │ Adapter  │ Stock(US)   │ Stock(HK)       │ │
│  └──────────┴──────────┴─────────────┴─────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### 关键设计：数据源抽象层

这是整个系统**可扩展性的核心**。定义统一接口，所有市场（加密货币 / 股票）实现同一套契约，上层代码完全不感知底层是币安还是美股。

```python
# src/datasource/base.py  —— 抽象基类（契约）
class MarketDataProvider(ABC):
    @abstractmethod
    def get_klines(self, symbol: str, interval: str,
                   start: datetime, end: datetime) -> pd.DataFrame: ...
    @abstractmethod
    def get_ticker(self, symbol: str) -> Ticker: ...
    @abstractmethod
    def get_orderbook(self, symbol: str, depth: int) -> OrderBook: ...
    @abstractmethod
    async def stream_klines(self, symbol: str, interval: str): ...  # WebSocket

# 实现：BinanceProvider / OKXProvider 现在做
#       USStockProvider / HKStockProvider 预留空实现 + NotImplementedError
```

> 统一约定：所有 K 线数据归一化为标准 DataFrame 列
> `[timestamp, open, high, low, close, volume]`，时区统一 UTC，交易对统一格式（内部用 `BTC/USDT`，适配器各自转换为 `BTCUSDT`(币安) / `BTC-USDT`(OKX)）。

---

## 二、技术栈

| 层 | 选型 | 理由 |
|----|------|------|
| 语言 | Python 3.11+ | 量化生态成熟 |
| 多交易所对接 | **ccxt** | 统一多交易所 API，方便未来扩展；币安/OKX 均支持 |
| 币安专用（可选） | python-binance / unicorn-binance-suite | 生产级 WebSocket 自动重连 |
| OKX 专用（可选） | python-okx | 官方维护，API 覆盖全 |
| 数据处理 | Pandas / NumPy | 标准 |
| 技术指标 | **TA-Lib**（主）+ pandas-ta（原型） | TA-Lib C 实现，158 指标，性能最佳 |
| 回测-研究 | **vectorbt** | 向量化，参数扫描快百倍 |
| 回测-验证 | **backtrader** | 真实撮合/手续费/持仓逻辑 |
| 后端框架 | FastAPI | 原生异步 + WebSocket，自动文档 |
| 时序数据库 | PostgreSQL + **TimescaleDB** | SQL 友好 + 时序优化（hypertable/压缩/连续聚合） |
| 缓存 | Redis | 行情缓存 / 限流 / 会话 |
| 任务调度 | Celery + Redis | 定时拉取、异步指标计算 |
| 前端 | 阶段1: Streamlit（快速）→ 阶段2: React + Lightweight Charts | 先快速验证，再做专业图表 |
| 配置 | pydantic-settings + .env | 类型安全配置 |
| 部署 | Docker Compose | 一键启动全套依赖 |

---

## 三、目录结构规划

```text
stock-analysis-system/
├── README.md
├── pyproject.toml / requirements.txt
├── docker-compose.yml          # PostgreSQL+Timescale / Redis 一键起
├── .env.example                # API Key 模板（不入库）
├── docs/                       # 设计文档、API 文档
│   ├── architecture.md
│   └── datasource-contract.md  # 数据源接口契约说明
├── src/
│   ├── config/                 # 配置加载（pydantic-settings）
│   ├── datasource/             # ★数据源抽象层★
│   │   ├── base.py             #   MarketDataProvider 抽象基类
│   │   ├── models.py           #   Ticker/OrderBook/Kline 标准数据模型
│   │   ├── factory.py          #   按市场名返回对应 Provider
│   │   ├── crypto/
│   │   │   ├── binance.py      #   币安适配器（现在做）
│   │   │   └── okx.py          #   OKX 适配器（现在做）
│   │   └── stock/
│   │       ├── us.py           #   美股适配器（预留，接口已定义）
│   │       └── hk.py           #   港股适配器（预留）
│   ├── ingestion/              # 数据采集（REST 历史 + WS 实时）
│   │   ├── historical.py       #   批量回填历史 K 线
│   │   └── realtime.py         #   WebSocket 实时消费写库
│   ├── storage/                # 存储层（仓储模式 Repository）
│   │   ├── db.py               #   连接/会话管理
│   │   ├── models.py           #   ORM 表模型
│   │   └── repositories.py     #   读写封装
│   ├── analytics/              # 分析层
│   │   ├── indicators.py       #   技术指标（封装 TA-Lib）
│   │   └── features.py         #   特征工程
│   ├── strategy/               # 策略定义（与回测解耦）
│   │   └── base.py             #   Strategy 抽象基类
│   ├── backtest/               # 回测引擎封装
│   │   ├── vectorbt_engine.py  #   研究态
│   │   └── backtrader_engine.py#   验证态
│   ├── tasks/                  # Celery 任务（定时/异步）
│   ├── api/                    # FastAPI 接口层
│   │   ├── routers/            #   行情/指标/回测/告警路由
│   │   └── ws.py               #   WebSocket 推送
│   └── app.py                  # 应用入口
├── frontend/                   # 前端（阶段2，React）
├── scripts/                    # 运维脚本（初始化库、回填数据）
└── tests/                      # 单元测试 + 集成测试
    ├── test_datasource/        #   含 mock 适配器，不打真实 API
    ├── test_analytics/
    └── test_backtest/
```

---

## 四、开发计划（To-Do List）

按**里程碑（Milestone）**组织，每个里程碑都是一个可交付、可验证的最小闭环，避免一次性铺太大。

### 🏗 M0 · 工程基建（地基，1 周）
- [ ] 初始化 `pyproject.toml` / 依赖管理，确定 Python 版本
- [ ] 编写 `docker-compose.yml`：PostgreSQL+TimescaleDB、Redis
- [ ] 配置体系：`pydantic-settings` + `.env.example`（API Key/密钥管理，**密钥绝不入库**）
- [ ] 日志体系（structlog / loguru）+ 统一异常处理
- [ ] 搭建测试框架（pytest）与 CI（GitHub Actions：lint + test）
- [ ] 代码规范：ruff + black + pre-commit

### 🔌 M1 · 数据源抽象层 + 币安/OKX 接入（核心，1-2 周）
- [ ] 定义 `MarketDataProvider` 抽象接口与标准数据模型（Kline/Ticker/OrderBook）
- [ ] 制定符号与时区归一化规范（内部统一 `BTC/USDT`、UTC）
- [ ] 实现 `BinanceProvider`：REST 历史 K 线 + ticker + orderbook
- [ ] 实现 `OKXProvider`：同上（注意 OKX candle 为 9 字段、`confirm` 标志）
- [ ] 实现 `DataSourceFactory`：按市场/交易所名返回对应 Provider
- [ ] **预留股票适配器**：`USStockProvider` / `HKStockProvider` 仅定义类与方法签名，内部 `raise NotImplementedError`
- [ ] 编写 mock 适配器用于测试（CI 不依赖真实网络）
- [ ] 限流处理：尊重币安权重制 / OKX 20req/2s

### 💾 M2 · 存储与历史回填（1 周）
- [ ] 设计时序表结构（TimescaleDB hypertable，按交易对+周期分区）
- [ ] Repository 读写封装（去重、断点续传）
- [ ] `historical.py`：批量回填指定交易对/周期历史 K 线
- [ ] Redis 缓存最新行情与热点查询
- [ ] 数据完整性校验（缺口检测与补齐）

### 📡 M3 · 实时数据流（1 周）
- [ ] `realtime.py`：WebSocket 订阅 K 线/成交/盘口
- [ ] 自动重连、心跳（币安 24h 强制断连、20s ping）
- [ ] 实时数据落库 + 推送到上层
- [ ] 多交易对并发订阅管理

### 📊 M4 · 技术指标与分析（1 周）
- [ ] 封装 TA-Lib：MA/EMA/MACD/RSI/BOLL/KDJ/ATR 等常用指标
- [ ] 指标计算结果缓存（避免重复计算）
- [ ] 特征工程模块（为后续策略/选币提供输入）
- [ ] 指标计算单元测试（与已知值对比）

### 🔁 M5 · 策略与回测（2 周）
- [ ] 定义 `Strategy` 抽象基类（信号生成与执行解耦）
- [ ] vectorbt 研究引擎：快速参数扫描、批量回测
- [ ] backtrader 验证引擎：真实手续费/滑点/持仓
- [ ] 回测报告：收益曲线、最大回撤、夏普、胜率等风险收益指标
- [ ] 示例策略（双均线 / RSI 超买超卖）跑通端到端

### 🌐 M6 · API 服务层（1 周）
- [ ] FastAPI 路由：行情查询 / 指标 / 回测触发 / 结果查询
- [ ] WebSocket 推送实时行情与信号到前端
- [ ] 接口鉴权（本地使用可先 API Key 简单鉴权）
- [ ] 自动生成 OpenAPI 文档

### 🖥 M7 · 可视化仪表盘（1-2 周）
- [ ] 阶段1：Streamlit 快速验证（K线图、指标叠加、回测结果）
- [ ] 阶段2：React + Lightweight Charts 专业图表
- [ ] 自选交易对、多周期切换、指标叠加
- [ ] 告警面板（价格/指标触发提醒）

### ⏰ M8 · 任务调度与运维（1 周）
- [ ] Celery 定时任务：定时回填、定时计算指标
- [ ] 告警任务（条件触发通知：Telegram / 邮件）
- [ ] 监控与健康检查
- [ ] 部署文档与一键启动脚本

### 🚀 M9 · 扩展：传统股票市场（后续）
- [ ] 实现 `USStockProvider`（如 yfinance / Alpha Vantage / Polygon）
- [ ] 实现 `HKStockProvider`（数据源调研）
- [ ] 处理股票特有逻辑：交易时段、停牌、复权、除权除息
- [ ] 验证上层（指标/回测/前端）无需改动即可复用

---

## 五、给开发者的建议（优先级与避坑）

1. **先把 M0-M1 做扎实**：数据源抽象层是地基，接口定义错了后面全要返工。先把 `MarketDataProvider` 契约和数据归一化定清楚。
2. **从小闭环验证**：建议第一个可见成果是「拉取 BTC/USDT 日线 → 算 MA → 画图」跑通，再逐步加功能。
3. **密钥安全**：API Key/Secret 一律走 `.env`，加入 `.gitignore`，提交 `.env.example` 模板。只读行情大多无需鉴权，先用公开接口。
4. **研究与生产分离**：vectorbt 用于快速试错，backtrader 用于贴近实盘验证，不要混用。
5. **股票预留而非现在实现**：M9 之前股票适配器只保留接口签名，避免分散精力。
6. **测试不打真实 API**：用 mock 适配器，保证 CI 稳定、不被限流。

---

## License

待定。
