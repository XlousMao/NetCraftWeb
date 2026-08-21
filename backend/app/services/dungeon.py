"""副本服务：创建/更新副本记录（只保存事实：item_id + quantity + 时间）。

V3：副本不保存估值快照与利润，利润由 Analysis 动态计算。
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.dungeon import (
    Dungeon,
    DungeonConsumption,
    DungeonLoot,
    DungeonRepair,
    DungeonRun,
)
from app.models.equipment import Equipment
from app.schemas.dungeon import (
    ConsumptionCreate,
    DungeonRunCreate,
    LootCreate,
    RepairLineCreate,
)
from app.services.activity import ActivityService


class DungeonService:
    def __init__(self, db: Session):
        self.db = db
        self.activity = ActivityService(db)

    def create_run(self, payload: DungeonRunCreate) -> DungeonRun:
        """创建副本记录（事务由调用方保证）。"""
        run = DungeonRun(
            dungeon_id=payload.dungeon_id,
            started_at=payload.started_at,
            ended_at=payload.ended_at,
            travel_minutes=Decimal(payload.travel_minutes),
            combat_minutes=Decimal(payload.combat_minutes),
            death_count=payload.death_count,
            notes=payload.notes,
        )
        self.db.add(run)
        self.db.flush()  # 取得 run.id

        self._apply_details(run, payload)
        self.db.flush()
        self.activity.sync_dungeon_run(run)
        return run

    def update_run(self, run_id: int, payload: DungeonRunCreate) -> DungeonRun:
        """更新副本记录：删除旧明细，按新数据重写事实。"""
        run = self.db.get(DungeonRun, run_id)
        if run is None:
            raise ValueError(f"副本记录 {run_id} 不存在")

        run.dungeon_id = payload.dungeon_id
        run.started_at = payload.started_at
        run.ended_at = payload.ended_at
        run.travel_minutes = Decimal(payload.travel_minutes)
        run.combat_minutes = Decimal(payload.combat_minutes)
        run.death_count = payload.death_count
        run.notes = payload.notes

        for l in list(run.loots):
            self.db.delete(l)
        for c in list(run.consumptions):
            self.db.delete(c)
        for r in list(run.repairs):
            self.db.delete(r)
        self.db.flush()

        self._apply_details(run, payload)
        self.db.flush()
        self.activity.sync_dungeon_run(run)
        return run

    def _apply_details(self, run: DungeonRun, payload: DungeonRunCreate) -> None:
        """记录掉落/消耗/维修的事实（item_id + quantity）。"""
        for loot in payload.loots:
            self.db.add(
                DungeonLoot(
                    dungeon_run_id=run.id,
                    item_id=loot.item_id,
                    quantity=Decimal(loot.quantity),
                )
            )
        for cons in payload.consumptions:
            self.db.add(
                DungeonConsumption(
                    dungeon_run_id=run.id,
                    item_id=cons.item_id,
                    quantity=Decimal(cons.quantity),
                )
            )
        for repair in payload.repairs:
            self._apply_repair(run, repair)

        run.ended_at = run.ended_at or datetime.now(timezone.utc)

    def _apply_repair(self, run: DungeonRun, repair: RepairLineCreate) -> None:
        """维修：按装备模板展开，或手动 item + quantity。"""
        if repair.equipment_id is not None:
            equipment = self.db.get(Equipment, repair.equipment_id)
            if equipment is None:
                raise ValueError(f"装备 {repair.equipment_id} 不存在")
            for req in equipment.repair_requirements:
                self.db.add(
                    DungeonRepair(
                        dungeon_run_id=run.id,
                        equipment_id=repair.equipment_id,
                        item_id=req.item_id,
                        quantity=Decimal(req.quantity),
                    )
                )
        elif repair.item_id is not None:
            self.db.add(
                DungeonRepair(
                    dungeon_run_id=run.id,
                    item_id=repair.item_id,
                    quantity=Decimal(repair.quantity or 0),
                )
            )

    def get_run(self, run_id: int) -> Optional[DungeonRun]:
        return self.db.get(DungeonRun, run_id)

    def list_runs(
        self, dungeon_id: Optional[int] = None, limit: int = 50, offset: int = 0
    ) -> tuple[List[DungeonRun], int]:
        from sqlalchemy import func, select

        stmt = select(DungeonRun)
        count_stmt = select(func.count()).select_from(DungeonRun)
        if dungeon_id is not None:
            stmt = stmt.where(DungeonRun.dungeon_id == dungeon_id)
            count_stmt = count_stmt.where(DungeonRun.dungeon_id == dungeon_id)
        total = self.db.execute(count_stmt).scalar_one()
        rows = (
            self.db.execute(
                stmt.order_by(DungeonRun.started_at.desc())
                .offset(offset)
                .limit(limit)
            )
            .scalars()
            .all()
        )
        return rows, total
