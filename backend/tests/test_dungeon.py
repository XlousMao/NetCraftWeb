"""副本收益计算集成测试（掉落/维修/消耗/净利润/每小时）。"""

from datetime import datetime, timedelta, timezone

from app.models.dungeon import Dungeon
from app.models.equipment import Equipment, EquipmentRepairRequirement
from app.schemas.dungeon import (
    ConsumptionCreate,
    DungeonRunCreate,
    LootCreate,
    RepairLineCreate,
)
from app.services.dungeon import DungeonService


def _setup(db, make_item):
    items = {
        "精钢锭": make_item("精钢锭", vendor_buy_price=80, market_price=105),
        "钻石": make_item("钻石", vendor_buy_price=150),
        "魔晶": make_item("魔晶", vendor_buy_price=120),
        "生命药水": make_item("生命药水", vendor_buy_price=40),
    }
    dungeon = Dungeon(name="副本A")
    db.add(dungeon)
    db.flush()

    sword = Equipment(name="龙骑士剑")
    db.add(sword)
    db.flush()
    db.add(EquipmentRepairRequirement(equipment_id=sword.id, item_id=items["精钢锭"].id, quantity=3))
    db.add(EquipmentRepairRequirement(equipment_id=sword.id, item_id=items["钻石"].id, quantity=2))
    db.flush()
    return items, dungeon, sword


def test_dungeon_run_full_calculation(db, make_item):
    items, dungeon, sword = _setup(db, make_item)

    payload = DungeonRunCreate(
        dungeon_id=dungeon.id,
        started_at=datetime.now(timezone.utc) - timedelta(hours=1),
        travel_minutes=12,
        combat_minutes=60,
        loots=[
            LootCreate(item_id=items["精钢锭"].id, quantity=32),
            LootCreate(item_id=items["钻石"].id, quantity=4),
            LootCreate(item_id=items["魔晶"].id, quantity=5),
        ],
        consumptions=[ConsumptionCreate(item_id=items["生命药水"].id, quantity=10)],
        repairs=[RepairLineCreate(equipment_id=sword.id)],
    )

    run = DungeonService(db).create_run(payload)

    # 掉落: 32*80 + 4*150 + 5*120 = 2560 + 600 + 600 = 3760
    assert run.gross_value == 3760.0
    # 维修: 精钢锭3*80 + 钻石2*150 = 240 + 300 = 540
    assert run.repair_cost == 540.0
    # 消耗: 生命药水10*40 = 400
    assert run.consumable_cost == 400.0
    # 总成本 540 + 400 = 940
    assert run.total_cost == 940.0
    # 净利润 3760 - 940 = 2820
    assert run.net_profit == 2820.0
    # 总时长 72 分钟
    assert run.total_duration_minutes == 72.0
    # 每小时 2820 / 1.2 = 2350
    assert run.profit_per_hour == round(2820 / 1.2, 4)


def test_valuation_snapshot_immutable(db, make_item):
    """修改当前价格后，历史副本收益保持不变。"""
    items, dungeon, sword = _setup(db, make_item)

    payload = DungeonRunCreate(
        dungeon_id=dungeon.id,
        started_at=datetime.now(timezone.utc) - timedelta(hours=1),
        loots=[LootCreate(item_id=items["精钢锭"].id, quantity=30)],
    )
    run = DungeonService(db).create_run(payload)
    assert run.gross_value == 2400.0  # 30 * 80

    # 现在把精钢锭商人价从 80 改为 120
    items["精钢锭"].vendor_buy_price = 120
    db.flush()

    # 历史记录的掉落估值快照应保持 80 不变
    assert run.loots[0].valuation_unit_price == 80.0
    assert run.gross_value == 2400.0
