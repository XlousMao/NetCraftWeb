# NetCraftWeb 项目长期约定

奶块游戏经济分析平台（FastAPI + SQLAlchemy 2 + Vue3 + Element Plus + Docker）。

## 核心架构（V3）

- **Item Master 是唯一核心主数据**，一切通过 `item_id` 引用，禁止孤立物品名字符串。
- **价格是市场事件，不是 Item 属性**：价格记录在 `market_observations`（observation_type：SELL_OFFER/BUY_ORDER/NPC_PRICE/MANUAL_ESTIMATE；支持以物易物 price_item_id + price_quantity）。不要给 Item 加 merchant/market/manual 价格字段。
- **货币换算引擎**：`currency_systems` / `currency_denominations` / `currency_conversion_rules`（from_item_id→to_item_id×factor），图遍历换算，禁止硬编码 9/99。基础货币=钻石。
- **副本只记事实**：DungeonLoot/Cost/Repair 只存 item_id + quantity + 时间，**不保存利润/估值快照**，利润由 `compute_run_economy(db, run)` 按 started_at 动态查历史价计算。
- **统一估值服务** `ValuationService`：`value(item_id, quantity, observed_at, policy)` → 钻石 + RMB，auto 优先级 MANUAL_ESTIMATE > NPC_PRICE > SELL_OFFER。
- **RMB 是法币不是游戏货币**：`fiat_exchange_observations` 记录历史汇率，估值标注"估算"。
- **Decimal 强制**：经济字段 Numeric(20,8)，核心计算用 Python Decimal，禁止 float。
- **决策分析**：`analysis/decision.py`（买vs做 / 卖材料vs合成 / 刷副本vs购买）。

## 环境约定

- 后端 venv：`C:\Users\25805\.workbuddy\binaries\python\envs\geap`。
- 测试：`python -m pytest`（27 测试，SQLite 内存 + create_all，不走迁移）。
- **迁移只适配 PostgreSQL**（Float→Numeric 用 `postgresql_using`），SQLite 跑不了 ALTER COLUMN TYPE，本地开发用 `python -m app.seed`（create_all）。
- 前端构建：`rm -rf dist && npm run build`（沙箱会拦截 rm，用 dangerouslyDisableSandbox 或先 rm）。

## 用户偏好

- 高信息密度、简洁逻辑清晰；笔记用 Markdown + Mermaid 流程图。
- 软删除统一模式：默认过滤 `is_active`，加 `include_inactive` 参数。
- Docker 部署（PostgreSQL + Nginx 动态解析）；国内网络用镜像源（.env 里 PIP_INDEX_URL/NPM_REGISTRY）。
