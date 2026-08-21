"""装备 Schema。"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class RepairRequirementCreate(BaseModel):
    item_id: int
    quantity: float = Field(..., gt=0)


class RepairRequirementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    equipment_id: int
    item_id: int
    item_name: Optional[str] = None
    quantity: float


class EquipmentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: Optional[str] = None
    icon_url: Optional[str] = None
    repair_requirements: List[RepairRequirementCreate] = Field(default_factory=list)


class EquipmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon_url: Optional[str] = None
    is_active: Optional[bool] = None


class EquipmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str] = None
    icon_url: Optional[str] = None
    is_active: bool
    created_at: datetime
    repair_requirements: List[RepairRequirementOut] = Field(default_factory=list)
