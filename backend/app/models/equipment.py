"""装备与维修系统。

V2：维修需求不再有 currency_cost 这种单独字段，统一建模为「任意数量的 Item 消耗」。
钻石、精钢锭等在数据库层没有区别，都是 Repair Requirement Item，
只有 Currency System 再决定货币类 Item 的基础价值。
"""

from decimal import Decimal
from typing import List, Optional

from sqlalchemy import Boolean, ForeignKey, Numeric, String, Text
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
    """维修需求：每一行就是一个 Item 的消耗量。"""

    __tablename__ = "equipment_repair_requirements"

    id: Mapped[int] = mapped_column(primary_key=True)
    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipments.id"), index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)

    equipment: Mapped["Equipment"] = relationship(back_populates="repair_requirements")
    item: Mapped["Item"] = relationship()
