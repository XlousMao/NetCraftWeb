"""核心经济公式单元测试。"""

from app.analysis.economy_calculator import (
    calculate_actual_unit_cost,
    calculate_gross_profit,
    calculate_loot_value,
    calculate_net_profit,
    calculate_profit_per_hour,
    calculate_repair_cost,
    calculate_roi,
    calculate_success_rate,
    calculate_total_cost,
)


def test_loot_value():
    assert calculate_loot_value([(80, 30), (150, 4)]) == 3000.0  # 2400 + 600


def test_net_profit():
    gross = 9260
    cost = calculate_total_cost(repair_cost=1200, consumable_cost=300)
    assert cost == 1500
    assert calculate_net_profit(gross, cost) == 7760


def test_profit_per_hour():
    # 7760 金币 / 72 分钟(1.2h)
    assert calculate_profit_per_hour(7760, 72) == round(7760 / 1.2, 4)


def test_repair_cost():
    # 精钢锭×3(80) + 钻石×2(150) + 金币 100
    cost = calculate_repair_cost([(80, 3), (150, 2)], currency_cost=100)
    assert cost == 640  # 240 + 300 + 100


def test_success_rate():
    assert calculate_success_rate(87, 100) == 0.87
    assert calculate_success_rate(0, 0) == 0.0


def test_actual_unit_cost():
    # 7500 总成本 / 87 成功 = 86.2069...
    assert round(calculate_actual_unit_cost(7500, 87), 2) == 86.21


def test_roi():
    # 毛利 39.5%，即 34/86.21 约 0.3944
    assert round(calculate_roi(34, 86.21), 3) == 0.394


def test_gross_profit():
    assert calculate_gross_profit(10440, 7500) == 2940
