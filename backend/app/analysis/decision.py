"""决策分析（DecisionAnalyzer）：买 vs 做、卖材料 vs 合成、刷副本 vs 直接购买。

输出成本差异 / 利润 / 收益率与推荐方案，供 AI 与前端消费。
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analysis.service import compute_run_economy
from app.models.dungeon import Dungeon, DungeonRun
from app.models.item import Item
from app.models.recipe import Recipe, RecipeOutput
from app.services.currency import q_money
from app.services.valuation import ValuationService


def _item_name(db: Session, item_id: int) -> str:
    item = db.get(Item, item_id)
    return item.name if item else f"#{item_id}"


def analyze_craft_vs_buy(db: Session, item_id: int) -> dict:
    """制作 vs 直接购买：返回各配方单件制作成本 + 购买价 + 推荐。"""
    vs = ValuationService(db)
    item = db.get(Item, item_id)
    if item is None:
        return {"item_id": item_id, "error": "物品不存在"}

    # 购买价：优先最低出售挂单，其次商人价
    buy_price, buy_source = vs.get_unit_price(item_id, "SELL_OFFER")
    if buy_price <= 0:
        buy_price, buy_source = vs.get_unit_price(item_id, "NPC_PRICE")
    buy_value = vs.value(item_id, 1, "auto")

    # 找到产出该物品的配方
    recipes = (
        db.execute(
            select(Recipe)
            .join(RecipeOutput, RecipeOutput.recipe_id == Recipe.id)
            .where(RecipeOutput.item_id == item_id, Recipe.is_active.is_(True))
        )
        .scalars()
        .all()
    )

    options = []
    for r in recipes:
        material_cost = Decimal(0)
        for m in r.materials:
            material_cost += vs.value(m.item_id, m.quantity, "auto").base_currency_value
        output_qty = sum(
            (o.quantity for o in r.outputs if o.item_id == item_id), Decimal(0)
        )
        success_rate = Decimal(r.expected_success_rate or 1)
        per_unit = (
            material_cost / (output_qty * success_rate)
            if output_qty > 0 and success_rate > 0
            else material_cost
        )
        options.append(
            {
                "recipe_id": r.id,
                "recipe_name": r.name,
                "recipe_type": r.recipe_type,
                "material_cost": float(q_money(material_cost)),
                "per_unit_cost": float(q_money(per_unit)),
                "success_rate": float(success_rate),
            }
        )

    options.sort(key=lambda x: x["per_unit_cost"])
    best_craft = options[0]["per_unit_cost"] if options else None
    can_buy = float(buy_price) > 0
    recommend = "buy"
    if best_craft is not None and (not can_buy or best_craft < float(buy_price)):
        recommend = "craft"

    return {
        "item_id": item_id,
        "item_name": item.name,
        "buy_price": float(buy_price),
        "buy_source": buy_source,
        "buy_fiat": float(buy_value.fiat_value) if buy_value.fiat_value is not None else None,
        "craft_options": options,
        "recommendation": recommend,
        "recommendation_text": "推荐自己制作" if recommend == "craft" else "推荐直接购买",
    }


def analyze_recipe_decision(db: Session, recipe_id: int) -> dict:
    """卖材料 vs 合成：比较材料直接卖 vs 合成产出的价值。"""
    vs = ValuationService(db)
    recipe = db.get(Recipe, recipe_id)
    if recipe is None:
        return {"recipe_id": recipe_id, "error": "配方不存在"}

    material_value = Decimal(0)
    materials = []
    for m in recipe.materials:
        v = vs.value(m.item_id, m.quantity, "auto")
        material_value += v.base_currency_value
        materials.append(
            {"item_id": m.item_id, "item_name": _item_name(db, m.item_id),
             "quantity": float(m.quantity), "value": float(v.base_currency_value)}
        )

    output_value = Decimal(0)
    outputs = []
    for o in recipe.outputs:
        v = vs.value(o.item_id, o.quantity, "auto")
        output_value += v.base_currency_value
        outputs.append(
            {"item_id": o.item_id, "item_name": _item_name(db, o.item_id),
             "quantity": float(o.quantity), "value": float(v.base_currency_value)}
        )

    success_rate = Decimal(recipe.expected_success_rate or 1)
    expected_output = output_value * success_rate
    profit = expected_output - material_value
    roi = profit / material_value if material_value > 0 else Decimal(0)

    return {
        "recipe_id": recipe.id,
        "recipe_name": recipe.name,
        "recipe_type": recipe.recipe_type,
        "material_value": float(q_money(material_value)),
        "output_value": float(q_money(output_value)),
        "expected_output_value": float(q_money(expected_output)),
        "profit": float(q_money(profit)),
        "roi": float(q_money(roi)),
        "success_rate": float(success_rate),
        "recommendation": "craft" if profit > 0 else "sell",
        "recommendation_text": "推荐合成" if profit > 0 else "推荐直接卖材料",
        "materials": materials,
        "outputs": outputs,
    }


def analyze_dungeon_decision(db: Session, dungeon_id: int) -> dict:
    """刷副本 vs 直接购买：基于历史副本记录的平均净收益判断是否值得刷。"""
    dungeon = db.get(Dungeon, dungeon_id)
    if dungeon is None:
        return {"dungeon_id": dungeon_id, "error": "副本不存在"}

    runs = (
        db.execute(
            select(DungeonRun)
            .where(DungeonRun.dungeon_id == dungeon_id)
            .order_by(DungeonRun.started_at.desc())
            .limit(20)
        )
        .scalars()
        .all()
    )

    if not runs:
        return {
            "dungeon_id": dungeon_id,
            "dungeon_name": dungeon.name,
            "run_count": 0,
            "recommendation": "unknown",
            "recommendation_text": "暂无副本记录，无法判断",
        }

    total_gross = total_cost = total_duration = Decimal(0)
    for r in runs:
        e = compute_run_economy(db, r)
        total_gross += e["gross_value"]
        total_cost += e["total_cost"]
        total_duration += r.total_duration_minutes

    n = Decimal(len(runs))
    avg_gross = total_gross / n
    avg_cost = total_cost / n
    avg_net = avg_gross - avg_cost
    avg_duration = total_duration / n
    profit_per_hour = (
        avg_net / (avg_duration / Decimal(60)) if avg_duration > 0 else Decimal(0)
    )

    return {
        "dungeon_id": dungeon_id,
        "dungeon_name": dungeon.name,
        "run_count": len(runs),
        "avg_gross_value": float(q_money(avg_gross)),
        "avg_cost": float(q_money(avg_cost)),
        "avg_net_profit": float(q_money(avg_net)),
        "avg_duration_minutes": float(q_money(avg_duration)),
        "profit_per_hour": float(q_money(profit_per_hour)),
        "recommendation": "farm" if avg_net > 0 else "avoid",
        "recommendation_text": "推荐刷此副本" if avg_net > 0 else "此副本平均亏损，建议直接购买掉落物",
    }
