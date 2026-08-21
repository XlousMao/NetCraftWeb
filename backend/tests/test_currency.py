"""货币换算测试：验证 1钻石=1 / 1钻石块=9 / 1钻石结晶=99，及换算推导。"""

from decimal import Decimal

from app.services.currency import CurrencyService


def test_denomination_base_values(db, currency_setup):
    svc = CurrencyService(db)
    diamond = currency_setup["钻石"]
    block = currency_setup["钻石块"]
    crystal = currency_setup["钻石结晶"]

    assert svc.to_base_factor(diamond.id) == Decimal(1)
    assert svc.to_base_factor(block.id) == Decimal(9)
    # 钻石结晶 → 钻石块(11) → 钻石(9) = 99
    assert svc.to_base_factor(crystal.id) == Decimal(99)


def test_convert_blocks_to_diamond(db, currency_setup):
    svc = CurrencyService(db)
    block = currency_setup["钻石块"]
    diamond = currency_setup["钻石"]
    assert svc.convert(Decimal(10), block.id, diamond.id) == Decimal(90)


def test_convert_crystals_to_diamond(db, currency_setup):
    svc = CurrencyService(db)
    crystal = currency_setup["钻石结晶"]
    diamond = currency_setup["钻石"]
    assert svc.convert(Decimal(3), crystal.id, diamond.id) == Decimal(297)


def test_to_base_block_and_crystal(db, currency_setup):
    svc = CurrencyService(db)
    block = currency_setup["钻石块"]
    crystal = currency_setup["钻石结晶"]
    assert svc.to_base(block.id, Decimal(10)) == Decimal(90)
    assert svc.to_base(crystal.id, Decimal(3)) == Decimal(297)
