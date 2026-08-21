"""估值引擎 —— 统一为任意物品在任意时点给出单价与来源，并换算钻石/RMB 双价值。

V2 关键：
  - observed_at 真实参与历史价格查询（取 observed_at <= target 的最近有效价格）。
  - 输出 Value 对象：unit_price + currency + base_currency_value(钻石) + fiat_value(RMB)。
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.item import Item, ItemPriceHistory
from app.services.currency import CurrencyService, q_money
from app.services.fiat import FiatService

# 估值来源优先级（auto 策略下取第一个非空）
# manual（手动估值）最高；vendor（商人收购价）作为稳定保守的"实际可变现价值"
# 默认优先于 market（玩家市场价，可能波动/被操纵），与规格示例一致。
AUTO_POLICY_ORDER = ("manual", "vendor", "market")

POLICY_FIELD_MAP = {
    "vendor": "vendor_buy_price",
    "market": "market_price",
    "manual": "manual_price",
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

    def _history_price_at(
        self, item_id: int, price_type: str, observed_at: datetime
    ) -> Optional[ItemPriceHistory]:
        return self.db.execute(
            select(ItemPriceHistory)
            .where(
                ItemPriceHistory.item_id == item_id,
                ItemPriceHistory.price_type == price_type,
                ItemPriceHistory.observed_at <= observed_at,
            )
            .order_by(ItemPriceHistory.observed_at.desc())
            .limit(1)
        ).scalar_one_or_none()

    def get_unit_price(
        self,
        item_id: int,
        policy: str = "auto",
        observed_at: Optional[datetime] = None,
    ) -> tuple[Decimal, Optional[int], str]:
        """返回 (unit_price, currency_item_id, source)。

        显式策略：查历史价格（observed_at <= target），无则回退 Item 当前字段。
        auto：按 manual → vendor → market 顺序取第一个有值的来源。
        """
        item = self.db.get(Item, item_id)
        if item is None:
            return Decimal(0), None, "unknown"
        observed_at = observed_at or datetime.now(timezone.utc)
        base = self._base_currency_id()

        policies = [policy] if policy in POLICY_FIELD_MAP else list(AUTO_POLICY_ORDER)
        for p in policies:
            hist = self._history_price_at(item_id, p, observed_at)
            if hist is not None and hist.price is not None:
                currency_id = hist.currency_item_id or base
                return Decimal(hist.price), currency_id, f"{p}:history"
            current = getattr(item, POLICY_FIELD_MAP[p], None)
            if current is not None and Decimal(current) > 0:
                return Decimal(current), base, p

        return Decimal(0), base, "none"

    def value(
        self,
        item_id: int,
        quantity: Decimal = Decimal(1),
        policy: str = "auto",
        observed_at: Optional[datetime] = None,
    ) -> ValuationResult:
        """估算某物品某数量的价值，返回钻石 + RMB 双价值。

        货币面额物品（钻石块/钻石结晶等）直接按换算系数估值，
        普通物品按价格估值。
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

        unit_price, currency_item_id, source = self.get_unit_price(
            item_id, policy, observed_at
        )
        total = q_money(unit_price * quantity)

        if currency_item_id is None or currency_item_id == base_id:
            base_value = total
        else:
            f = self.currency.to_base_factor(currency_item_id)
            base_value = q_money(total * f) if f is not None else total

        fiat = self.fiat.value(base_value, observed_at)

        return ValuationResult(
            item_id=item_id,
            quantity=quantity,
            unit_price=unit_price,
            total=total,
            currency_item_id=currency_item_id or base_id,
            base_currency_value=base_value,
            fiat_value=fiat,
            source=source,
            observed_at=observed_at,
        )

    def record_price(
        self,
        item_id: int,
        price_type: str,
        price: Decimal,
        source: Optional[str] = None,
        quantity: Optional[Decimal] = None,
        observed_at: Optional[datetime] = None,
        currency_item_id: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> ItemPriceHistory:
        """记录一条价格历史，并同步更新 item 当前价格字段。"""
        item = self.db.get(Item, item_id)
        if item is None:
            raise ValueError(f"Item {item_id} 不存在")

        observed_at = observed_at or datetime.now(timezone.utc)
        entry = ItemPriceHistory(
            item_id=item_id,
            price_type=price_type,
            price=Decimal(price),
            currency_item_id=currency_item_id,
            quantity=Decimal(quantity) if quantity is not None else None,
            source=source,
            observed_at=observed_at,
            notes=notes,
        )
        self.db.add(entry)
        self.db.flush()

        # 同步当前价格字段为「该类型最新观察价格」（历史记录不覆盖当前价）
        if price_type in POLICY_FIELD_MAP:
            latest = self.db.execute(
                select(ItemPriceHistory)
                .where(
                    ItemPriceHistory.item_id == item_id,
                    ItemPriceHistory.price_type == price_type,
                )
                .order_by(ItemPriceHistory.observed_at.desc())
                .limit(1)
            ).scalar_one_or_none()
            if latest is not None:
                setattr(item, POLICY_FIELD_MAP[price_type], Decimal(latest.price))

        return entry

    def price_stats(self, item_id: int, price_type: str) -> dict:
        """某物品某类价格的历史统计。"""
        rows = (
            self.db.execute(
                select(ItemPriceHistory).where(
                    ItemPriceHistory.item_id == item_id,
                    ItemPriceHistory.price_type == price_type,
                )
            )
            .scalars()
            .all()
        )
        prices = [Decimal(r.price) for r in rows]
        if not prices:
            return {"price_type": price_type, "latest": None, "avg": None,
                    "min": None, "max": None, "count": 0}
        return {
            "price_type": price_type,
            "latest": float(prices[-1]),
            "avg": float(sum(prices) / len(prices)),
            "min": float(min(prices)),
            "max": float(max(prices)),
            "count": len(prices),
        }
