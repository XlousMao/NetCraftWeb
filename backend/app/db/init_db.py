"""数据库初始化与建表。"""

from app.db.base import Base
from app.db.session import engine


def init_db() -> None:
    """创建所有表。"""
    import app.models  # noqa: F401  确保模型已注册

    Base.metadata.create_all(bind=engine)
