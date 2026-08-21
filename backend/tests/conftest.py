"""pytest 夹具：独立内存 SQLite 数据库。"""

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
