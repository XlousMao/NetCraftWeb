"""决策分析（DecisionAnalyzer）：买 vs 做、卖材料 vs 合成、刷副本 vs 直接购买。

输出成本差异 / 利润 / 收益率与推荐方案，供 AI 与前端消费。
"""

from __future__ import annotations

from decimal import Decimal, ROUND_CEILING
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


def analyze_crafting_plan(db: Session, item_id: int, target_quantity: int = 99) -> dict:
    """制作采购方案：配方逆向拆解 + 材料按地点最低价采购 + 自制 vs 购买。

    - 找到所有产出该物品的启用配方
    - 按目标数量（默认一组 99）算所需合成次数（含成功率向上取整）
    - 每个材料取 SELL_OFFER 按地点分组的最低出售价，推荐最便宜地点
    - 汇总自制总成本，与直接购买对比给出推荐
    """
    from app.models.market import MarketObservation

    vs = ValuationService(db)
    item = db.get(Item, item_id)
    if item is None:
        return {"item_id": item_id, "error": "物品不存在"}

    target = Decimal(str(target_quantity))

    recipes = (
        db.execute(
            select(Recipe)
            .join(RecipeOutput, RecipeOutput.recipe_id == Recipe.id)
            .where(RecipeOutput.item_id == item_id, Recipe.is_active.is_(True))
            .distinct()
        )
        .scalars()
        .all()
    )

    def market_locations(iid: int) -> list[dict]:
        """某物品按地点分组的最低出售挂单价（含时间戳），升序。"""
        rows = (
            db.execute(
                select(MarketObservation)
                .where(
                    MarketObservation.item_id == iid,
                    MarketObservation.observation_type == "SELL_OFFER",
                )
                .order_by(MarketObservation.observed_at.desc())
            )
            .scalars()
            .all()
        )
        best_by_loc: dict[str, dict] = {}
        for o in rows:
            unit = vs._unit_price_to_base(o)
            loc = o.location or "未知地点"
            if loc not in best_by_loc or unit < best_by_loc[loc]["price"]:
                best_by_loc[loc] = {
                    "location": loc,
                    "price": float(unit),
                    "observed_at": o.observed_at.isoformat(),
                }
        return sorted(best_by_loc.values(), key=lambda x: x["price"])

    plan = []
    for r in recipes:
        output_qty = sum(
            (o.quantity for o in r.outputs if o.item_id == item_id), Decimal(0)
        )
        success_rate = Decimal(r.expected_success_rate or 1)
        effective = output_qty * success_rate
        craft_times = (
            int((target / effective).to_integral_value(rounding=ROUND_CEILING))
            if effective > 0
            else 0
        )

        materials = []
        total_cost = Decimal(0)
        for m in r.materials:
            total_required = Decimal(m.quantity) * craft_times
            locs = market_locations(m.item_id)
            if locs:
                unit_price = Decimal(str(locs[0]["price"]))
                best_location = locs[0]["location"]
            else:
                unit_price = vs.get_unit_price(m.item_id, "auto")[0]
                best_location = None
            mcost = unit_price * total_required
            total_cost += mcost
            m_item = db.get(Item, m.item_id)
            materials.append(
                {
                    "item_id": m.item_id,
                    "item_name": m_item.name if m_item else f"#{m.item_id}",
                    "icon_url": m_item.icon_url if m_item else None,
                    "per_craft": float(m.quantity),
                    "total_required": float(total_required),
                    "best_price": float(q_money(unit_price)),
                    "best_location": best_location,
                    "locations": locs,
                    "total_cost": float(q_money(mcost)),
                }
            )

        plan.append(
            {
                "recipe_id": r.id,
                "recipe_name": r.name,
                "recipe_type": r.recipe_type,
                "success_rate": float(success_rate),
                "output_quantity": float(output_qty),
                "craft_times": craft_times,
                "materials": materials,
                "total_material_cost": float(q_money(total_cost)),
            }
        )

    plan.sort(key=lambda x: x["total_material_cost"])

    # 直接购买：目标物品按地点最低出售价
    buy_locs = market_locations(item_id)
    buy_best = buy_locs[0] if buy_locs else None
    if buy_best:
        buy_price = Decimal(str(buy_best["price"]))
    else:
        buy_price = vs.get_unit_price(item_id, "SELL_OFFER")[0]
        if buy_price <= 0:
            buy_price = vs.get_unit_price(item_id, "NPC_PRICE")[0]
    buy_total = buy_price * target

    best_recipe = plan[0] if plan else None
    can_craft = best_recipe is not None
    if not can_craft:
        recommendation = "buy"
        recommendation_text = "该物品暂无制作配方，只能直接购买"
    elif buy_price <= 0:
        recommendation = "craft"
        recommendation_text = "暂无市场出售价，只能自己制作"
    elif best_recipe["total_material_cost"] < float(buy_total):
        diff = float(buy_total) - best_recipe["total_material_cost"]
        recommendation = "craft"
        recommendation_text = f"推荐自己制作，做 {int(target)} 个可节省 {round(diff, 2)} 钻石"
    else:
        diff = best_recipe["total_material_cost"] - float(buy_total)
        recommendation = "buy"
        recommendation_text = f"推荐直接购买，可节省 {round(diff, 2)} 钻石"

    return {
        "item_id": item_id,
        "item_name": item.name,
        "target_quantity": float(target),
        "recipes": plan,
        "best_recipe_id": best_recipe["recipe_id"] if best_recipe else None,
        "buy_price": float(buy_price),
        "buy_location": buy_best["location"] if buy_best else None,
        "buy_locations": buy_locs,
        "buy_total": float(q_money(buy_total)),
        "recommendation": recommendation,
        "recommendation_text": recommendation_text,
    }
