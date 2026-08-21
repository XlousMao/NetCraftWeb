"""炼金/生产成本与 ROI 集成测试（Decimal）。"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.models.recipe import Recipe, RecipeMaterial, RecipeOutput
from app.schemas.recipe import ProductionRecordCreate
from app.services.recipe import RecipeService


def _setup_recipe(db, make_item):
    red = make_item("红草", vendor_buy_price=25)
    crystal = make_item("魔晶", vendor_buy_price=120)
    bottle = make_item("空瓶", vendor_buy_price=5)
    potion = make_item("高级生命药水", vendor_buy_price=120)

    recipe = Recipe(name="高级生命药水", expected_success_rate=Decimal("0.9"))
    db.add(recipe)
    db.flush()
    db.add(RecipeMaterial(recipe_id=recipe.id, item_id=red.id, quantity=3))
    db.add(RecipeMaterial(recipe_id=recipe.id, item_id=crystal.id, quantity=2))
    db.add(RecipeMaterial(recipe_id=recipe.id, item_id=bottle.id, quantity=1))
    db.add(RecipeOutput(recipe_id=recipe.id, item_id=potion.id, quantity=1))
    db.flush()
    return recipe, potion


def test_production_record_cost_and_roi(db, make_item):
    recipe, potion = _setup_recipe(db, make_item)

    # 理论单次成本 = 3*25 + 2*120 + 1*5 = 320
    payload = ProductionRecordCreate(
        recipe_id=recipe.id,
        started_at=datetime.now(timezone.utc) - timedelta(hours=1),
        attempted_count=100,
        success_count=87,
    )
    record = RecipeService(db).create_production_record(payload)

    # 材料总成本 = 320 * 100 = 32000
    assert record.material_cost == Decimal(32000)
    # 成功率 87%
    assert record.actual_success_rate == Decimal("0.87")
    # 实际单位成本 = 32000 / 87
    assert abs(record.actual_unit_cost - Decimal(32000) / Decimal(87)) < Decimal("0.0001")
    # 收入 = 成功 87 * 产出1 * 单价120 = 10440
    assert record.revenue == Decimal(10440)
    # 毛利 = 10440 - 32000 = -21560
    assert record.gross_profit == Decimal(-21560)
    # ROI = -21560 / 32000
    assert abs(record.roi - Decimal(-21560) / Decimal(32000)) < Decimal("0.0001")
