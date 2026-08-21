"""估值引擎与市场观察测试（Decimal）。"""

from decimal import Decimal

from app.services.valuation import ValuationService


def test_valuation_auto_fallback_to_sell_offer(db, make_item, set_price):
    # 只有 SELL_OFFER，auto 应回退到它
    item = make_item("测试物")
    set_price(item.id, 105, "SELL_OFFER")
    vs = ValuationService(db)
    price, source = vs.get_unit_price(item.id, "auto")
    assert price == Decimal(105)
    assert source.startswith("SELL_OFFER")


def test_valuation_manual_priority(db, make_item, set_price):
    # MANUAL_ESTIMATE 优先级最高
    item = make_item("测试物2")
    set_price(item.id, 80, "NPC_PRICE")
    set_price(item.id, 105, "SELL_OFFER")
    set_price(item.id, 130, "MANUAL_ESTIMATE")
    vs = ValuationService(db)
    price, source = vs.get_unit_price(item.id, "auto")
    assert price == Decimal(130)
    assert source.startswith("MANUAL_ESTIMATE")


def test_npc_price_priority_over_sell(db, make_item, set_price):
    # NPC_PRICE 优先于 SELL_OFFER
    item = make_item("测试物3")
    set_price(item.id, 105, "SELL_OFFER")
    set_price(item.id, 80, "NPC_PRICE")
    vs = ValuationService(db)
    price, source = vs.get_unit_price(item.id, "auto")
    assert price == Decimal(80)
    assert source.startswith("NPC_PRICE")


def test_market_summary(db, make_item, set_price):
    item = make_item("精钢锭")
    set_price(item.id, 80, "NPC_PRICE")
    set_price(item.id, 105, "SELL_OFFER")
    set_price(item.id, 90, "BUY_ORDER")
    vs = ValuationService(db)
    s = vs.market_summary(item.id)
    assert s["count"] == 3
    assert s["max"] == 105.0
    assert s["min"] == 80.0
    assert s["highest_buy_order"] == 90.0
    assert s["lowest_sell_offer"] == 105.0
