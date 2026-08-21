"""通用 Schema：分页、枚举、错误响应。"""

from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """统一分页响应。"""

    total: int
    items: List[T]
    page: int = 1
    page_size: int = 20


class ErrorResponse(BaseModel):
    detail: str


class MessageResponse(BaseModel):
    message: str = "ok"


class PeriodQuery(BaseModel):
    """周期查询参数。"""

    start: Optional[str] = None  # ISO 日期/时间
    end: Optional[str] = None


class ValuationRequest(BaseModel):
    item_id: int
    quantity: float = 1.0
    policy: str = "auto"  # auto | vendor | market | manual
    observed_at: Optional[str] = None


class ValuationResult(BaseModel):
    item_id: int
    unit_price: float
    total: float
    source: str
    currency: str = "gold"
    observed_at: str
