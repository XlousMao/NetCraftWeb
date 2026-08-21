"""估值引擎 —— 统一为任意物品在任意时点给出单价与来源。

支持多种估值策略（VendorPrice / MarketPrice / ManualPrice），
未来可扩展 AverageMarketPrice / WeightedAverage / CustomFormula。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.item import Item, ItemPriceHistory

# 估值来源优先级（auto 策略下取第一个非空）
AUTO_POLICY_ORDER = ("manual", "market", "vendor")

POLICY_FIELD_MAP = {
    "vendor": "vendor_buy_price",
    "market": "market_price",
    "manual": "manual_price",
}


class ValuationService:
    """估值服务：输入 item_id + 时间戳 + 策略，输出单价与来源。"""

    def __init__(self, db: Session):
        self.db = db

    def get_unit_price(
        self,
        item_id: int,
        policy: str = "auto",
        observed_at: Optional[datetime] = None,
    ) -> tuple[float, str]:
        """返回 (unit_price, source)。

        - 显式策略：直接读取 item 上对应价格字段。
        - auto：按 manual → market → vendor 顺序取第一个非空值。
        """
        item = self.db.get(Item, item_id)
        if item is None:
            return 0.0, "unknown"

        if policy in POLICY_FIELD_MAP:
            price = getattr(item, POLICY_FIELD_MAP[policy], None)
            return (price if price is not None else 0.0), policy

        # auto 策略
        for p in AUTO_POLICY_ORDER:
            price = getattr(item, POLICY_FIELD_MAP[p], None)
            if price is not None and price > 0:
                return price, p

        return 0.0, "none"

    def value(
        self,
        item_id: int,
        quantity: float = 1.0,
        policy: str = "auto",
        observed_at: Optional[datetime] = None,
    ) -> dict:
        """估算某物品某数量的总值，附带快照信息。"""
        unit_price, source = self.get_unit_price(item_id, policy, observed_at)
        ts = observed_at or datetime.now(timezone.utc)
        return {
            "item_id": item_id,
            "unit_price": unit_price,
            "total": round(unit_price * quantity, 4),
            "source": source,
            "currency": "gold",
            "observed_at": ts.isoformat(),
        }

    def record_price(
        self,
        item_id: int,
        price_type: str,
        price: float,
        source: Optional[str] = None,
        quantity: Optional[float] = None,
        observed_at: Optional[datetime] = None,
    ) -> ItemPriceHistory:
        """记录一条价格历史，并同步更新 item 当前价格字段。"""
        item = self.db.get(Item, item_id)
        if item is None:
            raise ValueError(f"Item {item_id} 不存在")

        observed_at = observed_at or datetime.now(timezone.utc)
        entry = ItemPriceHistory(
            item_id=item_id,
            price_type=price_type,
            price=price,
            quantity=quantity,
            source=source,
            observed_at=observed_at,
        )
        self.db.add(entry)

        # 同步当前价格字段
        if price_type in POLICY_FIELD_MAP:
            setattr(item, POLICY_FIELD_MAP[price_type], price)

        self.db.flush()
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
        prices = [r.price for r in rows]
        if not prices:
            return {"price_type": price_type, "latest": None, "avg": None,
                    "min": None, "max": None, "count": 0}
        return {
            "price_type": price_type,
            "latest": prices[-1],
            "avg": round(sum(prices) / len(prices), 4),
            "min": min(prices),
            "max": max(prices),
            "count": len(prices),
        }
