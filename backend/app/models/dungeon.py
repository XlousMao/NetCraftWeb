"""副本系统：Dungeon / DungeonRun / Loot / Consumption / Repair。

V3：副本只记录「事实」（item_id + quantity + 时间），不保存估值快照与利润。
利润由 Analysis Service 按时间动态查询 MarketObservation 历史价计算，
这样价格体系重构后，历史副本利润始终反映当时的真实价格。
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin


class Dungeon(Base, TimestampMixin):
    __tablename__ = "dungeons"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    icon_url: Mapped[Optional[str]] = mapped_column(String(512))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    runs: Mapped[List["DungeonRun"]] = relationship(back_populates="dungeon")


class DungeonRun(Base, TimestampMixin):
    __tablename__ = "dungeon_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    dungeon_id: Mapped[int] = mapped_column(ForeignKey("dungeons.id"), index=True)

    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    travel_minutes: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=0)
    combat_minutes: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=0)
    death_count: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    dungeon: Mapped["Dungeon"] = relationship(back_populates="runs")
    loots: Mapped[List["DungeonLoot"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    consumptions: Mapped[List["DungeonConsumption"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    repairs: Mapped[List["DungeonRepair"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )

    @property
    def total_duration_minutes(self) -> Decimal:
        """总时长 = 赶路 + 战斗（派生，不落库）。"""
        return Decimal(self.travel_minutes or 0) + Decimal(self.combat_minutes or 0)


class DungeonLoot(Base, TimestampMixin):
    __tablename__ = "dungeon_loots"

    id: Mapped[int] = mapped_column(primary_key=True)
    dungeon_run_id: Mapped[int] = mapped_column(ForeignKey("dungeon_runs.id"), index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)

    run: Mapped["DungeonRun"] = relationship(back_populates="loots")
    item: Mapped["Item"] = relationship(foreign_keys=[item_id])


class DungeonConsumption(Base, TimestampMixin):
    __tablename__ = "dungeon_consumptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    dungeon_run_id: Mapped[int] = mapped_column(ForeignKey("dungeon_runs.id"), index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)

    run: Mapped["DungeonRun"] = relationship(back_populates="consumptions")
    item: Mapped["Item"] = relationship(foreign_keys=[item_id])


class DungeonRepair(Base, TimestampMixin):
    """副本维修明细：本次维修消耗的任意 Item（材料 + 钻石 + 钻石块…）。"""

    __tablename__ = "dungeon_repairs"

    id: Mapped[int] = mapped_column(primary_key=True)
    dungeon_run_id: Mapped[int] = mapped_column(ForeignKey("dungeon_runs.id"), index=True)
    equipment_id: Mapped[Optional[int]] = mapped_column(ForeignKey("equipments.id"))
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=0)

    run: Mapped["DungeonRun"] = relationship(back_populates="repairs")
    item: Mapped["Item"] = relationship(foreign_keys=[item_id])
