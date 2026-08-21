"""维修多物品成本测试。

维修 = 精钢锭 ×3 + 钻石 ×20 + 钻石块 ×2，验证材料总成本 / 钻石等价 / RMB 估值。
"""

from datetime import datetime, timezone
from decimal import Decimal

from app.models.currency import FiatExchangeObservation
from app.models.dungeon import Dungeon
from app.models.equipment import Equipment, EquipmentRepairRequirement
from app.schemas.dungeon import DungeonRunCreate, RepairLineCreate
from app.services.dungeon import DungeonService
from app.analysis.service import compute_run_economy


def _setup(db, make_item, currency_setup, set_price):
    steel = make_item("精钢锭")
    set_price(steel.id, 80)
    diamond = currency_setup["钻石"]
    block = currency_setup["钻石块"]

    sword = Equipment(name="龙骑士剑")
    db.add(sword)
    db.flush()
    # 维修需求：精钢锭×3 + 钻石×20 + 钻石块×2（多物品，含货币）
    db.add(EquipmentRepairRequirement(equipment_id=sword.id, item_id=steel.id, quantity=3))
    db.add(EquipmentRepairRequirement(equipment_id=sword.id, item_id=diamond.id, quantity=20))
    db.add(EquipmentRepairRequirement(equipment_id=sword.id, item_id=block.id, quantity=2))
    db.flush()
    return steel, diamond, block, sword


def test_repair_multi_item_cost(db, make_item, currency_setup, set_price):
    steel, diamond, block, sword = _setup(db, make_item, currency_setup, set_price)
    dungeon = Dungeon(name="副本A")
    db.add(dungeon)
    db.flush()

    # 加入 RMB 观察：99 钻石块 = 27.10 RMB
    db.add(
        FiatExchangeObservation(
            currency_item_id=block.id,
            quantity=Decimal(99),
            fiat_currency="CNY",
            fiat_amount=Decimal("27.10"),
            observed_at=datetime.now(timezone.utc),
        )
    )
    db.flush()

    payload = DungeonRunCreate(
        dungeon_id=dungeon.id,
        started_at=datetime.now(timezone.utc),
        repairs=[RepairLineCreate(equipment_id=sword.id)],
    )
    run = DungeonService(db).create_run(payload)
    e = compute_run_economy(db, run)

    # 维修成本（钻石）：精钢锭 3×80 + 钻石 20×1 + 钻石块 2×9 = 240 + 20 + 18 = 278
    assert e["repair_cost"] == Decimal(278)
    # 维修明细 3 条
    assert len(run.repairs) == 3
    # 无掉落，净利润为负；RMB 估值 = -278 钻石对应的 RMB
    assert e["net_profit_fiat"] is not None and e["net_profit_fiat"] < 0
    expected_rmb = Decimal(278) * Decimal("27.10") / Decimal(99) / Decimal(9)
    assert abs(abs(e["net_profit_fiat"]) - expected_rmb) < Decimal("0.01")


def test_repair_manual_item_line(db, make_item, currency_setup, set_price):
    """手动指定 item + quantity 的维修。"""
    steel, diamond, block, sword = _setup(db, make_item, currency_setup, set_price)
    dungeon = Dungeon(name="副本B")
    db.add(dungeon)
    db.flush()

    payload = DungeonRunCreate(
        dungeon_id=dungeon.id,
        started_at=datetime.now(timezone.utc),
        repairs=[RepairLineCreate(item_id=block.id, quantity=2)],
    )
    run = DungeonService(db).create_run(payload)
    # 2 钻石块 = 18 钻石
    e = compute_run_economy(db, run)
    assert e["repair_cost"] == Decimal(18)
