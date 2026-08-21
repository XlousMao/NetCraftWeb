"""物品关系服务：自动维护 recipe/equipment/dungeon 与 item 的关系。

关系类型（可扩展）：
  Dungeon -> DROPS -> Item
  Recipe -> CONSUMES -> Item
  Recipe -> PRODUCES -> Item
  Equipment -> REQUIRES_REPAIR -> Item
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.dungeon import Dungeon, DungeonLoot, DungeonRun
from app.models.equipment import Equipment
from app.models.item import Item, ItemRelation
from app.models.recipe import Recipe


class RelationService:
    def __init__(self, db: Session):
        self.db = db

    def _upsert(
        self,
        relation_type: str,
        source_type: str,
        source_id: int,
        target_item_id: int,
        quantity: float,
    ) -> None:
        existing = self.db.execute(
            select(ItemRelation).where(
                ItemRelation.relation_type == relation_type,
                ItemRelation.source_type == source_type,
                ItemRelation.source_id == source_id,
                ItemRelation.target_item_id == target_item_id,
            )
        ).scalar_one_or_none()
        if existing:
            existing.quantity = quantity
        else:
            self.db.add(
                ItemRelation(
                    relation_type=relation_type,
                    source_type=source_type,
                    source_id=source_id,
                    target_item_id=target_item_id,
                    quantity=quantity,
                )
            )

    def _clear_source(self, relation_type: str, source_type: str, source_id: int) -> None:
        rows = self.db.execute(
            select(ItemRelation).where(
                ItemRelation.relation_type == relation_type,
                ItemRelation.source_type == source_type,
                ItemRelation.source_id == source_id,
            )
        ).scalars().all()
        for r in rows:
            self.db.delete(r)

    def sync_recipe(self, recipe: Recipe) -> None:
        self._clear_source("CONSUMES", "recipe", recipe.id)
        self._clear_source("PRODUCES", "recipe", recipe.id)
        for m in recipe.materials:
            self._upsert("CONSUMES", "recipe", recipe.id, m.item_id, m.quantity)
        for o in recipe.outputs:
            self._upsert("PRODUCES", "recipe", recipe.id, o.item_id, o.quantity)

    def sync_equipment(self, equipment: Equipment) -> None:
        self._clear_source("REQUIRES_REPAIR", "equipment", equipment.id)
        for r in equipment.repair_requirements:
            self._upsert(
                "REQUIRES_REPAIR", "equipment", equipment.id, r.item_id, r.quantity
            )

    def sync_dungeon_drop(self, dungeon_id: int, item_id: int, quantity: float) -> None:
        self._upsert("DROPS", "dungeon", dungeon_id, item_id, quantity)

    def sync_dungeon_run_drops(self, run: DungeonRun) -> None:
        """副本记录落库后，把掉落物品登记为该副本的产出。"""
        for loot in run.loots:
            self.sync_dungeon_drop(run.dungeon_id, loot.item_id, loot.quantity)

    def sync_all(self) -> None:
        """全量重建关系（Demo 种子后调用）。"""
        for r in self.db.execute(select(Recipe)).scalars().all():
            self.sync_recipe(r)
        for e in self.db.execute(select(Equipment)).scalars().all():
            self.sync_equipment(e)
        for d in self.db.execute(select(Dungeon)).scalars().all():
            # 从掉落记录归纳副本产出
            rows = self.db.execute(
                select(DungeonLoot.item_id, func.sum(DungeonLoot.quantity))
                .join(DungeonRun, DungeonLoot.dungeon_run_id == DungeonRun.id)
                .where(DungeonRun.dungeon_id == d.id)
                .group_by(DungeonLoot.item_id)
            ).all()
            for item_id, qty in rows:
                self._upsert("DROPS", "dungeon", d.id, item_id, float(qty))
