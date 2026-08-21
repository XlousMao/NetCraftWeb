"""Item Master —— 整个系统的核心主数据实体。

所有其他业务（掉落/收购/价格/维修/炼金/制造/消耗/产出/分析）都必须通过
item_id 引用本表，禁止使用孤立的物品名称字符串。

V3：价格不再是 Item 属性，改由 market_observations 记录（市场事件）。
一个物品可拥有多个 Role（货币/材料/装备/掉落…）。
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    JSON,
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

# 物品角色（一个物品可同时具备多个）
ITEM_ROLES = (
    "MATERIAL",
    "EQUIPMENT",
    "CONSUMABLE",
    "CURRENCY",
    "TRADEABLE",
    "DUNGEON_DROP",
    "REPAIR_MATERIAL",
    "RECIPE_MATERIAL",
    "RECIPE_OUTPUT",
)


class Item(Base, TimestampMixin):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(128))
    category: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    subcategory: Mapped[Optional[str]] = mapped_column(String(64))
    description: Mapped[Optional[str]] = mapped_column(Text)
    icon_url: Mapped[Optional[str]] = mapped_column(String(512))
    rarity: Mapped[Optional[str]] = mapped_column(String(32))
    level: Mapped[Optional[int]] = mapped_column(Integer)
    stack_size: Mapped[Optional[int]] = mapped_column(Integer)
    tags: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    importance_score: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    roles: Mapped[List["ItemRole"]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )
    images: Mapped[List["ItemImage"]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )
    market_observations: Mapped[List["MarketObservation"]] = relationship(
        back_populates="item",
        cascade="all, delete-orphan",
        foreign_keys="MarketObservation.item_id",
    )
    relations_out: Mapped[List["ItemRelation"]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )


class ItemRole(Base, TimestampMixin):
    """物品角色（多对多语义，一个物品可属于多个角色）。"""

    __tablename__ = "item_roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), index=True)
    role: Mapped[str] = mapped_column(String(32), index=True, nullable=False)

    item: Mapped["Item"] = relationship(back_populates="roles")


class ItemImage(Base, TimestampMixin):
    __tablename__ = "item_images"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), index=True)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), index=True)  # SHA-256 去重
    image_type: Mapped[str] = mapped_column(String(32), default="icon")  # icon/screenshot/wiki/evidence
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    width: Mapped[Optional[int]] = mapped_column(Integer)
    height: Mapped[Optional[int]] = mapped_column(Integer)

    item: Mapped["Item"] = relationship(back_populates="images")


class ItemRelation(Base, TimestampMixin):
    """物品关系：Dungeon DROPS Item / Recipe CONSUMES+PRODUCES Item / 维修 REQUIRES Item 等。

    通过 source_type + source_id 指向具体业务实体，target_item_id 指向物品。
    关系类型可扩展。
    """

    __tablename__ = "item_relations"

    id: Mapped[int] = mapped_column(primary_key=True)
    relation_type: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    source_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    target_item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=1)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSON, default=dict)

    item: Mapped["Item"] = relationship(back_populates="relations_out")
