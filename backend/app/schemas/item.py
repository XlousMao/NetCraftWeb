"""物品相关 Schema。"""

from datetime import datetime
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
    vendor_buy_price: Optional[float] = None
    market_price: Optional[float] = None
    manual_price: Optional[float] = None
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
    vendor_buy_price: Optional[float] = None
    market_price: Optional[float] = None
    manual_price: Optional[float] = None
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


class PriceHistoryCreate(BaseModel):
    price_type: str = "vendor"  # vendor | market | manual
    price: float = Field(..., gt=0)
    quantity: Optional[float] = None
    source: Optional[str] = None
    observed_at: Optional[datetime] = None


class PriceHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    item_id: int
    price_type: str
    price: float
    quantity: Optional[float] = None
    source: Optional[str] = None
    observed_at: datetime
    created_at: datetime


class PriceStats(BaseModel):
    price_type: str
    latest: Optional[float] = None
    avg: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None
    count: int = 0


class ItemRelationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    relation_type: str
    source_type: str
    source_id: int
    target_item_id: int
    quantity: float
    metadata_: Optional[dict] = Field(default=None, alias="metadata")
    created_at: datetime


class ItemDetailOut(ItemOut):
    images: List[ItemImageOut] = Field(default_factory=list)
    price_history: List[PriceHistoryOut] = Field(default_factory=list)
    relations: List[ItemRelationOut] = Field(default_factory=list)
