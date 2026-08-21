"""分析引擎：重要性评分、周期经济分析、排行、活动效率、Dashboard 聚合。

所有计算读取业务事实数据，产出可解释的结构化结果（供 Dashboard 与 AI 消费）。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analysis.economy_calculator import calculate_profit_per_hour
from app.models.dungeon import Dungeon, DungeonLoot, DungeonRun
from app.models.equipment import EquipmentRepairRequirement
from app.models.item import Item, ItemRelation
from app.models.recipe import ProductionRecord, Recipe, RecipeMaterial, RecipeOutput
from app.models.activity import ActivityRecord


# ---- Item Importance ----

def compute_item_importance(db: Session, item_id: int) -> tuple[float, dict]:
    """重要性评分（简单可解释公式）。

    因素与权重：
      - 被副本产出：每个副本 +2
      - 被装备消耗：每件装备 +2
      - 被配方消耗：每个配方 +2
      - 被配方产出：每个配方 +1
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
            select(func.coalesce(func.sum(DungeonLoot.quantity), 0.0)).where(
                DungeonLoot.item_id == item_id
            )
        )
        .scalar_one()
    ) or 0.0

    price = (
        item.manual_price
        if item.manual_price
        else item.market_price
        if item.market_price
        else item.vendor_buy_price or 0.0
    )

    price_component = min(price / 100.0, 5.0)
    flow_component = min(total_flow / 100.0, 5.0)

    score = round(
        2 * drop_dungeons
        + 2 * repair_consumers
        + 2 * recipe_consumers
        + 1 * recipe_producers
        + price_component
        + flow_component,
        2,
    )

    breakdown = {
        "drop_dungeons": drop_dungeons,
        "repair_consumers": repair_consumers,
        "recipe_consumers": recipe_consumers,
        "recipe_producers": recipe_producers,
        "total_flow": round(total_flow, 2),
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
        if item.importance_score != score:
            item.importance_score = score
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


def analyze_period(db: Session, start: Optional[str] = None, end: Optional[str] = None) -> dict:
    """周期副本经济分析（掉落/维修/消耗/其他/净利润/每小时）。"""
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

    total_gross = sum(r.gross_value for r in runs)
    total_repair = sum(r.repair_cost for r in runs)
    total_consumable = sum(r.consumable_cost for r in runs)
    total_other = sum(r.other_cost for r in runs)
    total_cost = sum(r.total_cost for r in runs)
    net_profit = total_gross - total_cost
    total_duration = sum(r.total_duration_minutes for r in runs)
    profit_per_hour = calculate_profit_per_hour(net_profit, total_duration)
    cost_ratio = round(total_cost / total_gross, 4) if total_gross > 0 else 0.0

    # 成本构成
    cost_breakdown = [
        {"name": "维修", "value": round(total_repair, 2)},
        {"name": "消耗品", "value": round(total_consumable, 2)},
        {"name": "其他", "value": round(total_other, 2)},
    ]

    return {
        "start": start_dt.isoformat(),
        "end": end_dt.isoformat(),
        "run_count": len(runs),
        "total_gross": round(total_gross, 2),
        "total_repair": round(total_repair, 2),
        "total_consumable": round(total_consumable, 2),
        "total_other": round(total_other, 2),
        "total_cost": round(total_cost, 2),
        "net_profit": round(net_profit, 2),
        "total_duration_minutes": round(total_duration, 2),
        "profit_per_hour": profit_per_hour,
        "cost_ratio": cost_ratio,
        "cost_breakdown": cost_breakdown,
        "is_loss": net_profit < 0,
    }


def dungeon_rankings(db: Session, start: Optional[str] = None, end: Optional[str] = None) -> list[dict]:
    """副本收益排行：净利润 / 每小时收益 / 成本。"""
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
                "gross_value": 0.0,
                "total_cost": 0.0,
                "net_profit": 0.0,
                "total_duration": 0.0,
                "repair_cost": 0.0,
                "consumable_cost": 0.0,
            }
        d = agg[key]
        d["run_count"] += 1
        d["gross_value"] += r.gross_value
        d["total_cost"] += r.total_cost
        d["net_profit"] += r.net_profit
        d["total_duration"] += r.total_duration_minutes
        d["repair_cost"] += r.repair_cost
        d["consumable_cost"] += r.consumable_cost

    result = []
    for d in agg.values():
        d["gross_value"] = round(d["gross_value"], 2)
        d["total_cost"] = round(d["total_cost"], 2)
        d["net_profit"] = round(d["net_profit"], 2)
        d["repair_cost"] = round(d["repair_cost"], 2)
        d["consumable_cost"] = round(d["consumable_cost"], 2)
        d["profit_per_hour"] = calculate_profit_per_hour(
            d["net_profit"], d["total_duration"]
        )
        result.append(d)

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
                "material_cost": 0.0,
                "revenue": 0.0,
                "gross_profit": 0.0,
            }
        d = agg[key]
        d["attempted"] += r.attempted_count
        d["success"] += r.success_count
        d["material_cost"] += r.material_cost
        d["revenue"] += r.revenue
        d["gross_profit"] += r.gross_profit

    result = []
    for d in agg.values():
        d["success_rate"] = (
            round(d["success"] / d["attempted"], 4) if d["attempted"] else 0.0
        )
        d["roi"] = (
            round(d["gross_profit"] / d["material_cost"], 4)
            if d["material_cost"]
            else 0.0
        )
        d["material_cost"] = round(d["material_cost"], 2)
        d["revenue"] = round(d["revenue"], 2)
        d["gross_profit"] = round(d["gross_profit"], 2)
        result.append(d)

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
                "gross_value": 0.0,
                "total_cost": 0.0,
                "net_profit": 0.0,
                "duration_minutes": 0.0,
            }
        d = agg[key]
        d["count"] += 1
        d["gross_value"] += r.gross_value
        d["total_cost"] += r.total_cost
        d["net_profit"] += r.net_profit
        d["duration_minutes"] += r.duration_minutes

    items = []
    total_net = 0.0
    total_duration = 0.0
    for d in agg.values():
        d["gross_value"] = round(d["gross_value"], 2)
        d["total_cost"] = round(d["total_cost"], 2)
        d["net_profit"] = round(d["net_profit"], 2)
        d["profit_per_hour"] = calculate_profit_per_hour(
            d["net_profit"], d["duration_minutes"]
        )
        total_net += d["net_profit"]
        total_duration += d["duration_minutes"]
        items.append(d)

    items.sort(key=lambda x: x["profit_per_hour"], reverse=True)
    best = items[0]["activity_type"] if items else None

    return {
        "activities": items,
        "total_net_profit": round(total_net, 2),
        "total_duration_minutes": round(total_duration, 2),
        "avg_profit_per_hour": calculate_profit_per_hour(total_net, total_duration),
        "best_activity": best,
    }


# ---- Dashboard ----

def dashboard(db: Session) -> dict:
    """首页 Dashboard 聚合：今日 + 本周 + 排行 + 活动 + 重要物品。"""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)

    today = analyze_period(db, today_start.isoformat(), now.isoformat())
    week = analyze_period(db, week_start.isoformat(), now.isoformat())

    top_dungeons = dungeon_rankings(db, week_start.isoformat(), now.isoformat())[:5]
    top_recipes = recipe_rankings(db)[:5]
    activities = activity_efficiency(db, week_start.isoformat(), now.isoformat())

    # 最重要物品 TOP 5
    top_items = (
        db.execute(select(Item).where(Item.is_active.is_(True)).order_by(Item.importance_score.desc()).limit(5))
        .scalars()
        .all()
    )
    important_items = [
        {
            "id": i.id,
            "name": i.name,
            "category": i.category,
            "importance_score": i.importance_score,
            "vendor_buy_price": i.vendor_buy_price,
            "market_price": i.market_price,
        }
        for i in top_items
    ]

    return {
        "today": today,
        "week": week,
        "top_dungeons": top_dungeons,
        "top_recipes": top_recipes,
        "activities": activities,
        "important_items": important_items,
    }
