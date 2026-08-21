"""经济计算器 —— 所有核心经济公式集中于此，使用 Decimal 计算。

以后修改游戏经济规则时，只需改这里，不四处散落魔法数字。
所有函数为纯函数，便于单元测试。
"""

from __future__ import annotations

from decimal import Decimal
from typing import Iterable, Optional

from app.services.currency import q_money, q_rate


def _D(x) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


def calculate_total(unit_price, quantity) -> Decimal:
    """总值 = 单价 × 数量。"""
    return q_money(_D(unit_price) * _D(quantity))


def calculate_loot_value(items: Iterable[tuple[Decimal, Decimal]]) -> Decimal:
    """掉落价值 = Σ(单价 × 数量)。入参为 (unit_price, quantity) 列表。"""
    total = sum((_D(p) * _D(q) for p, q in items), Decimal(0))
    return q_money(total)


def calculate_consumable_cost(items: Iterable[tuple[Decimal, Decimal]]) -> Decimal:
    """消耗品成本 = Σ(单价 × 数量)。"""
    total = sum((_D(p) * _D(q) for p, q in items), Decimal(0))
    return q_money(total)


def calculate_repair_cost(
    material_costs: Iterable[tuple[Decimal, Decimal]],
) -> Decimal:
    """维修成本 = Σ(单价 × 数量)。V2：维修由任意 Item 组成，不再有 currency_cost。"""
    total = sum((_D(p) * _D(q) for p, q in material_costs), Decimal(0))
    return q_money(total)


def calculate_total_cost(
    repair_cost: Decimal = Decimal(0),
    consumable_cost: Decimal = Decimal(0),
    other_cost: Decimal = Decimal(0),
) -> Decimal:
    """总成本 = 维修 + 消耗 + 其他。"""
    return q_money(_D(repair_cost) + _D(consumable_cost) + _D(other_cost))


def calculate_net_profit(gross_value: Decimal, total_cost: Decimal) -> Decimal:
    """净利润 = 总价值 - 总成本。"""
    return q_money(_D(gross_value) - _D(total_cost))


def calculate_profit_per_hour(net_profit: Decimal, duration_minutes) -> Decimal:
    """每小时收益 = 净利润 / 有效时间(小时)。"""
    minutes = _D(duration_minutes)
    if minutes <= 0:
        return Decimal(0)
    return q_money(_D(net_profit) / (minutes / Decimal(60)))


def calculate_total_duration(
    travel_minutes, combat_minutes, other_minutes=Decimal(0)
) -> Decimal:
    """总时长 = 赶路 + 战斗 + 其他。"""
    return q_money(_D(travel_minutes) + _D(combat_minutes) + _D(other_minutes))


def calculate_recipe_material_cost(
    materials: Iterable[tuple[Decimal, Decimal]], attempts=Decimal(1)
) -> Decimal:
    """配方材料成本（理论，单次）= Σ(材料单价 × 数量) × 尝试次数。"""
    per_unit = sum((_D(p) * _D(q) for p, q in materials), Decimal(0))
    return q_money(per_unit * _D(attempts))


def calculate_success_rate(success_count: int, attempted_count: int) -> Decimal:
    """实际成功率 = 成功次数 / 尝试次数。"""
    if attempted_count <= 0:
        return Decimal(0)
    return q_rate(Decimal(success_count) / Decimal(attempted_count))


def calculate_actual_unit_cost(total_material_cost: Decimal, success_count: int) -> Decimal:
    """实际单位成本 = 实际投入总成本 / 实际成功产出数量。"""
    if success_count <= 0:
        return Decimal(0)
    return q_money(_D(total_material_cost) / Decimal(success_count))


def calculate_gross_profit(revenue: Decimal, material_cost: Decimal) -> Decimal:
    """毛利 = 收入 - 材料成本。"""
    return q_money(_D(revenue) - _D(material_cost))


def calculate_roi(gross_profit: Decimal, material_cost: Decimal) -> Decimal:
    """ROI = 毛利 / 材料成本。成本为 0 时返回 0。"""
    cost = _D(material_cost)
    if cost <= 0:
        return Decimal(0)
    return q_rate(_D(gross_profit) / cost)


def calculate_failure_loss(
    expected_unit_cost: Decimal, actual_unit_cost: Decimal, success_count: int
) -> Decimal:
    """失败损耗 = (实际单位成本 - 理论单位成本) × 成功数量。"""
    if success_count <= 0:
        return Decimal(0)
    return q_money((_D(actual_unit_cost) - _D(expected_unit_cost)) * Decimal(success_count))
