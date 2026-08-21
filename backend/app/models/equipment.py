"""装备与维修系统。装备维修需求引用 item_id（材料）。"""

from typing import List, Optional

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin


class Equipment(Base, TimestampMixin):
    __tablename__ = "equipments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    icon_url: Mapped[Optional[str]] = mapped_column(String(512))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    repair_requirements: Mapped[List["EquipmentRepairRequirement"]] = relationship(
        back_populates="equipment", cascade="all, delete-orphan"
    )


class EquipmentRepairRequirement(Base, TimestampMixin):
    __tablename__ = "equipment_repair_requirements"

    id: Mapped[int] = mapped_column(primary_key=True)
    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipments.id"), index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), index=True)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    currency_cost: Mapped[float] = mapped_column(Float, default=0.0)

    equipment: Mapped["Equipment"] = relationship(back_populates="repair_requirements")
    item: Mapped["Item"] = relationship()
