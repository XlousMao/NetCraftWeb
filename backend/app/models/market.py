"""市场观察（MarketObservation）—— 价格是市场事件，不是 Item 属性。

一个 Item 拥有无限条价格观察记录。每条观察表达「用 price_quantity 个 price_item
换取 quantity 个 item」，支持以物易物（奶块真实交易不一定是钻石计价）。

observation_type:
  SELL_OFFER       玩家出售挂单（某人以某价卖该物品）
  BUY_ORDER        玩家收购订单（某人以某价收该物品）
  NPC_PRICE        商人/NPC 定价
  MANUAL_ESTIMATE  手动估值（无真实交易时的主观估价）

单价（每个 item 值多少 price_item）= price_quantity / quantity。
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin

OBSERVATION_TYPES = ("SELL_OFFER", "BUY_ORDER", "NPC_PRICE", "MANUAL_ESTIMATE")


class MarketObservation(Base, TimestampMixin):
    __tablename__ = "market_observations"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), index=True)
    observation_type: Mapped[str] = mapped_column(String(32), index=True, nullable=False)

    # 目标物品数量
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=1)
    # 计价物品（如钻石），为空表示基础货币
    price_item_id: Mapped[Optional[int]] = mapped_column(ForeignKey("items.id"))
    price_quantity: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)

    seller_name: Mapped[Optional[str]] = mapped_column(String(128))
    location: Mapped[Optional[str]] = mapped_column(String(128))
    source: Mapped[Optional[str]] = mapped_column(String(64))
    observed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    note: Mapped[Optional[str]] = mapped_column(Text)

    item: Mapped["Item"] = relationship(foreign_keys=[item_id], back_populates="market_observations")
    price_item: Mapped["Item"] = relationship(foreign_keys=[price_item_id])

    @property
    def unit_price(self) -> Decimal:
        """每个 item 的单价（以 price_item 计价）。"""
        q = Decimal(self.quantity) if self.quantity else Decimal(1)
        if q == 0:
            return Decimal(0)
        return Decimal(self.price_quantity) / q
