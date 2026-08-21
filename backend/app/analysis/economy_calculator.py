"""经济计算器 —— 所有核心经济公式集中于此。

以后修改游戏经济规则时，只需改这里，不四处散落魔法数字。
所有函数为纯函数，便于单元测试。
"""

from __future__ import annotations

from typing import Iterable, Optional


def calculate_total(unit_price: float, quantity: float) -> float:
    """总值 = 单价 × 数量。"""
    return round(unit_price * quantity, 4)


def calculate_loot_value(items: Iterable[tuple[float, float]]) -> float:
    """掉落价值 = Σ(单价 × 数量)。入参为 (unit_price, quantity) 列表。"""
    return round(sum(unit_price * quantity for unit_price, quantity in items), 4)


def calculate_consumable_cost(items: Iterable[tuple[float, float]]) -> float:
    """消耗品成本 = Σ(单价 × 数量)。"""
    return round(sum(unit_price * quantity for unit_price, quantity in items), 4)


def calculate_repair_cost(
    material_costs: Iterable[tuple[float, float]], currency_cost: float = 0.0
) -> float:
    """维修成本 = 材料成本 + 金币维修费。"""
    material = sum(unit_price * quantity for unit_price, quantity in material_costs)
    return round(material + currency_cost, 4)


def calculate_total_cost(
    repair_cost: float = 0.0,
    consumable_cost: float = 0.0,
    other_cost: float = 0.0,
) -> float:
    """总成本 = 维修 + 消耗 + 其他。"""
    return round(repair_cost + consumable_cost + other_cost, 4)


def calculate_net_profit(gross_value: float, total_cost: float) -> float:
    """净利润 = 总价值 - 总成本。"""
    return round(gross_value - total_cost, 4)


def calculate_profit_per_hour(net_profit: float, duration_minutes: float) -> float:
    """每小时收益 = 净利润 / 有效时间(小时)。"""
    if duration_minutes <= 0:
        return 0.0
    return round(net_profit / (duration_minutes / 60.0), 4)


def calculate_total_duration(
    travel_minutes: float, combat_minutes: float, other_minutes: float = 0.0
) -> float:
    """总时长 = 赶路 + 战斗 + 其他。"""
    return round(travel_minutes + combat_minutes + other_minutes, 4)


def calculate_recipe_material_cost(
    materials: Iterable[tuple[float, float]], attempts: float = 1.0
) -> float:
    """配方材料成本（理论，单次）= Σ(材料单价 × 数量) × 尝试次数。"""
    per_unit = sum(unit_price * quantity for unit_price, quantity in materials)
    return round(per_unit * attempts, 4)


def calculate_success_rate(success_count: int, attempted_count: int) -> float:
    """实际成功率 = 成功次数 / 尝试次数。"""
    if attempted_count <= 0:
        return 0.0
    return round(success_count / attempted_count, 4)


def calculate_actual_unit_cost(total_material_cost: float, success_count: int) -> float:
    """实际单位成本 = 实际投入总成本 / 实际成功产出数量。"""
    if success_count <= 0:
        return 0.0
    return round(total_material_cost / success_count, 4)


def calculate_gross_profit(revenue: float, material_cost: float) -> float:
    """毛利 = 收入 - 材料成本。"""
    return round(revenue - material_cost, 4)


def calculate_roi(gross_profit: float, material_cost: float) -> float:
    """ROI = 毛利 / 材料成本。成本为 0 时返回 0。"""
    if material_cost <= 0:
        return 0.0
    return round(gross_profit / material_cost, 4)


def calculate_failure_loss(
    expected_unit_cost: float, actual_unit_cost: float, success_count: int
) -> float:
    """失败损耗 = (实际单位成本 - 理论单位成本) × 成功数量。"""
    if success_count <= 0:
        return 0.0
    return round((actual_unit_cost - expected_unit_cost) * success_count, 4)
