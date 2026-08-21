"""历史价格按时间生效测试（P0 级要求）。

估价按 observed_at 取最近有效市场观察，而非单一当前价。
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.services.valuation import ValuationService


def test_historical_price_by_time(db, make_item, set_price):
    """估价按 observed_at 取最近有效历史价格。"""
    item = make_item("精钢锭")
    now = datetime.now(timezone.utc)
    # 历史价格：3 天前 80；当前价格 120
    set_price(item.id, 80, "NPC_PRICE", observed_at=now - timedelta(days=3))
    set_price(item.id, 120, "NPC_PRICE", observed_at=now)

    vs = ValuationService(db)
    price, _ = vs.get_unit_price(item.id, "auto", now - timedelta(days=3))
    assert price == Decimal(80)
    price, _ = vs.get_unit_price(item.id, "auto", now)
    assert price == Decimal(120)


def test_no_future_price(db, make_item, set_price):
    """不能使用未来价格。"""
    item = make_item("秘银锭")
    now = datetime.now(timezone.utc)
    set_price(item.id, 200, "NPC_PRICE", observed_at=now + timedelta(days=1))

    vs = ValuationService(db)
    price, source = vs.get_unit_price(item.id, "auto", now)
    # 未来价格不可用，回退为 0
    assert price == Decimal(0)
    assert source == "none"
