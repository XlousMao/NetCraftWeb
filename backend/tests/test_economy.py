"""核心经济公式单元测试（Decimal）。"""

from decimal import Decimal

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
    assert calculate_loot_value([(Decimal(80), Decimal(30)), (Decimal(150), Decimal(4))]) == Decimal(3000)


def test_net_profit():
    gross = Decimal(9260)
    cost = calculate_total_cost(repair_cost=Decimal(1200), consumable_cost=Decimal(300))
    assert cost == Decimal(1500)
    assert calculate_net_profit(gross, cost) == Decimal(7760)


def test_profit_per_hour():
    # 7760 / 72 分钟(1.2h)
    r = calculate_profit_per_hour(Decimal(7760), Decimal(72))
    assert abs(r - Decimal(7760) / Decimal("1.2")) < Decimal("0.0001")


def test_repair_cost():
    # 精钢锭×3(80) + 钻石×2(150) = 240 + 300 = 540
    cost = calculate_repair_cost([(Decimal(80), Decimal(3)), (Decimal(150), Decimal(2))])
    assert cost == Decimal(540)


def test_success_rate():
    assert calculate_success_rate(87, 100) == Decimal("0.87")
    assert calculate_success_rate(0, 0) == Decimal(0)


def test_actual_unit_cost():
    r = calculate_actual_unit_cost(Decimal(7500), 87)
    assert abs(r - Decimal(7500) / Decimal(87)) < Decimal("0.0001")


def test_roi():
    # 毛利 34 / 成本 86.21
    r = calculate_roi(Decimal(34), Decimal("86.21"))
    assert abs(r - Decimal(34) / Decimal("86.21")) < Decimal("0.0001")


def test_gross_profit():
    assert calculate_gross_profit(Decimal(10440), Decimal(7500)) == Decimal(2940)
