"""活动 Schema。"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ActivityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    activity_type: str
    description: Optional[str] = None
    is_active: bool


class ActivityRecordCreate(BaseModel):
    activity_type: str = "OTHER"  # DUNGEON/ALCHEMY/GATHERING/CRAFTING/TRADING/OTHER
    label: str = Field(..., min_length=1)
    started_at: datetime
    ended_at: Optional[datetime] = None
    gross_value: float = 0.0
    total_cost: float = 0.0
    notes: Optional[str] = None


class ActivityRecordUpdate(BaseModel):
    activity_type: Optional[str] = None
    label: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    gross_value: Optional[float] = None
    total_cost: Optional[float] = None
    notes: Optional[str] = None


class ActivityRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    activity_type: str
    activity_id: Optional[int] = None
    label: str
    reference_type: Optional[str] = None
    reference_id: Optional[int] = None
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_minutes: float
    gross_value: float
    total_cost: float
    net_profit: float
    profit_per_hour: float
    notes: Optional[str] = None
    created_at: datetime
