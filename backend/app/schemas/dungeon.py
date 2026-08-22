"""副本相关 Schema。

V3：掉落/消耗/维修只记录事实（item_id + quantity），利润字段由后端动态计算返回。
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class DungeonBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: Optional[str] = None
    icon_url: Optional[str] = None
    is_active: bool = True


class DungeonCreate(DungeonBase):
    pass


class DungeonUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon_url: Optional[str] = None
    is_active: Optional[bool] = None


class DungeonOut(DungeonBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class LootCreate(BaseModel):
    item_id: int
    quantity: float = Field(..., gt=0)


class ConsumptionCreate(BaseModel):
    item_id: int
    quantity: float = Field(..., gt=0)


class RepairLineCreate(BaseModel):
    """一次维修记录：按装备模板自动展开，或手动指定 item + quantity。"""

    equipment_id: Optional[int] = None
    item_id: Optional[int] = None
    quantity: Optional[float] = None


class DungeonRunCreate(BaseModel):
    dungeon_id: int
    started_at: datetime
    ended_at: Optional[datetime] = None
    travel_minutes: float = 0.0
    combat_minutes: float = 0.0
    death_count: int = 0
    notes: Optional[str] = None
    loots: List[LootCreate] = Field(default_factory=list)
    consumptions: List[ConsumptionCreate] = Field(default_factory=list)
    repairs: List[RepairLineCreate] = Field(default_factory=list)


class LootOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dungeon_run_id: int
    item_id: int
    item_name: Optional[str] = None
    icon_url: Optional[str] = None
    quantity: float
    base_currency_value: float = 0.0
    valuation_source: Optional[str] = None


class ConsumptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dungeon_run_id: int
    item_id: int
    item_name: Optional[str] = None
    icon_url: Optional[str] = None
    quantity: float
    base_currency_value: float = 0.0
    valuation_source: Optional[str] = None


class RepairOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dungeon_run_id: int
    equipment_id: Optional[int] = None
    item_id: int
    item_name: Optional[str] = None
    quantity: float
    base_currency_value: float = 0.0
    valuation_source: Optional[str] = None


class DungeonRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dungeon_id: int
    dungeon_name: Optional[str] = None
    started_at: datetime
    ended_at: Optional[datetime] = None
    travel_minutes: float
    combat_minutes: float
    death_count: int
    notes: Optional[str] = None
    total_duration_minutes: float
    # 以下为动态计算（非落库字段）
    gross_value: float = 0.0
    repair_cost: float = 0.0
    consumable_cost: float = 0.0
    total_cost: float = 0.0
    net_profit: float = 0.0
    profit_per_hour: float = 0.0
    gross_value_fiat: Optional[float] = None
    net_profit_fiat: Optional[float] = None
    profit_per_hour_fiat: Optional[float] = None
    created_at: datetime
    loots: List[LootOut] = Field(default_factory=list)
    consumptions: List[ConsumptionOut] = Field(default_factory=list)
    repairs: List[RepairOut] = Field(default_factory=list)
