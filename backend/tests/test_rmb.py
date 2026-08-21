"""RMB 估值测试：基于法币观察价格换算钻石/RMB。"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.models.currency import FiatExchangeObservation
from app.services.fiat import FiatService
from app.services.valuation import ValuationService


def _add_rmb_observation(db, currency_setup, quantity, amount, observed_at):
    db.add(
        FiatExchangeObservation(
            currency_item_id=currency_setup["钻石块"].id,
            quantity=Decimal(quantity),
            fiat_currency="CNY",
            fiat_amount=Decimal(amount),
            observed_at=observed_at,
            source="test",
        )
    )
    db.flush()


def test_rmb_rate_99_blocks_27_1(db, currency_setup):
    # 99 钻石块 = 27.10 RMB
    now = datetime.now(timezone.utc)
    _add_rmb_observation(db, currency_setup, 99, "27.10", now)

    fiat = FiatService(db)
    # 1 钻石块 = 27.10/99 RMB；1 钻石 = /9
    rate = fiat.base_currency_rate(now)
    expected = Decimal("27.10") / Decimal(99) / Decimal(9)
    assert rate is not None
    assert abs(rate - expected) < Decimal("0.000001")


def test_rmb_value_of_diamond_amount(db, currency_setup):
    now = datetime.now(timezone.utc)
    _add_rmb_observation(db, currency_setup, 99, "27.10", now)

    fiat = FiatService(db)
    # 1000 钻石 = 1000 * (27.10/99/9) RMB
    value = fiat.value(Decimal(1000), now)
    expected = Decimal(1000) * Decimal("27.10") / Decimal(99) / Decimal(9)
    assert value is not None
    assert abs(value - expected) < Decimal("0.0001")


def test_rmb_uses_historical_observation(db, currency_setup):
    """RMB 汇率按 observed_at 取最近有效观察，不能用未来价格。"""
    now = datetime.now(timezone.utc)
    _add_rmb_observation(db, currency_setup, 99, "27.10", now - timedelta(days=3))
    _add_rmb_observation(db, currency_setup, 99, "30.00", now + timedelta(days=3))

    fiat = FiatService(db)
    rate = fiat.base_currency_rate(now)
    expected = Decimal("27.10") / Decimal(99) / Decimal(9)
    assert abs(rate - expected) < Decimal("0.000001")


def test_valuation_returns_diamond_and_rmb(db, currency_setup):
    """估值服务输出钻石 + RMB 双价值。"""
    now = datetime.now(timezone.utc)
    _add_rmb_observation(db, currency_setup, 99, "27.10", now)

    vs = ValuationService(db)
    # 钻石（基础货币）：1000 钻石 = 1000 钻石
    v = vs.value(currency_setup["钻石"].id, Decimal(1000), "auto", now)
    assert v.base_currency_value == Decimal(1000)
    assert v.fiat_value is not None
    expected_rmb = Decimal(1000) * Decimal("27.10") / Decimal(99) / Decimal(9)
    assert abs(v.fiat_value - expected_rmb) < Decimal("0.0001")
