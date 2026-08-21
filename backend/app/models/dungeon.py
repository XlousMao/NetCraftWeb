"""副本系统：Dungeon / DungeonRun / Loot / Cost(Consumption) / Repair。

所有掉落与成本必须引用 item_id，并在发生时保存估值快照
（unit_price + currency + base_currency_value + fiat_value），
确保历史记录不被当前价格污染。
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

    # 计算结果快照（单位：基础货币 = 钻石；历史稳定）
    total_duration_minutes: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=0)
    gross_value: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=0)
    repair_cost: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=0)
    consumable_cost: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=0)
    other_cost: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=0)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=0)
    net_profit: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=0)
    profit_per_hour: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=0)
    # RMB 估值（基于记录时的汇率快照，非实际可兑现价格）
    gross_value_fiat: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))
    net_profit_fiat: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))
    profit_per_hour_fiat: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))

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


class DungeonLoot(Base, TimestampMixin):
    __tablename__ = "dungeon_loots"

    id: Mapped[int] = mapped_column(primary_key=True)
    dungeon_run_id: Mapped[int] = mapped_column(ForeignKey("dungeon_runs.id"), index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)

    # 估值快照（发生时的价格，历史不可变）
    valuation_unit_price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    valuation_total: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    valuation_source: Mapped[str] = mapped_column(String(32), nullable=False)
    valuation_currency_item_id: Mapped[Optional[int]] = mapped_column(ForeignKey("items.id"))
    base_currency_value: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    fiat_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))
    valuation_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    run: Mapped["DungeonRun"] = relationship(back_populates="loots")
    item: Mapped["Item"] = relationship(foreign_keys=[item_id])


class DungeonConsumption(Base, TimestampMixin):
    __tablename__ = "dungeon_consumptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    dungeon_run_id: Mapped[int] = mapped_column(ForeignKey("dungeon_runs.id"), index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)

    valuation_unit_price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    valuation_total: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    valuation_source: Mapped[str] = mapped_column(String(32), nullable=False)
    valuation_currency_item_id: Mapped[Optional[int]] = mapped_column(ForeignKey("items.id"))
    base_currency_value: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    fiat_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))
    valuation_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    run: Mapped["DungeonRun"] = relationship(back_populates="consumptions")
    item: Mapped["Item"] = relationship(foreign_keys=[item_id])


class DungeonRepair(Base, TimestampMixin):
    """副本维修明细：本次维修消耗的任意 Item（材料 + 钻石 + 钻石块…）及估值快照。"""

    __tablename__ = "dungeon_repairs"

    id: Mapped[int] = mapped_column(primary_key=True)
    dungeon_run_id: Mapped[int] = mapped_column(ForeignKey("dungeon_runs.id"), index=True)
    equipment_id: Mapped[Optional[int]] = mapped_column(ForeignKey("equipments.id"))
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=0)
    valuation_unit_price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    material_cost: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=0)
    valuation_source: Mapped[str] = mapped_column(String(32), default="vendor")
    valuation_currency_item_id: Mapped[Optional[int]] = mapped_column(ForeignKey("items.id"))
    base_currency_value: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=0)
    fiat_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))

    run: Mapped["DungeonRun"] = relationship(back_populates="repairs")
    item: Mapped["Item"] = relationship(foreign_keys=[item_id])
