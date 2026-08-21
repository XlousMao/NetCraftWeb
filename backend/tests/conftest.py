"""pytest 夹具：独立内存 SQLite 数据库 + 货币体系 + 市场观察辅助。"""

import os
import sys
from pathlib import Path

# 确保 backend 根目录在 sys.path，可导入 app
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
import app.models  # noqa: F401

# 测试使用独立内存数据库
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def engine():
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=None,
    )
    return engine


@pytest.fixture(scope="function")
def db(engine):
    """每个测试独立的 schema + 会话。"""
    connection = engine.connect()
    Base.metadata.create_all(connection)
    Session = sessionmaker(bind=connection, autoflush=False, autocommit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        connection.close()


@pytest.fixture()
def make_item(db):
    """创建物品的辅助函数（价格由市场观察记录，非 Item 属性）。"""
    from app.models.item import Item

    def _make(name, **kwargs):
        item = Item(name=name, **kwargs)
        db.add(item)
        db.flush()
        return item

    return _make


@pytest.fixture()
def currency_setup(db, make_item):
    """建立「奶块钻石经济体系」：钻石(1) / 钻石块(9) / 钻石结晶(99)。

    返回 {name: Item}。
    """
    from app.models.currency import (
        CurrencyConversionRule,
        CurrencyDenomination,
        CurrencySystem,
    )
    from app.models.item import ItemRole

    diamond = make_item("钻石", category="货币")
    diamond_block = make_item("钻石块", category="货币")
    diamond_crystal = make_item("钻石结晶", category="货币")

    for item in (diamond, diamond_block, diamond_crystal):
        db.add(ItemRole(item_id=item.id, role="CURRENCY"))

    system = CurrencySystem(name="奶块钻石经济体系", base_currency_item_id=diamond.id)
    db.add(system)
    db.flush()

    for item, base_value, is_base in [
        (diamond, Decimal(1), True),
        (diamond_block, Decimal(9), False),
        (diamond_crystal, Decimal(99), False),
    ]:
        db.add(
            CurrencyDenomination(
                currency_system_id=system.id,
                item_id=item.id,
                base_value=base_value,
                is_base=is_base,
            )
        )

    db.add(
        CurrencyConversionRule(
            currency_system_id=system.id,
            from_item_id=diamond_block.id,
            to_item_id=diamond.id,
            factor=Decimal(9),
        )
    )
    db.add(
        CurrencyConversionRule(
            currency_system_id=system.id,
            from_item_id=diamond_crystal.id,
            to_item_id=diamond_block.id,
            factor=Decimal(11),
        )
    )
    db.flush()
    return {"钻石": diamond, "钻石块": diamond_block, "钻石结晶": diamond_crystal}


@pytest.fixture()
def set_price(db, currency_setup):
    """记录一条市场观察（默认 NPC_PRICE，钻石计价），返回 helper。"""
    from app.services.valuation import ValuationService

    diamond = currency_setup["钻石"]
    vs = ValuationService(db)

    def _set(item_id, price, obs_type="NPC_PRICE", observed_at=None):
        vs.record_observation(
            item_id,
            obs_type,
            Decimal(str(price)),
            price_item_id=diamond.id,
            observed_at=observed_at or datetime.now(timezone.utc),
        )
        db.flush()

    return _set
