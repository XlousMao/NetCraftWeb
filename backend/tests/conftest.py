"""pytest 夹具：独立内存 SQLite 数据库 + 货币体系辅助。"""

import os
import sys
from pathlib import Path

# 确保 backend 根目录在 sys.path，可导入 app
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

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
    """创建物品的辅助函数。"""
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
    from decimal import Decimal

    from app.models.currency import (
        CurrencyConversionRule,
        CurrencyDenomination,
        CurrencySystem,
    )
    from app.models.item import ItemRole

    diamond = make_item("钻石", category="货币", vendor_buy_price=1)
    diamond_block = make_item("钻石块", category="货币")
    diamond_crystal = make_item("钻石结晶", category="货币")

    for item, role in [
        (diamond, "CURRENCY"),
        (diamond_block, "CURRENCY"),
        (diamond_crystal, "CURRENCY"),
    ]:
        db.add(ItemRole(item_id=item.id, role=role))

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
