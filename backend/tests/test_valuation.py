"""估值引擎与价格历史测试。"""

from datetime import datetime, timedelta, timezone

from app.services.valuation import ValuationService


def test_valuation_auto_policy(db, make_item):
    # 只有 market 有值，auto 应回退到 market
    item = make_item("测试物", vendor_buy_price=None, market_price=105, manual_price=None)
    vs = ValuationService(db)
    price, source = vs.get_unit_price(item.id, "auto")
    assert price == 105.0
    assert source == "market"


def test_valuation_manual_priority(db, make_item):
    item = make_item("测试物2", vendor_buy_price=80, market_price=105, manual_price=130)
    vs = ValuationService(db)
    price, source = vs.get_unit_price(item.id, "auto")
    assert price == 130.0
    assert source == "manual"


def test_record_price_updates_current_and_history(db, make_item):
    item = make_item("精钢锭", vendor_buy_price=80)
    vs = ValuationService(db)
    vs.record_price(item.id, "vendor", 120, source="test", observed_at=datetime.now(timezone.utc))
    db.flush()

    assert item.vendor_buy_price == 120.0
    stats = vs.price_stats(item.id, "vendor")
    assert stats["count"] == 1
    assert stats["latest"] == 120.0
