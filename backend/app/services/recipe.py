"""炼金/生产服务：生产记录、成功率、实际成本、ROI 计算。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from app.analysis.economy_calculator import (
    calculate_actual_unit_cost,
    calculate_gross_profit,
    calculate_recipe_material_cost,
    calculate_roi,
    calculate_success_rate,
)
from app.models.recipe import ProductionRecord, Recipe
from app.schemas.recipe import ProductionRecordCreate
from app.services.activity import ActivityService
from app.services.valuation import ValuationService


class RecipeService:
    def __init__(self, db: Session):
        self.db = db
        self.valuation = ValuationService(db)
        self.activity = ActivityService(db)

    def _theoretical_unit_cost(self, recipe: Recipe) -> float:
        """理论单位成本 = Σ(材料单价 × 数量)。"""
        pairs = [
            (self.valuation.get_unit_price(m.item_id, "auto")[0], m.quantity)
            for m in recipe.materials
        ]
        return calculate_recipe_material_cost(pairs, attempts=1.0)

    def create_production_record(self, payload: ProductionRecordCreate) -> ProductionRecord:
        recipe = self.db.get(Recipe, payload.recipe_id)
        if recipe is None:
            raise ValueError(f"配方 {payload.recipe_id} 不存在")

        attempted = payload.attempted_count
        success = min(payload.success_count, attempted)
        fail = attempted - success

        # 材料总成本 = 理论单次成本 × 实际尝试次数
        theoretical_unit = self._theoretical_unit_cost(recipe)
        material_cost = round(theoretical_unit * attempted, 4)

        actual_success_rate = calculate_success_rate(success, attempted)
        actual_unit_cost = calculate_actual_unit_cost(material_cost, success)

        # 收入：优先用传入值，否则按产出物当前估值 × 成功数量
        if payload.revenue is not None:
            revenue = payload.revenue
        else:
            revenue = 0.0
            for out in recipe.outputs:
                unit_price, _ = self.valuation.get_unit_price(out.item_id, "auto")
                revenue += unit_price * out.quantity * success
            revenue = round(revenue, 4)

        gross_profit = calculate_gross_profit(revenue, material_cost)
        roi = calculate_roi(gross_profit, material_cost)

        record = ProductionRecord(
            recipe_id=recipe.id,
            started_at=payload.started_at,
            ended_at=payload.ended_at or datetime.now(timezone.utc),
            attempted_count=attempted,
            success_count=success,
            fail_count=fail,
            material_cost=material_cost,
            actual_unit_cost=actual_unit_cost,
            revenue=revenue,
            gross_profit=gross_profit,
            roi=roi,
            actual_success_rate=actual_success_rate,
            notes=payload.notes,
        )
        self.db.add(record)
        self.db.flush()

        self.activity.sync_production_record(record)
        return record

    def recipe_analysis(self, recipe_id: int) -> dict:
        """配方分析：理论成本/实际成本/失败损耗/ROI。"""
        recipe = self.db.get(Recipe, recipe_id)
        if recipe is None:
            raise ValueError(f"配方 {recipe_id} 不存在")

        theoretical_unit = self._theoretical_unit_cost(recipe)
        materials = [
            {
                "item_id": m.item_id,
                "item_name": m.item.name,
                "quantity": m.quantity,
                "unit_price": self.valuation.get_unit_price(m.item_id, "auto")[0],
            }
            for m in recipe.materials
        ]
        outputs = [
            {
                "item_id": o.item_id,
                "item_name": o.item.name,
                "quantity": o.quantity,
                "unit_price": self.valuation.get_unit_price(o.item_id, "auto")[0],
            }
            for o in recipe.outputs
        ]
        # 理论输出价值
        theoretical_output_value = round(
            sum(o["unit_price"] * o["quantity"] for o in outputs), 4
        )

        return {
            "recipe_id": recipe.id,
            "name": recipe.name,
            "expected_success_rate": recipe.expected_success_rate,
            "theoretical_unit_cost": theoretical_unit,
            "theoretical_output_value": theoretical_output_value,
            "materials": materials,
            "outputs": outputs,
        }
