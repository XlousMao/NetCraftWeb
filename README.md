# GEAP · 游戏经济分析平台

> **Game Economy Analytics Platform** —— 游戏经济数据基础设施 + 成本核算系统 + 收益分析系统 + 决策辅助平台。

GEAP 围绕一个核心理念构建：

> **Item（物品）是整个系统唯一的核心主数据实体。**

所有业务（副本掉落、商人收购、市场价格、装备维修、炼金、制造、消耗、产出、收益计算、成本计算、盈亏分析、AI 分析）都建立在 **Item Master** 之上，通过 `item_id` 关联，杜绝孤立的"物品名称字符串"。

---

## 目录

- [功能特性](#功能特性)
- [技术栈](#技术栈)
- [架构](#架构)
- [快速开始](#快速开始)
  - [方式一：Docker Compose（一键启动）](#方式一docker-compose一键启动)
  - [方式二：本地开发（无需 Docker）](#方式二本地开发无需-docker)
- [核心设计原则](#核心设计原则)
- [项目结构](#项目结构)
- [API 概览](#api-概览)
- [测试](#测试)
- [数据备份](#数据备份)
- [开发决策记录](#开发决策记录)
- [路线图](#路线图)

---

## 功能特性

| 模块 | 能力 |
|------|------|
| **Item Master** | 物品 CRUD、分类、标签、三种估值来源（商人/市场/手动） |
| **物品图片** | 拖拽上传、Ctrl+V 粘贴截图、SHA-256 去重、主图管理 |
| **价格历史** | 历史价格、趋势、均价/最低/最高、更新价格不污染历史记录 |
| **关系系统** | Dungeon DROPS / Recipe CONSUMES+PRODUCES / Equipment REQUIRES_REPAIR，可扩展关系类型 |
| **关系图** | 可视化图谱、节点点击跳转、缩放/拖动 |
| **重要性评分** | 可解释的加权公式（副本产出/装备消耗/配方引用/价值/流通量） |
| **副本系统** | 副本、副本记录、掉落、消耗、维修（装备模板自动展开） |
| **收益计算** | 掉落价值、维修成本、消耗成本、净利润、每小时收益（全流程/战斗/赶路拆分） |
| **周期分析** | 日/周/月/自定义，净利润、成本占比、亏损原因拆解 |
| **炼金/生产** | 配方、理论/实际成功率、实际单位成本、失败损耗、ROI |
| **活动系统** | 副本/炼金/采集/制造/交易/其他 统一账本、活动效率排行 |
| **Dashboard** | 今日/本周经济、副本排行、成本构成、最重要物品 |
| **AI 分析** | DeepSeek 接入，结构化数据 → 摘要/问题定位/优化建议（无 key 自动降级） |

---

## 技术栈

**后端**
- Python 3.12+（已在 3.13 验证）
- FastAPI + SQLAlchemy 2.x + Pydantic 2.x
- Alembic（数据库迁移）
- PostgreSQL（生产）/ SQLite（本地零依赖）
- Redis（可选，MVP 降级为 no-op）

**前端**
- Vue 3 + TypeScript + Vite
- Element Plus + Pinia + Vue Router
- ECharts（图表）+ vis-network（关系图）

**部署**
- Docker Compose + Nginx

---

## 架构

```
┌───────────────────────────────────────┐
│              Web Frontend             │
│ Vue3 + TypeScript + Element Plus      │
│ ECharts + 图谱可视化                  │
└───────────────────┬───────────────────┘
                    │ REST API
┌───────────────────▼───────────────────┐
│              Backend                  │
│ FastAPI + SQLAlchemy + Pydantic       │
│ Service Layer + Repository Layer      │
└───────────────────┬───────────────────┘
                    │
        ┌───────────┼───────────┐
        ↓           ↓           ↓
 PostgreSQL       Redis       File Storage
        │                       │
        ↓                       ↓
 业务数据 / 历史记录         图片 / 截图
                    │
                    ↓
              Analysis Engine
                    │
                    ↓
              AI Analysis Layer
```

后端采用清晰分层：

```
api/          — Controller 层（路由 + 参数校验 + 响应）
services/     — Service 层（业务逻辑）
repositories/ — Repository 层（数据访问）
models/       — ORM 模型
schemas/      — Pydantic 校验模型
analysis/     — 分析引擎（economy_calculator + service）
```

---

## 快速开始

### 方式一：Docker Compose（一键启动）

```bash
# 1. 准备环境变量
cp .env.example .env

# 2. 一键启动（PostgreSQL + Redis + 后端 + 前端 + Nginx）
docker compose up -d --build

# 3. 访问
#   http://localhost       （Nginx 统一入口）
#   http://localhost:8000  （后端 API，/docs 为 Swagger）
```

后端启动时会自动执行 Alembic 迁移并写入 Demo 数据。

### 方式二：本地开发（无需 Docker）

后端（默认 SQLite，零依赖）：

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 初始化数据库 + Demo 数据
python -m app.seed

# 启动服务
uvicorn app.main:app --reload
```

前端：

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173，已配置 /api 代理到 8000
```

---

## 核心设计原则

1. **Item Master First** — 一切业务引用 `item_id`，禁止 `item_name`。
2. **历史数据不可被当前价格污染** — 所有实际交易/掉落/消耗/生产成本保存 `valuation_snapshot`（单价/来源/时间/币种），修改当前价格不影响历史报表。
3. **业务数据与计算结果分离** — 原始事实与派生指标分离，需要历史稳定性的结果保存 `calculation_snapshot`。
4. **图片属于物品主数据资产** — 支持多图、主图、游戏截图、证据截图。
5. **删除策略 = 软删除** — `is_active=false`，历史副本记录始终可正确引用。
6. **事务一致** — 副本记录+掉落+成本、炼金记录+材料+成品 均在单事务内完成。
7. **AI 只读分析** — AI 不直接修改数据库，只消费结构化分析数据、生成文本。
8. **核心公式集中管理** — `analysis/economy_calculator.py` 承载所有经济公式，修改规则只改一处。

---

## 项目结构

```
NetCraftAnalyz/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── seed.py              # Demo 数据种子
│   │   ├── core/                # 配置
│   │   ├── db/                  # 会话、基类、建表
│   │   ├── models/              # ORM 模型
│   │   ├── schemas/             # Pydantic
│   │   ├── repositories/        # 数据访问
│   │   ├── services/            # 业务逻辑（估值/图片/副本/炼金/活动/关系/AI）
│   │   ├── analysis/            # 分析引擎 + 经济计算器
│   │   ├── api/                 # 路由
│   │   └── utils/               # 日志等
│   ├── alembic/                 # 数据库迁移
│   ├── tests/                   # 测试
│   ├── scripts/                 # 备份脚本
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── api/                 # Axios 客户端 + 接口
│   │   ├── components/          # 图表/关系图/卡片/上传
│   │   ├── layouts/             # 主布局
│   │   ├── views/               # 页面
│   │   ├── router/ stores/ types/ utils/
│   │   └── main.ts / App.vue
│   ├── Dockerfile
│   └── nginx.conf
├── nginx/nginx.conf             # 反向代理
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## API 概览

```
/api/items                         物品 CRUD + 搜索/筛选/排序/分页
/api/items/{id}                    物品详情
/api/items/{id}/images             图片上传（multipart）
/api/items/{id}/images/paste       Ctrl+V 粘贴上传（raw bytes）
/api/items/{id}/prices             价格历史 + 记录
/api/items/{id}/relation-graph     关系图数据

/api/dungeons                      副本 CRUD
/api/dungeon-runs                  副本记录（掉落/消耗/维修 + 自动收益计算）

/api/equipments                    装备 + 维修需求模板

/api/recipes                       配方 + 配方分析
/api/production-records            生产记录（成功率/实际成本/ROI）

/api/activities                    活动 + 统一账本
/api/analysis/period               周期经济分析
/api/analysis/dungeon-rankings     副本排行
/api/analysis/recipe-rankings      配方排行
/api/analysis/activity-efficiency  活动效率
/api/dashboard                     Dashboard 聚合
/api/ai/analyze                    AI 分析
```

所有接口统一：Pydantic 校验、统一错误格式 `{detail}`、分页、搜索、排序、筛选。

---

## 测试

```bash
cd backend
pytest -v
```

测试覆盖核心经济公式与关键验收场景：

- 副本：掉落价值 / 维修成本 / 消耗成本 / 净利润 / 每小时收益
- 炼金：理论成本 / 实际成本 / 成功率 / 单位成本 / ROI
- **历史价格稳定性**：更新当前价格不改变历史副本收益
- 估值引擎：auto 策略优先级（manual → market → vendor）

---

## 数据备份

Docker 环境提供 PostgreSQL 备份脚本：

```bash
# 备份
backend/scripts/backup.sh

# 恢复
backend/scripts/restore.sh <备份文件>
```

---

## 开发决策记录

以下是自动开发过程中对一些非关键细节的取舍，均记录在案：

1. **本地默认 SQLite**：规格要求 PostgreSQL，但为保证"零依赖一键启动"与测试可跑通，本地开发默认使用 SQLite（SQLAlchemy 统一驱动），Docker/生产环境无缝切换 PostgreSQL（`DATABASE_URL` 一行配置）。
2. **Postgres 驱动选 `psycopg` 3**：`psycopg2-binary` 在 Python 3.13 无预编译 wheel，改用 `psycopg[binary]`（SQLAlchemy URL scheme 为 `postgresql+psycopg://`）。
3. **Redis 可选**：MVP 阶段 Redis 非必需，未配置时缓存层自动降级，不阻塞启动。
4. **AI 降级**：未配置 `DEEPSEEK_API_KEY` 时，AI 层返回本地规则化分析（同样输出"摘要/定位/原因/建议"四段）。
5. **维修明细落库**：新增 `dungeon_repairs` 表保留每次维修的材料与金币快照，保证可追溯。
6. **重要性评分可解释**：采用加权公式而非黑盒，权重与因素在 `analysis/service.py` 顶部注释说明。

---

## 路线图

- [x] Item Master + 图片（拖拽/粘贴/去重）
- [x] 价格历史 + 估值引擎
- [x] 关系系统 + 关系图 + 重要性评分
- [x] 副本 + 掉落 + 消耗 + 维修 + 收益计算
- [x] 周期经济分析
- [x] 炼金/生产 + 成功率 + 实际成本 + ROI
- [x] 统一活动系统
- [x] Dashboard
- [x] AI 分析层（DeepSeek）
- [ ] 拍卖行自动采集 / OCR / 截图识别
- [ ] 自动价格采集 / 价格预测 / 最优路线

---

*Built with WorkBuddy + DeepSeek V4 Pro.*
