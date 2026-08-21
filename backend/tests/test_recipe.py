"""炼金/生产成本与 ROI 集成测试。"""

from datetime import datetime, timedelta, timezone

from app.models.recipe import Recipe, RecipeMaterial, RecipeOutput
from app.schemas.recipe import ProductionRecordCreate
from app.services.recipe import RecipeService


def _setup_recipe(db, make_item):
    red = make_item("红草", vendor_buy_price=25)
    crystal = make_item("魔晶", vendor_buy_price=120)
    bottle = make_item("空瓶", vendor_buy_price=5)
    potion = make_item("高级生命药水", vendor_buy_price=120)

    recipe = Recipe(name="高级生命药水", expected_success_rate=0.9)
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

    # 理论单次成本 = 3*25 + 2*120 + 1*5 = 75 + 240 + 5 = 320
    payload = ProductionRecordCreate(
        recipe_id=recipe.id,
        started_at=datetime.now(timezone.utc) - timedelta(hours=1),
        attempted_count=100,
        success_count=87,
    )
    record = RecipeService(db).create_production_record(payload)

    # 材料总成本 = 320 * 100 = 32000
    assert record.material_cost == 32000.0
    # 成功率 87%
    assert record.actual_success_rate == 0.87
    # 实际单位成本 = 32000 / 87
    assert round(record.actual_unit_cost, 2) == round(32000 / 87, 2)
    # 收入 = 成功 87 * 产出1 * 单价120 = 10440
    assert record.revenue == 10440.0
    # 毛利 = 10440 - 32000 = -21560 (亏损)
    assert record.gross_profit == -21560.0
    # ROI = -21560 / 32000
    assert record.roi == round(-21560 / 32000, 4)
