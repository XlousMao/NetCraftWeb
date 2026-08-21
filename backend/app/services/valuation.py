"""估值引擎 —— 统一为任意物品在任意时点给出单价与来源，并换算钻石/RMB 双价值。

V3 关键：
  - 价格数据源改为 market_observations（市场事件），不再依赖 Item 属性字段。
  - observed_at 真实参与历史查询（取 observed_at <= target 的最近有效观察）。
  - 输出 Value 对象：unit_price + base_currency_value(钻石) + fiat_value(RMB)。
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.item import Item
from app.models.market import OBSERVATION_TYPES, MarketObservation
from app.services.currency import CurrencyService, q_money
from app.services.fiat import FiatService

# auto 估值优先级（第一个有值即用）：
# 手动估值最可信；商人定价(NPC)稳定；出售挂单(SELL_OFFER)作为市场价参考
AUTO_ORDER = ("MANUAL_ESTIMATE", "NPC_PRICE", "SELL_OFFER")

# 旧 policy 别名（兼容历史调用）
POLICY_ALIAS = {
    "vendor": "NPC_PRICE",
    "market": "SELL_OFFER",
    "manual": "MANUAL_ESTIMATE",
}


class ValuationResult:
    """统一估值结果。"""

    def __init__(
        self,
        item_id: int,
        quantity: Decimal,
        unit_price: Decimal,
        total: Decimal,
        currency_item_id: Optional[int],
        base_currency_value: Decimal,
        fiat_value: Optional[Decimal],
        source: str,
        observed_at: datetime,
    ):
        self.item_id = item_id
        self.quantity = quantity
        self.unit_price = unit_price
        self.total = total
        self.currency_item_id = currency_item_id
        self.base_currency_value = base_currency_value
        self.fiat_value = fiat_value
        self.source = source
        self.observed_at = observed_at

    def as_dict(self) -> dict:
        return {
            "item_id": self.item_id,
            "quantity": float(self.quantity),
            "unit_price": float(self.unit_price),
            "total": float(self.total),
            "currency_item_id": self.currency_item_id,
            "base_currency_value": float(self.base_currency_value),
            "fiat_value": float(self.fiat_value) if self.fiat_value is not None else None,
            "source": self.source,
            "observed_at": self.observed_at.isoformat(),
        }


class ValuationService:
    """估值服务。"""

    def __init__(self, db: Session):
        self.db = db
        self.currency = CurrencyService(db)
        self.fiat = FiatService(db)

    def _base_currency_id(self) -> Optional[int]:
        return self.currency.get_base_currency_item_id()

    def _resolve_policy(self, policy: str) -> str:
        return POLICY_ALIAS.get(policy, policy)

    def _observation_at(
        self, item_id: int, obs_type: str, observed_at: datetime
    ) -> Optional[MarketObservation]:
        return self.db.execute(
            select(MarketObservation)
            .where(
                MarketObservation.item_id == item_id,
                MarketObservation.observation_type == obs_type,
                MarketObservation.observed_at <= observed_at,
            )
            .order_by(MarketObservation.observed_at.desc())
            .limit(1)
        ).scalar_one_or_none()

    def _unit_price_to_base(self, obs: MarketObservation) -> Decimal:
        """观察的单价以 price_item 计价，换算为基础货币（钻石）。"""
        unit = obs.unit_price
        base = self._base_currency_id()
        if obs.price_item_id is None or obs.price_item_id == base:
            return q_money(unit)
        factor = self.currency.to_base_factor(obs.price_item_id)
        return q_money(unit * factor) if factor is not None else q_money(unit)

    def get_unit_price(
        self,
        item_id: int,
        policy: str = "auto",
        observed_at: Optional[datetime] = None,
    ) -> tuple[Decimal, str]:
        """返回 (unit_price_in_diamond, source)。"""
        observed_at = observed_at or datetime.now(timezone.utc)
        resolved = self._resolve_policy(policy)
        policies = [resolved] if resolved in OBSERVATION_TYPES else list(AUTO_ORDER)
        for p in policies:
            obs = self._observation_at(item_id, p, observed_at)
            if obs is not None:
                return self._unit_price_to_base(obs), f"{p}:observation"
        return Decimal(0), "none"

    def value(
        self,
        item_id: int,
        quantity: Decimal = Decimal(1),
        policy: str = "auto",
        observed_at: Optional[datetime] = None,
    ) -> ValuationResult:
        """估算某物品某数量的价值，返回钻石 + RMB 双价值。

        货币面额物品（钻石块/钻石结晶等）直接按换算系数估值，
        普通物品按市场观察估值。
        """
        observed_at = observed_at or datetime.now(timezone.utc)
        quantity = Decimal(quantity)
        base_id = self._base_currency_id()

        # 货币物品：按换算系数估值（钻石块=9 钻石、钻石结晶=99 钻石）
        factor = self.currency.to_base_factor(item_id)
        if factor is not None:
            base_value = q_money(quantity * factor)
            fiat = self.fiat.value(base_value, observed_at)
            return ValuationResult(
                item_id=item_id,
                quantity=quantity,
                unit_price=factor,
                total=base_value,
                currency_item_id=item_id,
                base_currency_value=base_value,
                fiat_value=fiat,
                source="currency",
                observed_at=observed_at,
            )

        unit_price, source = self.get_unit_price(item_id, policy, observed_at)
        total = q_money(unit_price * quantity)
        fiat = self.fiat.value(total, observed_at)

        return ValuationResult(
            item_id=item_id,
            quantity=quantity,
            unit_price=unit_price,
            total=total,
            currency_item_id=base_id,
            base_currency_value=total,
            fiat_value=fiat,
            source=source,
            observed_at=observed_at,
        )

    # ---- 市场观察记录 ----

    def record_observation(
        self,
        item_id: int,
        observation_type: str,
        price_quantity: Decimal,
        quantity: Decimal = Decimal(1),
        price_item_id: Optional[int] = None,
        seller_name: Optional[str] = None,
        location: Optional[str] = None,
        source: Optional[str] = None,
        observed_at: Optional[datetime] = None,
        note: Optional[str] = None,
    ) -> MarketObservation:
        """记录一条市场观察。price_item_id 为空表示基础货币（钻石）。"""
        item = self.db.get(Item, item_id)
        if item is None:
            raise ValueError(f"Item {item_id} 不存在")

        observed_at = observed_at or datetime.now(timezone.utc)
        obs = MarketObservation(
            item_id=item_id,
            observation_type=observation_type,
            quantity=Decimal(quantity),
            price_item_id=price_item_id or self._base_currency_id(),
            price_quantity=Decimal(price_quantity),
            seller_name=seller_name,
            location=location,
            source=source,
            observed_at=observed_at,
            note=note,
        )
        self.db.add(obs)
        self.db.flush()
        return obs

    def market_summary(self, item_id: int) -> dict:
        """某物品市场概览：价格区间、最高收购、最低出售、最近观察。"""
        rows = (
            self.db.execute(
                select(MarketObservation)
                .where(MarketObservation.item_id == item_id)
                .order_by(MarketObservation.observed_at.desc())
            )
            .scalars()
            .all()
        )
        base_id = self._base_currency_id()
        def to_diamond(obs):
            unit = obs.unit_price
            if obs.price_item_id is None or obs.price_item_id == base_id:
                return float(unit)
            f = self.currency.to_base_factor(obs.price_item_id)
            return float(unit * f) if f is not None else float(unit)

        units = [to_diamond(o) for o in rows]
        buys = [to_diamond(o) for o in rows if o.observation_type == "BUY_ORDER"]
        sells = [to_diamond(o) for o in rows if o.observation_type == "SELL_OFFER"]

        return {
            "count": len(rows),
            "latest": units[0] if units else None,
            "min": min(units) if units else None,
            "max": max(units) if units else None,
            "highest_buy_order": max(buys) if buys else None,
            "lowest_sell_offer": min(sells) if sells else None,
        }

    def price_history(self, item_id: int, observation_type: Optional[str] = None) -> list[dict]:
        """某物品价格历史（供图表）。"""
        stmt = (
            select(MarketObservation)
            .where(MarketObservation.item_id == item_id)
            .order_by(MarketObservation.observed_at.asc())
        )
        if observation_type:
            stmt = stmt.where(MarketObservation.observation_type == observation_type)
        rows = self.db.execute(stmt).scalars().all()
        base_id = self._base_currency_id()
        result = []
        for o in rows:
            unit = o.unit_price
            if o.price_item_id is not None and o.price_item_id != base_id:
                f = self.currency.to_base_factor(o.price_item_id)
                unit = unit * f if f is not None else unit
            result.append(
                {
                    "observation_type": o.observation_type,
                    "unit_price": float(unit),
                    "quantity": float(o.quantity),
                    "observed_at": o.observed_at.isoformat(),
                    "source": o.source,
                }
            )
        return result
