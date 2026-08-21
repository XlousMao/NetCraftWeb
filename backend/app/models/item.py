"""Item Master —— 整个系统的核心主数据实体。

所有其他业务（掉落/收购/价格/维修/炼金/制造/消耗/产出/分析）都必须通过
item_id 引用本表，禁止使用孤立的物品名称字符串。
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin


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

    # 三种价值来源（当前值，历史见 item_price_history）
    vendor_buy_price: Mapped[Optional[float]] = mapped_column(Float)
    market_price: Mapped[Optional[float]] = mapped_column(Float)
    manual_price: Mapped[Optional[float]] = mapped_column(Float)

    importance_score: Mapped[float] = mapped_column(Float, default=0.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    images: Mapped[List["ItemImage"]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )
    price_history: Mapped[List["ItemPriceHistory"]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )
    relations_out: Mapped[List["ItemRelation"]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )


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


class ItemPriceHistory(Base, TimestampMixin):
    __tablename__ = "item_price_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), index=True)
    price_type: Mapped[str] = mapped_column(String(32), nullable=False)  # vendor/market/manual
    price: Mapped[float] = mapped_column(Float, nullable=False)
    quantity: Mapped[Optional[float]] = mapped_column(Float)
    source: Mapped[Optional[str]] = mapped_column(String(64))
    observed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    item: Mapped["Item"] = relationship(back_populates="price_history")


class ItemRelation(Base, TimestampMixin):
    """物品关系：Dungeon DROPS Item / Recipe CONSUMES/PRODUCES Item / 维修 REQUIRES Item 等。

    通过 source_type + source_id 指向具体业务实体，target_item_id 指向物品。
    关系类型可扩展。
    """

    __tablename__ = "item_relations"

    id: Mapped[int] = mapped_column(primary_key=True)
    relation_type: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    source_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    target_item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), index=True)
    quantity: Mapped[float] = mapped_column(Float, default=1.0)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSON, default=dict)

    item: Mapped["Item"] = relationship(back_populates="relations_out")
