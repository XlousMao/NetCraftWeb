"""Demo 数据种子。

首次启动生成一套完整、体现真实关系的数据，让用户打开即见完整 Dashboard。
- 20 物品 / 5 副本 / 3 装备 / 5 配方 / 10+ 价格历史
- 20 副本记录（含掉落/消耗/维修）/ 10 炼金生产记录
- 自动构建物品关系与重要性评分

幂等：若已存在物品则跳过。
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.models.dungeon import Dungeon
from app.models.equipment import Equipment, EquipmentRepairRequirement
from app.models.item import Item
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


def _seed_items(db) -> dict[str, Item]:
    """创建 20 个物品，返回 name -> Item 映射。"""
    items = [
        ("精钢锭", "材料", 80, 105, "高级金属锭，装备维修核心材料"),
        ("钻石", "材料", 150, 180, "贵重宝石，高级装备维修材料"),
        ("魔晶", "材料", 120, 140, "蕴含魔力的晶体，炼金原料"),
        ("红草", "材料", 25, 30, "常见药草，炼金基础材料"),
        ("空瓶", "材料", 5, 8, "炼金容器"),
        ("银矿", "材料", 35, 42, "常见矿石"),
        ("铁矿", "材料", 15, 20, "基础矿石"),
        ("皮革", "材料", 22, 28, "怪物皮革，装备材料"),
        ("秘银锭", "材料", 200, 240, "稀有金属锭"),
        ("奥术水晶", "材料", 90, 110, "奥术能量结晶"),
        ("符文石", "材料", 45, 55, "铭刻符文的石头"),
        ("暗影之尘", "材料", 130, 160, "暗影生物掉落的粉末"),
        ("生命药水", "消耗品", 40, 55, "恢复少量生命"),
        ("高级生命药水", "消耗品", 120, 150, "恢复大量生命"),
        ("强力治疗药水", "消耗品", 85, 100, "强效治疗"),
        ("魔法卷轴", "消耗品", 60, 75, "一次性魔法道具"),
        ("传送卷轴", "消耗品", 30, 35, "回城道具"),
        ("龙骑士剑", "装备", None, 5000, "传奇单手剑"),
        ("秘银甲", "装备", None, 4200, "稀有铠甲"),
        ("金币袋", "货币", 100, 100, "可兑换 100 金币"),
    ]
    result: dict[str, Item] = {}
    for name, category, vendor, market, desc in items:
        item = Item(
            name=name,
            display_name=name,
            category=category,
            description=desc,
            vendor_buy_price=vendor,
            market_price=market,
            tags=[],
        )
        db.add(item)
        result[name] = item
    db.flush()
    return result


def _seed_dungeons(db) -> list[Dungeon]:
    dungeons = [
        ("黑暗洞穴", "低阶矿洞，产出铁矿与暗影之尘"),
        ("熔岩矿坑", "产出精钢锭、钻石与符文石"),
        ("亡灵古堡", "产出魔晶、暗影之尘与传送卷轴"),
        ("翡翠森林", "产出药草、皮革与生命药水"),
        ("龙之巢穴", "高价值副本，产出钻石、魔晶与奥术水晶"),
    ]
    result = []
    for name, desc in dungeons:
        d = Dungeon(name=name, description=desc)
        db.add(d)
        result.append(d)
    db.flush()
    return result


def _seed_equipments(db, items: dict[str, Item]) -> list[Equipment]:
    specs = [
        ("龙骑士剑", [("精钢锭", 3), ("钻石", 2)], 200),
        ("秘银甲", [("秘银锭", 2), ("皮革", 3)], 150),
        ("符文法杖", [("符文石", 3), ("奥术水晶", 1)], 180),
    ]
    result = []
    for name, reqs, currency in specs:
        eq = Equipment(name=name)
        db.add(eq)
        db.flush()
        for item_name, qty in reqs:
            db.add(
                EquipmentRepairRequirement(
                    equipment_id=eq.id,
                    item_id=items[item_name].id,
                    quantity=qty,
                    currency_cost=currency / len(reqs),
                )
            )
        result.append(eq)
    db.flush()
    return result


def _seed_recipes(db, items: dict[str, Item]) -> list[Recipe]:
    specs = [
        ("高级生命药水", "炼金", 0.90, [("红草", 3), ("魔晶", 2), ("空瓶", 1)], [("高级生命药水", 1)]),
        ("生命药水", "炼金", 0.95, [("红草", 2), ("空瓶", 1)], [("生命药水", 1)]),
        ("秘银锭", "制造", 0.85, [("银矿", 2), ("符文石", 1)], [("秘银锭", 1)]),
        ("强力治疗药水", "炼金", 0.88, [("生命药水", 2), ("奥术水晶", 1)], [("强力治疗药水", 1)]),
        ("精钢锭", "制造", 0.90, [("铁矿", 3), ("暗影之尘", 1)], [("精钢锭", 1)]),
    ]
    result = []
    for name, category, rate, mats, outs in specs:
        r = Recipe(name=name, category=category, expected_success_rate=rate)
        db.add(r)
        db.flush()
        for item_name, qty in mats:
            db.add(RecipeMaterial(recipe_id=r.id, item_id=items[item_name].id, quantity=qty))
        for item_name, qty in outs:
            db.add(RecipeOutput(recipe_id=r.id, item_id=items[item_name].id, quantity=qty))
        result.append(r)
    db.flush()
    return result


def _seed_price_history(db, items: dict[str, Item]):
    """为精钢锭等关键物品生成 10+ 条历史价格。"""
    vs = ValuationService(db)
    now = datetime.now(timezone.utc)
    hist = [
        ("精钢锭", "vendor", [70, 72, 75, 78, 80, 80]),
        ("钻石", "vendor", [130, 140, 145, 150]),
        ("精钢锭", "market", [90, 95, 100, 105]),
        ("魔晶", "vendor", [110, 115, 120]),
        ("高级生命药水", "market", [130, 140, 150]),
    ]
    for name, ptype, prices in hist:
        item = items[name]
        for i, p in enumerate(prices):
            vs.record_price(
                item.id,
                ptype,
                p,
                source="seed",
                observed_at=now - timedelta(days=len(prices) - i),
            )
    db.flush()


# 各副本掉落表
_DUNGEON_LOOT_TABLE = {
    "黑暗洞穴": [("铁矿", 12, 20), ("银矿", 4, 10), ("暗影之尘", 1, 3)],
    "熔岩矿坑": [("铁矿", 8, 15), ("精钢锭", 2, 6), ("符文石", 1, 4), ("钻石", 0, 2)],
    "亡灵古堡": [("魔晶", 2, 6), ("暗影之尘", 1, 4), ("传送卷轴", 1, 3)],
    "翡翠森林": [("红草", 6, 14), ("皮革", 2, 6), ("生命药水", 1, 4)],
    "龙之巢穴": [("钻石", 1, 4), ("魔晶", 2, 6), ("精钢锭", 2, 5), ("奥术水晶", 1, 3)],
}


def _seed_runs(db, items: dict[str, Item], dungeons: list[Dungeon]):
    rng = random.Random(42)
    svc = DungeonService(db)
    now = datetime.now(timezone.utc)

    for i in range(20):
        dungeon = dungeons[i % len(dungeons)]
        started = now - timedelta(days=rng.randint(0, 6), hours=rng.randint(0, 23))
        loots = []
        for item_name, lo, hi in _DUNGEON_LOOT_TABLE[dungeon.name]:
            qty = rng.randint(lo, hi)
            if qty > 0:
                loots.append(LootCreate(item_id=items[item_name].id, quantity=qty))

        consumptions = [
            ConsumptionCreate(item_id=items["生命药水"].id, quantity=rng.randint(1, 5)),
        ]
        if rng.random() < 0.4:
            consumptions.append(
                ConsumptionCreate(item_id=items["传送卷轴"].id, quantity=rng.randint(1, 2))
            )

        # 维修：随机一件装备
        equipment_choices = [1, 2, 3]  # 对应龙骑士剑/秘银甲/符文法杖
        repairs = []
        if rng.random() < 0.8:
            repairs.append(RepairLineCreate(equipment_id=rng.choice(equipment_choices)))

        payload = DungeonRunCreate(
            dungeon_id=dungeon.id,
            started_at=started,
            travel_minutes=rng.randint(3, 12),
            combat_minutes=rng.randint(15, 45),
            death_count=rng.randint(0, 2),
            other_cost=rng.randint(0, 200),
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
        success = int(attempted * (recipe.expected_success_rate + rng.uniform(-0.08, 0.05)))
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

        if db.execute(select(Item).limit(1)).first():
            print("[seed] 已存在数据，跳过 Demo 种子")
            return

        items = _seed_items(db)
        dungeons = _seed_dungeons(db)
        _seed_equipments(db, items)
        recipes = _seed_recipes(db, items)
        _seed_price_history(db, items)
        _seed_runs(db, items, dungeons)
        _seed_production(db, recipes)

        # 构建关系 + 重算重要性
        RelationService(db).sync_all()
        recompute_all_importance(db)

        db.commit()
        print("[seed] Demo 数据生成完成")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
