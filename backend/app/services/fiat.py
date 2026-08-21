"""法币（RMB）估值服务。

基于 FiatExchangeObservation（历史观察价格）把基础货币价值换算为 RMB。
RMB 是现实世界计价单位，不属于游戏货币，不当作普通 Item 处理。
RMB 价格也是历史数据，按 observed_at 取最近有效观察。
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.currency import FiatExchangeObservation
from app.services.currency import CurrencyService, q_money


class FiatService:
    """法币估值服务。"""

    def __init__(self, db: Session):
        self.db = db
        self.currency = CurrencyService(db)

    def _nearest_observation(
        self, observed_at: datetime, fiat_currency: str = "CNY"
    ) -> Optional[FiatExchangeObservation]:
        return self.db.execute(
            select(FiatExchangeObservation)
            .where(
                FiatExchangeObservation.observed_at <= observed_at,
                FiatExchangeObservation.fiat_currency == fiat_currency,
            )
            .order_by(FiatExchangeObservation.observed_at.desc())
            .limit(1)
        ).scalar_one_or_none()

    def base_currency_rate(
        self, observed_at: Optional[datetime] = None, fiat_currency: str = "CNY"
    ) -> Optional[Decimal]:
        """返回「1 基础货币（钻石）= 多少法币（RMB）」的汇率，无观察则返回 None。"""
        observed_at = observed_at or datetime.now(timezone.utc)
        obs = self._nearest_observation(observed_at, fiat_currency)
        if obs is None:
            return None

        # 观察：quantity 个 currency_item = fiat_amount 法币
        # 法币 / 单位货币 = fiat_amount / quantity
        fiat_per_unit = Decimal(obs.fiat_amount) / Decimal(obs.quantity)
        # 换算到基础货币：法币 / 1 钻石 = 法币 / 单位货币 / factor(currency_item -> base)
        factor = self.currency.to_base_factor(obs.currency_item_id)
        if factor is None:
            return None
        return q_money(fiat_per_unit / factor)

    def value(
        self, base_currency_amount: Decimal, observed_at: Optional[datetime] = None
    ) -> Optional[Decimal]:
        """把基础货币（钻石）数量换算为 RMB。无汇率返回 None。"""
        if base_currency_amount is None:
            return None
        rate = self.base_currency_rate(observed_at)
        if rate is None:
            return None
        return q_money(Decimal(base_currency_amount) * rate)
