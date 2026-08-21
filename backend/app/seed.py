"""Demo 数据种子（奶块 / NetCraft 特化）。

生成一套体现真实关系、可验证「货币→钻石→RMB」全链路的演示数据：
- 货币体系：钻石(1) / 钻石块(9) / 钻石结晶(99)
- RMB 观察：多日历史汇率（99 钻石块 = 25 / 27.1 RMB …）
- 物品 + 角色（材料/装备/消耗品/货币/掉落/维修材料/配方材料）
- 副本 / 装备（多物品维修）/ 配方（多货币材料）
- 价格历史 / 副本记录（掉落含钻石、钻石块）/ 炼金记录

幂等：若已存在数据则跳过。
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.models.currency import (
    CurrencyConversionRule,
    CurrencyDenomination,
    CurrencySystem,
    FiatExchangeObservation,
)
from app.models.dungeon import Dungeon
from app.models.equipment import Equipment, EquipmentRepairRequirement
from app.models.item import Item, ItemRole
from app.models.recipe import Recipe, RecipeMaterial, RecipeOutput
from app.schemas.dungeon import (
    ConsumptionCreate,
    DungeonRunCreate,
    LootCreate,
    RepairLineCreate,
)
from app.schemas.recipe import ProductionRecordCreate
from app.services.dungeon import DungeonService
from app.services.recipe import RecipeService
from app.services.relation import RelationService
from app.services.valuation import ValuationService
from app.analysis.service import recompute_all_importance


def _seed_currency(db) -> dict[str, Item]:
    """建立奶块钻石经济体系：钻石 / 钻石块 / 钻石结晶。"""
    diamond = Item(name="钻石", display_name="钻石", category="货币",
                   description="奶块基础货币，一切经济分析归一化为钻石")
    diamond_block = Item(name="钻石块", display_name="钻石块", category="货币",
                         description="由 9 个钻石合成")
    diamond_crystal = Item(name="钻石结晶", display_name="钻石结晶", category="货币",
                           description="由 11 个钻石块合成，即 99 钻石")
    for i in (diamond, diamond_block, diamond_crystal):
        db.add(i)
    db.flush()

    for item, role in [
        (diamond, ["CURRENCY", "TRADEABLE", "DUNGEON_DROP", "REPAIR_MATERIAL"]),
        (diamond_block, ["CURRENCY", "TRADEABLE", "DUNGEON_DROP", "REPAIR_MATERIAL"]),
        (diamond_crystal, ["CURRENCY", "TRADEABLE", "DUNGEON_DROP"]),
    ]:
        for r in role:
            db.add(ItemRole(item_id=item.id, role=r))

    system = CurrencySystem(
        name="奶块钻石经济体系",
        description="基础货币为钻石；钻石块=9钻石，钻石结晶=99钻石",
        base_currency_item_id=diamond.id,
    )
    db.add(system)
    db.flush()

    for item, base_value, is_base in [
        (diamond, Decimal(1), True),
        (diamond_block, Decimal(9), False),
        (diamond_crystal, Decimal(99), False),
    ]:
        db.add(CurrencyDenomination(
            currency_system_id=system.id, item_id=item.id,
            base_value=base_value, is_base=is_base,
        ))
    db.add(CurrencyConversionRule(
        currency_system_id=system.id, from_item_id=diamond_block.id,
        to_item_id=diamond.id, factor=Decimal(9),
    ))
    db.add(CurrencyConversionRule(
        currency_system_id=system.id, from_item_id=diamond_crystal.id,
        to_item_id=diamond_block.id, factor=Decimal(11),
    ))
    db.flush()
    return {"钻石": diamond, "钻石块": diamond_block, "钻石结晶": diamond_crystal}


def _seed_fiat(db, currency: dict[str, Item]):
    """多日 RMB 历史观察：99 钻石块 = 25 / 26.4 / 27.1 RMB。"""
    now = datetime.now(timezone.utc)
    block = currency["钻石块"]
    observations = [
        (Decimal("25.0"), now - timedelta(days=6)),
        (Decimal("26.4"), now - timedelta(days=3)),
        (Decimal("27.1"), now),
    ]
    for amount, obs_at in observations:
        db.add(FiatExchangeObservation(
            currency_item_id=block.id, quantity=Decimal(99),
            fiat_currency="CNY", fiat_amount=amount,
            observed_at=obs_at, source="seed",
        ))


def _seed_items(db) -> dict[str, Item]:
    """奶块主题物品：材料/消耗品/装备（价格由市场观察记录，非 Item 属性）。"""
    specs = [
        ("精钢锭", "材料", ["MATERIAL", "REPAIR_MATERIAL", "RECIPE_OUTPUT", "TRADEABLE"], "高级金属锭，装备维修核心材料"),
        ("铁矿", "材料", ["MATERIAL", "RECIPE_MATERIAL", "DUNGEON_DROP"], "基础矿石"),
        ("银矿", "材料", ["MATERIAL", "RECIPE_MATERIAL", "DUNGEON_DROP"], "常见矿石"),
        ("秘银锭", "材料", ["MATERIAL", "RECIPE_OUTPUT", "TRADEABLE"], "稀有金属锭"),
        ("红草", "材料", ["MATERIAL", "RECIPE_MATERIAL", "DUNGEON_DROP"], "常见药草"),
        ("空瓶", "材料", ["MATERIAL", "RECIPE_MATERIAL"], "炼金容器"),
        ("奥术水晶", "材料", ["MATERIAL", "RECIPE_MATERIAL", "DUNGEON_DROP"], "奥术能量结晶"),
        ("符文石", "材料", ["MATERIAL", "RECIPE_MATERIAL", "DUNGEON_DROP"], "铭刻符文的石头"),
        ("暗影之尘", "材料", ["MATERIAL", "RECIPE_MATERIAL", "DUNGEON_DROP"], "暗影生物掉落的粉末"),
        ("皮革", "材料", ["MATERIAL", "RECIPE_MATERIAL", "DUNGEON_DROP"], "怪物皮革"),
        ("生命药水", "消耗品", ["CONSUMABLE", "RECIPE_OUTPUT", "TRADEABLE"], "恢复少量生命"),
        ("高级生命药水", "消耗品", ["CONSUMABLE", "RECIPE_OUTPUT", "TRADEABLE"], "恢复大量生命"),
        ("强力治疗药水", "消耗品", ["CONSUMABLE", "RECIPE_OUTPUT"], "强效治疗"),
        ("魔法卷轴", "消耗品", ["CONSUMABLE", "DUNGEON_DROP"], "一次性魔法道具"),
        ("传送卷轴", "消耗品", ["CONSUMABLE", "DUNGEON_DROP"], "回城道具"),
        ("龙骑士剑", "装备", ["EQUIPMENT", "TRADEABLE"], "传奇单手剑"),
        ("秘银甲", "装备", ["EQUIPMENT", "TRADEABLE"], "稀有铠甲"),
        ("符文法杖", "装备", ["EQUIPMENT", "TRADEABLE"], "秘法法杖"),
    ]
    result: dict[str, Item] = {}
    for name, category, roles, desc in specs:
        item = Item(name=name, display_name=name, category=category, description=desc, tags=[])
        db.add(item)
        db.flush()
        for r in roles:
            db.add(ItemRole(item_id=item.id, role=r))
        result[name] = item
    return result


def _seed_dungeons(db) -> list[Dungeon]:
    names = [
        ("黑暗洞穴", "低阶矿洞，产出铁矿与暗影之尘"),
        ("熔岩矿坑", "产出精钢锭、钻石与符文石"),
        ("亡灵古堡", "产出钻石块、暗影之尘与传送卷轴"),
        ("翡翠森林", "产出药草、皮革与生命药水"),
        ("龙之巢穴", "高价值副本，产出钻石结晶、钻石块与奥术水晶"),
    ]
    result = []
    for name, desc in names:
        d = Dungeon(name=name, description=desc)
        db.add(d)
        result.append(d)
    db.flush()
    return result


def _seed_equipments(db, items: dict[str, Item], currency: dict[str, Item]) -> list[Equipment]:
    """装备维修需求：材料 + 钻石 + 钻石块（多物品，无 currency_cost）。"""
    specs = [
        ("龙骑士剑", [("精钢锭", 3), ("钻石", 20), ("钻石块", 2)]),
        ("秘银甲", [("秘银锭", 2), ("皮革", 3), ("钻石", 10)]),
        ("符文法杖", [("符文石", 3), ("奥术水晶", 1), ("钻石块", 1)]),
    ]
    result = []
    for name, reqs in specs:
        eq = Equipment(name=name)
        db.add(eq)
        db.flush()
        for item_name, qty in reqs:
            target = items.get(item_name) or currency.get(item_name)
            db.add(EquipmentRepairRequirement(
                equipment_id=eq.id, item_id=target.id, quantity=Decimal(qty),
            ))
        result.append(eq)
    db.flush()
    return result


def _seed_recipes(db, items: dict[str, Item], currency: dict[str, Item]) -> list[Recipe]:
    """配方：材料 + 钻石/钻石块（多货币）。"""
    specs = [
        ("高级生命药水", "炼金", Decimal("0.90"),
         [("红草", 3), ("奥术水晶", 2), ("空瓶", 1)], [("高级生命药水", 1)]),
        ("生命药水", "炼金", Decimal("0.95"),
         [("红草", 2), ("空瓶", 1)], [("生命药水", 1)]),
        ("秘银锭", "制造", Decimal("0.85"),
         [("银矿", 2), ("符文石", 1), ("钻石", 5)], [("秘银锭", 1)]),
        ("强力治疗药水", "炼金", Decimal("0.88"),
         [("生命药水", 2), ("奥术水晶", 1)], [("强力治疗药水", 1)]),
        ("精钢锭", "制造", Decimal("0.90"),
         [("铁矿", 3), ("暗影之尘", 1), ("钻石块", 1)], [("精钢锭", 1)]),
    ]
    result = []
    for name, category, rate, mats, outs in specs:
        recipe_type = "ALCHEMY" if category == "炼金" else "CRAFT"
        r = Recipe(name=name, recipe_type=recipe_type, category=category, expected_success_rate=rate)
        db.add(r)
        db.flush()
        for item_name, qty in mats:
            target = items.get(item_name) or currency.get(item_name)
            db.add(RecipeMaterial(recipe_id=r.id, item_id=target.id, quantity=Decimal(qty)))
        for item_name, qty in outs:
            target = items.get(item_name) or currency.get(item_name)
            db.add(RecipeOutput(recipe_id=r.id, item_id=target.id, quantity=Decimal(qty)))
        result.append(r)
    db.flush()
    return result


def _seed_market_observations(db, items: dict[str, Item], currency: dict[str, Item]):
    """为物品记录 NPC 价、市场价与历史价格（市场观察）。"""
    vs = ValuationService(db)
    diamond = currency["钻石"]
    now = datetime.now(timezone.utc)

    # (name, npc_price, sell_price)
    price_table = [
        ("精钢锭", 80, 105), ("铁矿", 15, 20), ("银矿", 35, 42),
        ("秘银锭", 200, 240), ("红草", 25, 30), ("空瓶", 5, 8),
        ("奥术水晶", 90, 110), ("符文石", 45, 55), ("暗影之尘", 130, 160),
        ("皮革", 22, 28), ("生命药水", 40, 55), ("高级生命药水", 120, 150),
        ("强力治疗药水", 85, 100), ("魔法卷轴", 60, 75), ("传送卷轴", 30, 35),
        ("龙骑士剑", 5000, None), ("秘银甲", 4200, None), ("符文法杖", 4600, None),
    ]
    for name, npc, sell in price_table:
        item = items[name]
        if npc:
            vs.record_observation(item.id, "NPC_PRICE", Decimal(npc), price_item_id=diamond.id, source="seed", observed_at=now)
        if sell:
            vs.record_observation(item.id, "SELL_OFFER", Decimal(sell), price_item_id=diamond.id, source="seed", observed_at=now)

    # 历史价格（多时间点，验证历史价格按时间生效）
    hist = [
        ("精钢锭", "NPC_PRICE", [70, 72, 75, 78, 80]),
        ("精钢锭", "SELL_OFFER", [90, 95, 100, 105]),
        ("秘银锭", "NPC_PRICE", [180, 190, 200]),
        ("红草", "NPC_PRICE", [22, 24, 25]),
        ("高级生命药水", "SELL_OFFER", [130, 140, 150]),
    ]
    for name, otype, prices in hist:
        item = items[name]
        for i, p in enumerate(prices):
            vs.record_observation(
                item.id, otype, Decimal(p), price_item_id=diamond.id,
                source="seed", observed_at=now - timedelta(days=len(prices) - i),
            )
    db.flush()


# 各副本掉落表（含货币物品）
_DUNGEON_LOOT_TABLE = {
    "黑暗洞穴": [("铁矿", 12, 20), ("银矿", 4, 10), ("暗影之尘", 1, 3)],
    "熔岩矿坑": [("铁矿", 8, 15), ("精钢锭", 2, 6), ("符文石", 1, 4), ("钻石", 5, 15)],
    "亡灵古堡": [("钻石块", 1, 3), ("暗影之尘", 1, 4), ("传送卷轴", 1, 3)],
    "翡翠森林": [("红草", 6, 14), ("皮革", 2, 6), ("生命药水", 1, 4)],
    "龙之巢穴": [("钻石结晶", 1, 2), ("钻石块", 2, 5), ("奥术水晶", 1, 3), ("钻石", 10, 30)],
}


def _seed_runs(db, items: dict[str, Item], currency: dict[str, Item], dungeons: list[Dungeon]):
    rng = random.Random(42)
    svc = DungeonService(db)
    now = datetime.now(timezone.utc)
    all_items = {**items, **currency}

    for i in range(20):
        dungeon = dungeons[i % len(dungeons)]
        started = now - timedelta(days=rng.randint(0, 6), hours=rng.randint(0, 23))
        loots = []
        for item_name, lo, hi in _DUNGEON_LOOT_TABLE[dungeon.name]:
            qty = rng.randint(lo, hi)
            if qty > 0:
                loots.append(LootCreate(item_id=all_items[item_name].id, quantity=qty))

        consumptions = [
            ConsumptionCreate(item_id=all_items["生命药水"].id, quantity=rng.randint(1, 5)),
        ]
        if rng.random() < 0.4:
            consumptions.append(
                ConsumptionCreate(item_id=all_items["传送卷轴"].id, quantity=rng.randint(1, 2))
            )

        repairs = []
        if rng.random() < 0.8:
            repairs.append(RepairLineCreate(equipment_id=rng.choice([1, 2, 3])))

        payload = DungeonRunCreate(
            dungeon_id=dungeon.id,
            started_at=started,
            travel_minutes=rng.randint(3, 12),
            combat_minutes=rng.randint(15, 45),
            death_count=rng.randint(0, 2),
            other_cost=rng.randint(0, 30),
            loots=loots,
            consumptions=consumptions,
            repairs=repairs,
            notes="Demo 数据" if i == 0 else None,
        )
        svc.create_run(payload)
    db.flush()


def _seed_production(db, recipes: list[Recipe]):
    rng = random.Random(7)
    svc = RecipeService(db)
    now = datetime.now(timezone.utc)
    for i in range(10):
        recipe = recipes[i % len(recipes)]
        attempted = rng.randint(20, 100)
        success = int(attempted * (float(recipe.expected_success_rate) + rng.uniform(-0.08, 0.05)))
        success = max(0, min(attempted, success))
        payload = ProductionRecordCreate(
            recipe_id=recipe.id,
            started_at=now - timedelta(days=rng.randint(0, 6)),
            attempted_count=attempted,
            success_count=success,
            notes="Demo 生产记录" if i == 0 else None,
        )
        svc.create_production_record(payload)
    db.flush()


def seed() -> None:
    init_db()
    db = SessionLocal()
    try:
        from sqlalchemy import select

        from app.models.currency import CurrencySystem

        has_items = db.execute(select(Item).limit(1)).first() is not None
        has_currency = (
            db.execute(select(CurrencySystem).limit(1)).first() is not None
        )

        if has_items and has_currency:
            print("[seed] 已存在数据，跳过 Demo 种子")
            return
        if has_items and not has_currency:
            print(
                "[seed] 检测到 V1 旧数据但无货币体系，无法无损升级，"
                "请重建数据：docker compose down -v && docker compose up -d --build"
            )
            return

        currency = _seed_currency(db)
        _seed_fiat(db, currency)
        items = _seed_items(db)
        dungeons = _seed_dungeons(db)
        _seed_equipments(db, items, currency)
        recipes = _seed_recipes(db, items, currency)
        _seed_market_observations(db, items, currency)
        _seed_runs(db, items, currency, dungeons)
        _seed_production(db, recipes)

        RelationService(db).sync_all()
        recompute_all_importance(db)

        db.commit()
        print("[seed] 奶块 Demo 数据生成完成")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
