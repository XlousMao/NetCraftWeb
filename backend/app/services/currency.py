"""货币换算引擎。

通过 CurrencyConversionRule 构建的换算图，把任意货币面额换算为基础货币（如「钻石」）。
禁止把 1/9/11/99 等换算数字硬编码在业务代码中。
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.currency import (
    CurrencyConversionRule,
    CurrencyDenomination,
    CurrencySystem,
)
from app.models.item import Item

# 金额统一保留小数位
MONEY_PLACES = Decimal("0.00000001")
RATE_PLACES = Decimal("0.0001")


def q_money(x: Decimal) -> Decimal:
    """金额四舍五入到 8 位。"""
    return x.quantize(MONEY_PLACES, rounding=ROUND_HALF_UP)


def q_rate(x: Decimal) -> Decimal:
    """比率四舍五入到 4 位。"""
    return x.quantize(RATE_PLACES, rounding=ROUND_HALF_UP)


class CurrencyService:
    """货币换算服务。"""

    def __init__(self, db: Session):
        self.db = db

    def get_default_system(self) -> Optional[CurrencySystem]:
        return self.db.execute(
            select(CurrencySystem).where(CurrencySystem.is_active.is_(True))
        ).scalars().first()

    def get_base_currency_item_id(self, system_id: Optional[int] = None) -> Optional[int]:
        system = (
            self.db.get(CurrencySystem, system_id)
            if system_id
            else self.get_default_system()
        )
        if system is None:
            return None
        return system.base_currency_item_id

    def _rules_from(self, item_id: int, system_id: int) -> list[CurrencyConversionRule]:
        return self.db.execute(
            select(CurrencyConversionRule).where(
                CurrencyConversionRule.currency_system_id == system_id,
                CurrencyConversionRule.from_item_id == item_id,
            )
        ).scalars().all()

    def to_base_factor(self, currency_item_id: int, system_id: Optional[int] = None) -> Optional[Decimal]:
        """返回「1 个 currency_item 等于多少基础货币」的系数。

        若该物品本身不是货币（没有换算规则/面额定义），返回 None。
        """
        system = self.db.get(CurrencySystem, system_id) if system_id else self.get_default_system()
        if system is None:
            return None
        base = system.base_currency_item_id
        if currency_item_id == base:
            return Decimal(1)

        # 图遍历（BFS）寻找从 currency_item 到 base 的换算路径
        queue: list[tuple[int, Decimal]] = [(currency_item_id, Decimal(1))]
        visited: set[int] = set()
        while queue:
            item, factor = queue.pop(0)
            if item == base:
                return factor
            if item in visited:
                continue
            visited.add(item)
            for rule in self._rules_from(item, system.id):
                queue.append((rule.to_item_id, factor * rule.factor))

        # 回退：面额定义的 base_value
        denom = self.db.execute(
            select(CurrencyDenomination).where(
                CurrencyDenomination.currency_system_id == system.id,
                CurrencyDenomination.item_id == currency_item_id,
            )
        ).scalar_one_or_none()
        if denom is not None:
            return denom.base_value
        return None

    def to_base(
        self, currency_item_id: int, amount: Decimal, system_id: Optional[int] = None
    ) -> Decimal:
        """把某货币面额的数量换算为基础货币数量。"""
        if amount is None:
            return Decimal(0)
        amount = Decimal(amount)
        factor = self.to_base_factor(currency_item_id, system_id)
        if factor is None:
            # 非货币物品：视为基础货币（通常物品价格即以钻石计价）
            return q_money(amount)
        return q_money(amount * factor)

    def convert(
        self,
        amount: Decimal,
        from_item_id: int,
        to_item_id: int,
        system_id: Optional[int] = None,
    ) -> Decimal:
        """任意两个货币面额之间换算。"""
        amount = Decimal(amount)
        if from_item_id == to_item_id:
            return q_money(amount)
        from_factor = self.to_base_factor(from_item_id, system_id)
        to_factor = self.to_base_factor(to_item_id, system_id)
        if from_factor is None or to_factor is None:
            raise ValueError("货币换算失败：缺少换算规则")
        return q_money(amount * from_factor / to_factor)

    def denomination_items(self, system_id: Optional[int] = None) -> list[dict]:
        """列出货币体系的全部面额（用于配置页展示）。"""
        system = self.db.get(CurrencySystem, system_id) if system_id else self.get_default_system()
        if system is None:
            return []
        denoms = self.db.execute(
            select(CurrencyDenomination).where(
                CurrencyDenomination.currency_system_id == system.id
            )
        ).scalars().all()
        result = []
        for d in denoms:
            item = self.db.get(Item, d.item_id)
            result.append(
                {
                    "item_id": d.item_id,
                    "item_name": item.name if item else None,
                    "base_value": float(d.base_value),
                    "is_base": d.is_base,
                }
            )
        return result

    def rules(self, system_id: Optional[int] = None) -> list[dict]:
        system = self.db.get(CurrencySystem, system_id) if system_id else self.get_default_system()
        if system is None:
            return []
        rows = self.db.execute(
            select(CurrencyConversionRule).where(
                CurrencyConversionRule.currency_system_id == system.id
            )
        ).scalars().all()
        result = []
        for r in rows:
            f = self.db.get(Item, r.from_item_id)
            t = self.db.get(Item, r.to_item_id)
            result.append(
                {
                    "from_item_id": r.from_item_id,
                    "from_item_name": f.name if f else None,
                    "to_item_id": r.to_item_id,
                    "to_item_name": t.name if t else None,
                    "factor": float(r.factor),
                }
            )
        return result
