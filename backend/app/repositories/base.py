"""通用 Repository 基类：CRUD + 分页。"""

from __future__ import annotations

from typing import Any, Generic, Optional, Type, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.base import Base

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    def __init__(self, db: Session, model: Type[T]):
        self.db = db
        self.model = model

    def get(self, id: int) -> Optional[T]:
        return self.db.get(self.model, id)

    def list(self, limit: int = 20, offset: int = 0) -> tuple[list[T], int]:
        total = self.db.execute(
            select(func.count()).select_from(self.model)
        ).scalar_one()
        rows = (
            self.db.execute(
                select(self.model).order_by(self.model.id.desc()).offset(offset).limit(limit)
            )
            .scalars()
            .all()
        )
        return rows, total

    def create(self, **kwargs: Any) -> T:
        obj = self.model(**kwargs)
        self.db.add(obj)
        self.db.flush()
        return obj

    def update(self, id: int, **kwargs: Any) -> Optional[T]:
        obj = self.db.get(self.model, id)
        if obj is None:
            return None
        for key, value in kwargs.items():
            if value is not None:
                setattr(obj, key, value)
        self.db.flush()
        return obj

    def delete(self, id: int) -> bool:
        obj = self.db.get(self.model, id)
        if obj is None:
            return False
        self.db.delete(obj)
        self.db.flush()
        return True
