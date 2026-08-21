"""物品仓储：搜索 / 分类筛选 / 排序 / 关联计数。"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.item import Item, ItemImage, ItemRelation
from app.repositories.base import BaseRepository


class ItemRepository(BaseRepository[Item]):
    def __init__(self, db: Session):
        super().__init__(db, Item)

    def search(
        self,
        q: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[list[str]] = None,
        sort: str = "name",
        order: str = "asc",
        active_only: bool = True,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Item], int]:
        stmt = select(Item)
        if active_only:
            stmt = stmt.where(Item.is_active.is_(True))
        if q:
            like = f"%{q}%"
            stmt = stmt.where(or_(Item.name.ilike(like), Item.display_name.ilike(like)))
        if category:
            stmt = stmt.where(Item.category == category)
        if tags:
            for tag in tags:
                stmt = stmt.where(Item.tags.contains([tag]))

        # 排序（价值排序改用重要性评分，因价格已移至市场观察表）
        sort_map = {
            "name": Item.name,
            "value": Item.importance_score,
            "importance": Item.importance_score,
            "created": Item.created_at,
        }
        col = sort_map.get(sort, Item.name)
        stmt = stmt.order_by(col.desc() if order == "desc" else col.asc())

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.execute(count_stmt).scalar_one()
        rows = self.db.execute(stmt.offset(offset).limit(limit)).scalars().all()
        return rows, total

    def with_counts(self, item_id: int) -> tuple[int, int]:
        """返回 (image_count, relation_count)。"""
        img = self.db.execute(
            select(func.count()).select_from(ItemImage).where(ItemImage.item_id == item_id)
        ).scalar_one()
        rel = self.db.execute(
            select(func.count()).select_from(ItemRelation).where(
                ItemRelation.target_item_id == item_id
            )
        ).scalar_one()
        return img, rel
