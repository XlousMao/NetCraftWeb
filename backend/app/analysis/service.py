"""分析引擎：重要性评分、周期经济分析、排行、活动效率、Dashboard 聚合。

所有计算读取业务事实数据，产出可解释的结构化结果（供 Dashboard 与 AI 消费）。
核心经济计算使用 Decimal（见 economy_calculator），输出为 float 供 JSON 序列化。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analysis.economy_calculator import calculate_profit_per_hour
from app.models.activity import ActivityRecord
from app.models.dungeon import Dungeon, DungeonLoot, DungeonRun
from app.models.equipment import EquipmentRepairRequirement
from app.models.item import Item, ItemRelation, ItemRole
from app.models.recipe import ProductionRecord, RecipeMaterial, RecipeOutput


def _f(x) -> float:
    """Decimal/数值 → float，用于 JSON 输出。"""
    if x is None:
        return 0.0
    return float(x)


def _f_or_none(x) -> Optional[float]:
    return None if x is None else float(x)


# ---- Item Importance ----

def compute_item_importance(db: Session, item_id: int) -> tuple[float, dict]:
    """重要性评分（简单可解释公式）。

    因素与权重：
      - 被副本产出：每个副本 +2
      - 被装备消耗：每件装备 +2
      - 被配方消耗：每个配方 +2
      - 被配方产出：每个配方 +1
      - 是否属于货币：+5
      - 交易价值：min(价格/100, 5)
      - 总流通量：min(总量/100, 5)
    """
    item = db.get(Item, item_id)
    if item is None:
        return 0.0, {}

    drop_dungeons = (
        db.execute(
            select(func.count(func.distinct(DungeonRun.dungeon_id)))
            .select_from(DungeonLoot)
            .join(DungeonRun, DungeonLoot.dungeon_run_id == DungeonRun.id)
            .where(DungeonLoot.item_id == item_id)
        )
        .scalar_one()
    )
    repair_consumers = (
        db.execute(
            select(func.count(func.distinct(EquipmentRepairRequirement.equipment_id)))
            .where(EquipmentRepairRequirement.item_id == item_id)
        )
        .scalar_one()
    )
    recipe_consumers = (
        db.execute(
            select(func.count(func.distinct(RecipeMaterial.recipe_id))).where(
                RecipeMaterial.item_id == item_id
            )
        )
        .scalar_one()
    )
    recipe_producers = (
        db.execute(
            select(func.count(func.distinct(RecipeOutput.recipe_id))).where(
                RecipeOutput.item_id == item_id
            )
        )
        .scalar_one()
    )
    total_flow = (
        db.execute(
            select(func.coalesce(func.sum(DungeonLoot.quantity), 0)).where(
                DungeonLoot.item_id == item_id
            )
        )
        .scalar_one()
    ) or 0
    is_currency = (
        db.execute(
            select(ItemRole).where(
                ItemRole.item_id == item_id, ItemRole.role == "CURRENCY"
            )
        ).scalar_one_or_none()
        is not None
    )

    price = (
        item.manual_price
        if item.manual_price is not None
        else item.market_price
        if item.market_price is not None
        else item.vendor_buy_price or 0
    )
    price = float(price)
    flow = float(total_flow)

    price_component = min(price / 100.0, 5.0)
    flow_component = min(flow / 100.0, 5.0)

    score = round(
        2 * drop_dungeons
        + 2 * repair_consumers
        + 2 * recipe_consumers
        + 1 * recipe_producers
        + (5 if is_currency else 0)
        + price_component
        + flow_component,
        2,
    )

    breakdown = {
        "drop_dungeons": drop_dungeons,
        "repair_consumers": repair_consumers,
        "recipe_consumers": recipe_consumers,
        "recipe_producers": recipe_producers,
        "is_currency": is_currency,
        "total_flow": round(flow, 2),
        "price": round(price, 2),
        "price_component": round(price_component, 2),
        "flow_component": round(flow_component, 2),
        "score": score,
    }
    return score, breakdown


def recompute_all_importance(db: Session) -> int:
    """重算所有物品重要性并落库，返回更新的物品数。"""
    items = db.execute(select(Item)).scalars().all()
    count = 0
    for item in items:
        score, _ = compute_item_importance(db, item.id)
        if float(item.importance_score) != score:
            item.importance_score = Decimal(str(score))
            count += 1
    db.flush()
    return count


# ---- Period / Dungeon Analysis ----

def _parse_dt(value: Optional[str], default: datetime) -> datetime:
    if not value:
        return default
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return default


def period_bounds(start: Optional[str], end: Optional[str]):
    """返回 (start_dt, end_dt)。默认最近 7 天。"""
    now = datetime.now(timezone.utc)
    end_dt = _parse_dt(end, now)
    start_dt = _parse_dt(start, end_dt - timedelta(days=7))
    return start_dt, end_dt


def _period_aggregate(runs: list[DungeonRun]) -> dict:
    """聚合一批副本记录的原始事实（Decimal）。"""
    total_gross = sum((r.gross_value for r in runs), Decimal(0))
    total_repair = sum((r.repair_cost for r in runs), Decimal(0))
    total_consumable = sum((r.consumable_cost for r in runs), Decimal(0))
    total_other = sum((r.other_cost for r in runs), Decimal(0))
    total_cost = sum((r.total_cost for r in runs), Decimal(0))
    net_profit = total_gross - total_cost
    total_travel = sum((r.travel_minutes for r in runs), Decimal(0))
    total_combat = sum((r.combat_minutes for r in runs), Decimal(0))
    total_duration = sum((r.total_duration_minutes for r in runs), Decimal(0))
    return {
        "total_gross": total_gross,
        "total_repair": total_repair,
        "total_consumable": total_consumable,
        "total_other": total_other,
        "total_cost": total_cost,
        "net_profit": net_profit,
        "total_travel": total_travel,
        "total_combat": total_combat,
        "total_duration": total_duration,
    }


def analyze_period(db: Session, start: Optional[str] = None, end: Optional[str] = None) -> dict:
    """周期副本经济分析（掉落/维修/消耗/其他/净利润/每小时 + RMB 估值）。"""
    start_dt, end_dt = period_bounds(start, end)

    runs = (
        db.execute(
            select(DungeonRun).where(
                DungeonRun.started_at >= start_dt, DungeonRun.started_at <= end_dt
            )
        )
        .scalars()
        .all()
    )
    a = _period_aggregate(runs)

    profit_per_hour = calculate_profit_per_hour(a["net_profit"], a["total_duration"])
    cost_ratio = float(a["total_cost"] / a["total_gross"]) if a["total_gross"] > 0 else 0.0

    # RMB 估值（基于记录时快照）
    gross_fiat = sum(
        (r.gross_value_fiat for r in runs if r.gross_value_fiat is not None), Decimal(0)
    )
    net_fiat = sum(
        (r.net_profit_fiat for r in runs if r.net_profit_fiat is not None), Decimal(0)
    )
    profit_per_hour_fiat = calculate_profit_per_hour(net_fiat, a["total_duration"])

    # 成本构成
    cost_breakdown = [
        {"name": "维修", "value": round(float(a["total_repair"]), 2)},
        {"name": "消耗品", "value": round(float(a["total_consumable"]), 2)},
        {"name": "其他", "value": round(float(a["total_other"]), 2)},
    ]

    return {
        "start": start_dt.isoformat(),
        "end": end_dt.isoformat(),
        "run_count": len(runs),
        "total_gross": round(float(a["total_gross"]), 2),
        "total_repair": round(float(a["total_repair"]), 2),
        "total_consumable": round(float(a["total_consumable"]), 2),
        "total_other": round(float(a["total_other"]), 2),
        "total_cost": round(float(a["total_cost"]), 2),
        "net_profit": round(float(a["net_profit"]), 2),
        "total_travel_minutes": round(float(a["total_travel"]), 2),
        "total_combat_minutes": round(float(a["total_combat"]), 2),
        "total_duration_minutes": round(float(a["total_duration"]), 2),
        "profit_per_hour": float(profit_per_hour),
        "gross_value_fiat": round(float(gross_fiat), 2),
        "net_profit_fiat": round(float(net_fiat), 2),
        "profit_per_hour_fiat": float(profit_per_hour_fiat),
        "cost_ratio": round(cost_ratio, 4),
        "cost_breakdown": cost_breakdown,
        "is_loss": a["net_profit"] < 0,
    }


def dungeon_rankings(db: Session, start: Optional[str] = None, end: Optional[str] = None) -> list[dict]:
    """副本收益排行：净利润 / 每小时收益 / 成本 / 维修占比。"""
    start_dt, end_dt = period_bounds(start, end)
    runs = (
        db.execute(
            select(DungeonRun).where(
                DungeonRun.started_at >= start_dt, DungeonRun.started_at <= end_dt
            )
        )
        .scalars()
        .all()
    )

    agg: dict[int, dict] = {}
    for r in runs:
        key = r.dungeon_id
        if key not in agg:
            agg[key] = {
                "dungeon_id": key,
                "dungeon_name": r.dungeon.name if r.dungeon else "未知",
                "run_count": 0,
                "gross_value": Decimal(0),
                "total_cost": Decimal(0),
                "net_profit": Decimal(0),
                "repair_cost": Decimal(0),
                "consumable_cost": Decimal(0),
                "total_duration": Decimal(0),
                "net_profit_fiat": Decimal(0),
            }
        d = agg[key]
        d["run_count"] += 1
        d["gross_value"] += r.gross_value
        d["total_cost"] += r.total_cost
        d["net_profit"] += r.net_profit
        d["repair_cost"] += r.repair_cost
        d["consumable_cost"] += r.consumable_cost
        d["total_duration"] += r.total_duration_minutes
        if r.net_profit_fiat is not None:
            d["net_profit_fiat"] += r.net_profit_fiat

    result = []
    for d in agg.values():
        repair_ratio = (
            float(d["repair_cost"] / d["gross_value"]) if d["gross_value"] > 0 else 0.0
        )
        result.append(
            {
                "dungeon_id": d["dungeon_id"],
                "dungeon_name": d["dungeon_name"],
                "run_count": d["run_count"],
                "gross_value": round(float(d["gross_value"]), 2),
                "total_cost": round(float(d["total_cost"]), 2),
                "net_profit": round(float(d["net_profit"]), 2),
                "repair_cost": round(float(d["repair_cost"]), 2),
                "consumable_cost": round(float(d["consumable_cost"]), 2),
                "repair_ratio": round(repair_ratio, 4),
                "net_profit_fiat": round(float(d["net_profit_fiat"]), 2),
                "profit_per_hour": float(
                    calculate_profit_per_hour(d["net_profit"], d["total_duration"])
                ),
            }
        )

    result.sort(key=lambda x: x["net_profit"], reverse=True)
    return result


def recipe_rankings(db: Session) -> list[dict]:
    """配方排行榜（基于生产记录聚合）。"""
    records = db.execute(select(ProductionRecord)).scalars().all()
    agg: dict[int, dict] = {}
    for r in records:
        key = r.recipe_id
        if key not in agg:
            agg[key] = {
                "recipe_id": key,
                "recipe_name": r.recipe.name if r.recipe else "未知",
                "attempted": 0,
                "success": 0,
                "material_cost": Decimal(0),
                "revenue": Decimal(0),
                "gross_profit": Decimal(0),
            }
        d = agg[key]
        d["attempted"] += r.attempted_count
        d["success"] += r.success_count
        d["material_cost"] += r.material_cost
        d["revenue"] += r.revenue
        d["gross_profit"] += r.gross_profit

    result = []
    for d in agg.values():
        result.append(
            {
                "recipe_id": d["recipe_id"],
                "recipe_name": d["recipe_name"],
                "attempted": d["attempted"],
                "success": d["success"],
                "success_rate": round(d["success"] / d["attempted"], 4) if d["attempted"] else 0.0,
                "material_cost": round(float(d["material_cost"]), 2),
                "revenue": round(float(d["revenue"]), 2),
                "gross_profit": round(float(d["gross_profit"]), 2),
                "roi": round(float(d["gross_profit"] / d["material_cost"]), 4)
                if d["material_cost"]
                else 0.0,
            }
        )

    result.sort(key=lambda x: x["roi"], reverse=True)
    return result


def activity_efficiency(db: Session, start: Optional[str] = None, end: Optional[str] = None) -> dict:
    """活动效率分析：按活动类型聚合 profit/hour。"""
    start_dt, end_dt = period_bounds(start, end)
    records = (
        db.execute(
            select(ActivityRecord).where(
                ActivityRecord.started_at >= start_dt,
                ActivityRecord.started_at <= end_dt,
            )
        )
        .scalars()
        .all()
    )

    agg: dict[str, dict] = {}
    for r in records:
        key = r.activity_type
        if key not in agg:
            agg[key] = {
                "activity_type": key,
                "count": 0,
                "gross_value": Decimal(0),
                "total_cost": Decimal(0),
                "net_profit": Decimal(0),
                "duration_minutes": Decimal(0),
            }
        d = agg[key]
        d["count"] += 1
        d["gross_value"] += r.gross_value
        d["total_cost"] += r.total_cost
        d["net_profit"] += r.net_profit
        d["duration_minutes"] += r.duration_minutes

    items = []
    total_net = Decimal(0)
    total_duration = Decimal(0)
    for d in agg.values():
        total_net += d["net_profit"]
        total_duration += d["duration_minutes"]
        items.append(
            {
                "activity_type": d["activity_type"],
                "count": d["count"],
                "gross_value": round(float(d["gross_value"]), 2),
                "total_cost": round(float(d["total_cost"]), 2),
                "net_profit": round(float(d["net_profit"]), 2),
                "duration_minutes": round(float(d["duration_minutes"]), 2),
                "profit_per_hour": float(
                    calculate_profit_per_hour(d["net_profit"], d["duration_minutes"])
                ),
            }
        )

    items.sort(key=lambda x: x["profit_per_hour"], reverse=True)
    best = items[0]["activity_type"] if items else None

    return {
        "activities": items,
        "total_net_profit": round(float(total_net), 2),
        "total_duration_minutes": round(float(total_duration), 2),
        "avg_profit_per_hour": float(
            calculate_profit_per_hour(total_net, total_duration)
        ),
        "best_activity": best,
    }


# ---- Dashboard ----

def dashboard(db: Session) -> dict:
    """首页 Dashboard 聚合：今日 + 本周 + 排行 + 活动 + 重要物品。"""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)

    today = analyze_period(db, today_start.isoformat(), now.isoformat())
    week = analyze_period(db, week_start.isoformat(), now.isoformat())
    month = analyze_period(db, month_start.isoformat(), now.isoformat())

    top_dungeons = dungeon_rankings(db, week_start.isoformat(), now.isoformat())[:5]
    top_recipes = recipe_rankings(db)[:5]
    activities = activity_efficiency(db, week_start.isoformat(), now.isoformat())

    # 最重要物品 TOP 5
    top_items = (
        db.execute(
            select(Item)
            .where(Item.is_active.is_(True))
            .order_by(Item.importance_score.desc())
            .limit(5)
        )
        .scalars()
        .all()
    )
    important_items = [
        {
            "id": i.id,
            "name": i.name,
            "category": i.category,
            "importance_score": float(i.importance_score),
            "vendor_buy_price": _f_or_none(i.vendor_buy_price),
            "market_price": _f_or_none(i.market_price),
        }
        for i in top_items
    ]

    return {
        "today": today,
        "week": week,
        "month": month,
        "top_dungeons": top_dungeons,
        "top_recipes": top_recipes,
        "activities": activities,
        "important_items": important_items,
    }
