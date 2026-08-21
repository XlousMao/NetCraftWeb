"""历史价格按时间生效测试（P0 级要求）。

更新当前价格不能改变历史副本收益；不同日期的副本分别使用当日价格。
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.models.dungeon import Dungeon, DungeonRun
from app.schemas.dungeon import DungeonRunCreate, LootCreate
from app.services.dungeon import DungeonService
from app.services.valuation import ValuationService


def test_historical_price_by_time(db, make_item):
    """估价按 observed_at 取最近有效历史价格，而非当前价。"""
    item = make_item("精钢锭")
    now = datetime.now(timezone.utc)
    vs = ValuationService(db)
    # 历史价格：3 天前 80
    vs.record_price(
        item.id, "vendor", Decimal(80), source="test",
        observed_at=now - timedelta(days=3),
    )
    # 当前价格：120
    vs.record_price(
        item.id, "vendor", Decimal(120), source="test",
        observed_at=now,
    )
    db.flush()

    # 3 天前估价 → 用 80
    price, _, _ = vs.get_unit_price(item.id, "vendor", now - timedelta(days=3))
    assert price == Decimal(80)
    # 现在估价 → 用当前 120
    price, _, _ = vs.get_unit_price(item.id, "vendor", now)
    assert price == Decimal(120)


def test_dungeon_uses_historical_snapshot(db, make_item):
    """修改当前价格后，历史副本收益保持不变。"""
    item = make_item("精钢锭", vendor_buy_price=80)
    dungeon = Dungeon(name="副本A")
    db.add(dungeon)
    db.flush()

    payload = DungeonRunCreate(
        dungeon_id=dungeon.id,
        started_at=datetime.now(timezone.utc) - timedelta(hours=1),
        loots=[LootCreate(item_id=item.id, quantity=30)],
    )
    run = DungeonService(db).create_run(payload)
    assert run.gross_value == Decimal(2400)  # 30 × 80

    # 现在把精钢锭商人价从 80 改为 120
    item.vendor_buy_price = Decimal(120)
    db.flush()

    # 历史记录快照应保持 80 不变
    assert run.loots[0].valuation_unit_price == Decimal(80)
    assert run.gross_value == Decimal(2400)
