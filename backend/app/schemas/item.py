"""物品相关 Schema。"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ItemBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    display_name: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    description: Optional[str] = None
    icon_url: Optional[str] = None
    rarity: Optional[str] = None
    level: Optional[int] = None
    stack_size: Optional[int] = None
    tags: List[str] = Field(default_factory=list)
    roles: List[str] = Field(default_factory=list)
    is_active: bool = True


class ItemCreate(ItemBase):
    pass


class ItemUpdate(BaseModel):
    name: Optional[str] = None
    display_name: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    description: Optional[str] = None
    icon_url: Optional[str] = None
    rarity: Optional[str] = None
    level: Optional[int] = None
    stack_size: Optional[int] = None
    tags: Optional[List[str]] = None
    roles: Optional[List[str]] = None
    is_active: Optional[bool] = None


class ItemOut(ItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    importance_score: float = 0.0
    created_at: datetime
    updated_at: datetime
    image_count: int = 0
    relation_count: int = 0


class ItemImageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    item_id: int
    file_path: str
    file_hash: str
    image_type: str
    is_primary: bool
    width: Optional[int] = None
    height: Optional[int] = None
    created_at: datetime


# ---- 市场观察 ----

class MarketObservationCreate(BaseModel):
    observation_type: str = "SELL_OFFER"  # SELL_OFFER/BUY_ORDER/NPC_PRICE/MANUAL_ESTIMATE
    quantity: float = Field(1, gt=0)
    price_item_id: Optional[int] = None  # 为空表示基础货币（钻石）
    price_quantity: float = Field(..., gt=0)
    seller_name: Optional[str] = None
    location: Optional[str] = None
    source: Optional[str] = None
    observed_at: Optional[datetime] = None
    note: Optional[str] = None


class MarketObservationUpdate(BaseModel):
    observation_type: Optional[str] = None
    quantity: Optional[float] = Field(None, gt=0)
    price_item_id: Optional[int] = None
    price_quantity: Optional[float] = Field(None, gt=0)
    seller_name: Optional[str] = None
    location: Optional[str] = None
    source: Optional[str] = None
    observed_at: Optional[datetime] = None
    note: Optional[str] = None


class MarketObservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    item_id: int
    observation_type: str
    quantity: float
    price_item_id: Optional[int] = None
    price_quantity: float
    seller_name: Optional[str] = None
    location: Optional[str] = None
    source: Optional[str] = None
    observed_at: datetime
    note: Optional[str] = None
    created_at: datetime


class ItemRelationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    relation_type: str
    source_type: str
    source_id: int
    target_item_id: int
    quantity: float
    metadata_: Optional[dict] = Field(default=None, validation_alias="metadata_", serialization_alias="metadata")
    created_at: datetime


class ItemDetailOut(ItemOut):
    images: List[ItemImageOut] = Field(default_factory=list)
    market_observations: List[MarketObservationOut] = Field(default_factory=list)
    relations: List[ItemRelationOut] = Field(default_factory=list)
    current_value: Optional[dict] = None
    market_summary: Optional[dict] = None
    price_history: Optional[list] = None
