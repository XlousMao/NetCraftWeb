"""统一活动系统。activity_records 是所有活动的统一账本，
副本 / 炼金记录完成后会自动同步一条活动记录（引用来源）。"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin

# 活动类型常量
ACTIVITY_TYPES = ("DUNGEON", "ALCHEMY", "GATHERING", "CRAFTING", "TRADING", "OTHER")


class Activity(Base, TimestampMixin):
    """活动定义（目录）。"""

    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    activity_type: Mapped[str] = mapped_column(String(32), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    records: Mapped[list["ActivityRecord"]] = relationship(back_populates="activity")


class ActivityRecord(Base, TimestampMixin):
    """统一活动账本记录。"""

    __tablename__ = "activity_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    activity_type: Mapped[str] = mapped_column(String(32), index=True)
    activity_id: Mapped[Optional[int]] = mapped_column(ForeignKey("activities.id"), index=True)
    label: Mapped[str] = mapped_column(String(128))

    # 来源引用（可空，手动记录为空）
    reference_type: Mapped[Optional[str]] = mapped_column(String(32))
    reference_id: Mapped[Optional[int]] = mapped_column(Integer)

    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    duration_minutes: Mapped[float] = mapped_column(Float, default=0.0)

    gross_value: Mapped[float] = mapped_column(Float, default=0.0)
    total_cost: Mapped[float] = mapped_column(Float, default=0.0)
    net_profit: Mapped[float] = mapped_column(Float, default=0.0)
    profit_per_hour: Mapped[float] = mapped_column(Float, default=0.0)

    notes: Mapped[Optional[str]] = mapped_column(Text)

    activity: Mapped[Optional["Activity"]] = relationship(back_populates="records")
