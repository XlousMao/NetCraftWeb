"""炼金 / 生产系统。配方材料与产出均引用 item_id，不另建物品体系。

V2：配方材料统一为 item_id + quantity，支持多货币材料（材料 + 钻石 + 钻石块）。
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin


class Recipe(Base, TimestampMixin):
    __tablename__ = "recipes"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    category: Mapped[Optional[str]] = mapped_column(String(64))
    description: Mapped[Optional[str]] = mapped_column(Text)
    expected_success_rate: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=1)  # 0~1
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    materials: Mapped[List["RecipeMaterial"]] = relationship(
        back_populates="recipe", cascade="all, delete-orphan"
    )
    outputs: Mapped[List["RecipeOutput"]] = relationship(
        back_populates="recipe", cascade="all, delete-orphan"
    )
    records: Mapped[List["ProductionRecord"]] = relationship(back_populates="recipe")


class RecipeMaterial(Base, TimestampMixin):
    __tablename__ = "recipe_materials"

    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id"), index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)

    recipe: Mapped["Recipe"] = relationship(back_populates="materials")
    item: Mapped["Item"] = relationship()


class RecipeOutput(Base, TimestampMixin):
    __tablename__ = "recipe_outputs"

    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id"), index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)

    recipe: Mapped["Recipe"] = relationship(back_populates="outputs")
    item: Mapped["Item"] = relationship()


class ProductionRecord(Base, TimestampMixin):
    __tablename__ = "production_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id"), index=True)

    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    attempted_count: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    fail_count: Mapped[int] = mapped_column(Integer, default=0)

    # 成本/收益快照（基础货币 = 钻石）
    material_cost: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=0)
    actual_unit_cost: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=0)
    revenue: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=0)
    gross_profit: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=0)
    roi: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=0)
    actual_success_rate: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=0)
    fiat_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    recipe: Mapped["Recipe"] = relationship(back_populates="records")
