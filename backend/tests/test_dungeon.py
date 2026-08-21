"""副本收益计算集成测试（掉落/维修/消耗/净利润/每小时，含钻石+材料）。"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.models.dungeon import Dungeon
from app.models.equipment import Equipment, EquipmentRepairRequirement
from app.schemas.dungeon import (
    ConsumptionCreate,
    DungeonRunCreate,
    LootCreate,
    RepairLineCreate,
)
from app.services.dungeon import DungeonService
from app.analysis.service import compute_run_economy


def _setup(db, make_item, currency_setup, set_price):
    steel = make_item("精钢锭")
    set_price(steel.id, 80)
    diamond = currency_setup["钻石"]
    crystal = currency_setup["钻石结晶"]
    potion = make_item("生命药水")
    set_price(potion.id, 40)

    dungeon = Dungeon(name="副本A")
    db.add(dungeon)
    db.flush()

    sword = Equipment(name="龙骑士剑")
    db.add(sword)
    db.flush()
    db.add(EquipmentRepairRequirement(equipment_id=sword.id, item_id=steel.id, quantity=3))
    db.add(EquipmentRepairRequirement(equipment_id=sword.id, item_id=diamond.id, quantity=20))
    db.flush()
    return {"steel": steel, "diamond": diamond, "crystal": crystal, "potion": potion}, dungeon, sword


def test_dungeon_run_full_calculation(db, make_item, currency_setup, set_price):
    items, dungeon, sword = _setup(db, make_item, currency_setup, set_price)

    payload = DungeonRunCreate(
        dungeon_id=dungeon.id,
        started_at=datetime.now(timezone.utc),
        travel_minutes=12,
        combat_minutes=60,
        loots=[
            LootCreate(item_id=items["steel"].id, quantity=32),      # 32×80=2560
            LootCreate(item_id=items["diamond"].id, quantity=4),      # 4×1=4
            LootCreate(item_id=items["crystal"].id, quantity=5),      # 5×99=495
        ],
        consumptions=[ConsumptionCreate(item_id=items["potion"].id, quantity=10)],  # 400
        repairs=[RepairLineCreate(equipment_id=sword.id)],
    )

    run = DungeonService(db).create_run(payload)
    e = compute_run_economy(db, run)

    # 掉落: 2560 + 4 + 495 = 3059
    assert e["gross_value"] == Decimal(3059)
    # 维修: 精钢锭3×80 + 钻石20×1 = 260
    assert e["repair_cost"] == Decimal(260)
    # 消耗: 10×40 = 400
    assert e["consumable_cost"] == Decimal(400)
    # 总成本 = 660
    assert e["total_cost"] == Decimal(660)
    # 净利润 = 2399
    assert e["net_profit"] == Decimal(2399)
    # 总时长 72 分钟
    assert run.total_duration_minutes == Decimal(72)
    # 每小时 = 2399 / 1.2
    assert abs(e["profit_per_hour"] - Decimal(2399) / Decimal("1.2")) < Decimal("0.0001")


def test_crystal_loot_converts_to_diamond(db, make_item, currency_setup, set_price):
    """钻石结晶掉落自动换算为钻石。"""
    items, dungeon, _ = _setup(db, make_item, currency_setup, set_price)
    payload = DungeonRunCreate(
        dungeon_id=dungeon.id,
        started_at=datetime.now(timezone.utc),
        loots=[LootCreate(item_id=items["crystal"].id, quantity=3)],
    )
    run = DungeonService(db).create_run(payload)
    # 3 钻石结晶 = 297 钻石
    e = compute_run_economy(db, run)
    assert e["gross_value"] == Decimal(297)
