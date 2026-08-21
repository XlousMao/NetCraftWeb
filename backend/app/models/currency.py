"""货币体系与法币（RMB）兑换观察。

三层价值体系：
  1. 物品数量（原始事实）
  2. 游戏内基础货币（统一归一化为 Base Currency，如「钻石」）
  3. RMB 法币（基于历史观察价格换算，非实际可兑现价格）

禁止把 1/9/11/99 等换算数字硬编码在业务代码中，必须由
CurrencySystem / CurrencyDenomination / CurrencyConversionRule 动态计算。
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampMixin


class CurrencySystem(Base, TimestampMixin):
    """货币体系定义，如「奶块钻石经济体系」。"""

    __tablename__ = "currency_systems"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    # 基础货币对应的 Item（如「钻石」），所有经济分析最终归一化到它
    base_currency_item_id: Mapped[int] = mapped_column(ForeignKey("items.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class CurrencyDenomination(Base, TimestampMixin):
    """货币面额：一个 Item 作为货币面额时的基础价值（相对 base currency）。"""

    __tablename__ = "currency_denominations"

    id: Mapped[int] = mapped_column(primary_key=True)
    currency_system_id: Mapped[int] = mapped_column(
        ForeignKey("currency_systems.id"), index=True
    )
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), index=True)
    base_value: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    is_base: Mapped[bool] = mapped_column(Boolean, default=False)


class CurrencyConversionRule(Base, TimestampMixin):
    """货币换算规则：1 个 from_item = factor 个 to_item。

    例如：钻石块 → 钻石（×9）；钻石结晶 → 钻石块（×11）。
    系统通过图遍历自动推导「钻石结晶 = 11 × 9 = 99 钻石」。
    """

    __tablename__ = "currency_conversion_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    currency_system_id: Mapped[int] = mapped_column(
        ForeignKey("currency_systems.id"), index=True
    )
    from_item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), index=True)
    to_item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), index=True)
    factor: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)


class FiatExchangeObservation(Base, TimestampMixin):
    """法币（RMB）兑换观察：某时刻「quantity 个货币物品 = fiat_amount 法币」。

    例如：99 钻石块 = 27.10 RMB（2026-08-21）。
    RMB 价格也是历史数据，不允许只有一个当前值。
    """

    __tablename__ = "fiat_exchange_observations"

    id: Mapped[int] = mapped_column(primary_key=True)
    currency_item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    fiat_currency: Mapped[str] = mapped_column(String(8), default="CNY")
    fiat_amount: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    source: Mapped[Optional[str]] = mapped_column(String(64))
    notes: Mapped[Optional[str]] = mapped_column(Text)
