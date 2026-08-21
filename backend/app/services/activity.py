"""活动服务：把副本/炼金等业务统一纳入 activity_records 账本。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analysis.economy_calculator import calculate_profit_per_hour
from app.models.activity import Activity, ActivityRecord
from app.models.dungeon import DungeonRun
from app.models.recipe import ProductionRecord


class ActivityService:
    def __init__(self, db: Session):
        self.db = db

    def ensure_activity_types(self) -> None:
        """初始化六种活动类型目录。"""
        types = {
            "DUNGEON": "副本",
            "ALCHEMY": "炼金",
            "GATHERING": "采集",
            "CRAFTING": "制造",
            "TRADING": "交易",
            "OTHER": "其他",
        }
        for code, name in types.items():
            existing = self.db.execute(
                select(Activity).where(Activity.activity_type == code)
            ).scalar_one_or_none()
            if existing is None:
                self.db.add(Activity(name=name, activity_type=code))

    def _upsert_by_ref(self, reference_type: str, reference_id: int) -> Optional[ActivityRecord]:
        return self.db.execute(
            select(ActivityRecord).where(
                ActivityRecord.reference_type == reference_type,
                ActivityRecord.reference_id == reference_id,
            )
        ).scalar_one_or_none()

    def sync_dungeon_run(self, run: DungeonRun) -> ActivityRecord:
        """副本完成后同步活动账本。"""
        existing = self._upsert_by_ref("dungeon_run", run.id)
        record = existing or ActivityRecord(
            activity_type="DUNGEON",
            label=run.dungeon.name if run.dungeon else "副本",
            reference_type="dungeon_run",
            reference_id=run.id,
        )
        record.started_at = run.started_at
        record.ended_at = run.ended_at
        record.duration_minutes = run.total_duration_minutes
        record.gross_value = run.gross_value
        record.total_cost = run.total_cost
        record.net_profit = run.net_profit
        record.profit_per_hour = run.profit_per_hour
        record.notes = run.notes
        if existing is None:
            self.db.add(record)
        self.db.flush()
        return record

    def sync_production_record(self, pr: ProductionRecord) -> ActivityRecord:
        """炼金生产记录同步活动账本。"""
        existing = self._upsert_by_ref("production_record", pr.id)
        record = existing or ActivityRecord(
            activity_type="ALCHEMY",
            label=pr.recipe.name if pr.recipe else "炼金",
            reference_type="production_record",
            reference_id=pr.id,
        )
        record.started_at = pr.started_at
        record.ended_at = pr.ended_at
        record.duration_minutes = 0.0
        record.gross_value = pr.revenue
        record.total_cost = pr.material_cost
        record.net_profit = pr.gross_profit
        record.profit_per_hour = 0.0
        record.notes = pr.notes
        if existing is None:
            self.db.add(record)
        self.db.flush()
        return record

    def create_manual(
        self,
        activity_type: str,
        label: str,
        started_at: datetime,
        ended_at: Optional[datetime] = None,
        gross_value: float = 0.0,
        total_cost: float = 0.0,
        notes: Optional[str] = None,
    ) -> ActivityRecord:
        """手动创建一条活动记录（采集/制造/交易/其他）。"""
        ended_at = ended_at or started_at
        duration = max(0.0, (ended_at - started_at).total_seconds() / 60.0)
        net_profit = round(gross_value - total_cost, 4)
        record = ActivityRecord(
            activity_type=activity_type,
            label=label,
            started_at=started_at,
            ended_at=ended_at,
            duration_minutes=round(duration, 4),
            gross_value=gross_value,
            total_cost=total_cost,
            net_profit=net_profit,
            profit_per_hour=calculate_profit_per_hour(net_profit, duration),
            notes=notes,
        )
        self.db.add(record)
        self.db.flush()
        return record
