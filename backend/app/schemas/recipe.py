"""炼金 / 生产 Schema。"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class RecipeMaterialIn(BaseModel):
    item_id: int
    quantity: float = Field(..., gt=0)


class RecipeOutputIn(BaseModel):
    item_id: int
    quantity: float = Field(..., gt=0)


class RecipeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    recipe_type: str = "ALCHEMY"  # ALCHEMY/CRAFT/SYNTHESIS
    category: Optional[str] = None
    description: Optional[str] = None
    expected_success_rate: float = Field(1.0, ge=0, le=1)
    materials: List[RecipeMaterialIn] = Field(default_factory=list)
    outputs: List[RecipeOutputIn] = Field(default_factory=list)


class RecipeMaterialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    recipe_id: int
    item_id: int
    item_name: Optional[str] = None
    icon_url: Optional[str] = None
    quantity: float


class RecipeOutputOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    recipe_id: int
    item_id: int
    item_name: Optional[str] = None
    icon_url: Optional[str] = None
    quantity: float


class RecipeUpdate(BaseModel):
    name: Optional[str] = None
    recipe_type: Optional[str] = None  # ALCHEMY/CRAFT/SYNTHESIS
    category: Optional[str] = None
    description: Optional[str] = None
    expected_success_rate: Optional[float] = Field(None, ge=0, le=1)
    materials: Optional[List[RecipeMaterialIn]] = None
    outputs: Optional[List[RecipeOutputIn]] = None
    is_active: Optional[bool] = None


class RecipeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    recipe_type: str = "ALCHEMY"
    category: Optional[str] = None
    description: Optional[str] = None
    expected_success_rate: float
    is_active: bool
    created_at: datetime
    materials: List[RecipeMaterialOut] = Field(default_factory=list)
    outputs: List[RecipeOutputOut] = Field(default_factory=list)


class ProductionRecordCreate(BaseModel):
    recipe_id: int
    started_at: datetime
    ended_at: Optional[datetime] = None
    attempted_count: int = Field(..., ge=0)
    success_count: int = Field(0, ge=0)
    notes: Optional[str] = None
    revenue: Optional[float] = None  # 若不传，按当前估值自动计算


class ProductionRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    recipe_id: int
    recipe_name: Optional[str] = None
    started_at: datetime
    ended_at: Optional[datetime] = None
    attempted_count: int
    success_count: int
    fail_count: int
    material_cost: float
    actual_unit_cost: float
    revenue: float
    gross_profit: float
    roi: float
    actual_success_rate: float
    notes: Optional[str] = None
    created_at: datetime
