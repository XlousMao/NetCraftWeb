"""炼金/生产服务：生产记录、成功率、实际成本、ROI 计算（Decimal）。"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

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
from app.services.currency import q_money
from app.services.valuation import ValuationService


class RecipeService:
    def __init__(self, db: Session):
        self.db = db
        self.valuation = ValuationService(db)
        self.activity = ActivityService(db)

    def _theoretical_unit_cost(self, recipe: Recipe, observed_at: Optional[datetime] = None) -> Decimal:
        """理论单位成本 = Σ(材料单价 × 数量)，材料价值统一换算为钻石。"""
        total = Decimal(0)
        for m in recipe.materials:
            v = self.valuation.value(
                m.item_id, Decimal(m.quantity), "auto", observed_at
            )
            total += v.base_currency_value
        return q_money(total)

    def create_production_record(self, payload: ProductionRecordCreate) -> ProductionRecord:
        recipe = self.db.get(Recipe, payload.recipe_id)
        if recipe is None:
            raise ValueError(f"配方 {payload.recipe_id} 不存在")

        attempted = payload.attempted_count
        success = min(payload.success_count, attempted)
        fail = attempted - success

        # 材料总成本 = 理论单次成本（钻石）× 实际尝试次数
        theoretical_unit = self._theoretical_unit_cost(recipe, payload.started_at)
        material_cost = q_money(theoretical_unit * Decimal(attempted))

        actual_success_rate = calculate_success_rate(success, attempted)
        actual_unit_cost = calculate_actual_unit_cost(material_cost, success)

        # 收入：优先用传入值（钻石），否则按产出物当前估值 × 成功数量
        if payload.revenue is not None:
            revenue = q_money(Decimal(payload.revenue))
        else:
            revenue = Decimal(0)
            for out in recipe.outputs:
                v = self.valuation.value(
                    out.item_id, Decimal(out.quantity) * success, "auto", payload.started_at
                )
                revenue += v.base_currency_value
            revenue = q_money(revenue)

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
            fiat_value=self.valuation.fiat.value(gross_profit, payload.started_at),
            notes=payload.notes,
        )
        self.db.add(record)
        self.db.flush()

        self.activity.sync_production_record(record)
        return record

    def recipe_analysis(self, recipe_id: int) -> dict:
        """配方分析：理论成本/实际成本/失败损耗/ROI + 机会成本。"""
        recipe = self.db.get(Recipe, recipe_id)
        if recipe is None:
            raise ValueError(f"配方 {recipe_id} 不存在")

        theoretical_unit = self._theoretical_unit_cost(recipe)
        materials = []
        for m in recipe.materials:
            v = self.valuation.value(m.item_id, Decimal(m.quantity), "auto")
            materials.append(
                {
                    "item_id": m.item_id,
                    "item_name": m.item.name,
                    "quantity": float(m.quantity),
                    "unit_price": float(v.unit_price),
                    "base_currency_value": float(v.base_currency_value),
                    "market_value": self._market_value(m.item_id, Decimal(m.quantity)),
                }
            )
        outputs = []
        for o in recipe.outputs:
            v = self.valuation.value(o.item_id, Decimal(o.quantity), "auto")
            outputs.append(
                {
                    "item_id": o.item_id,
                    "item_name": o.item.name,
                    "quantity": float(o.quantity),
                    "unit_price": float(v.unit_price),
                    "base_currency_value": float(v.base_currency_value),
                }
            )
        theoretical_output_value = q_money(
            sum((Decimal(o["base_currency_value"]) for o in outputs), Decimal(0))
        )
        # 机会成本：材料若直接按市场价出售的价值
        market_opportunity = q_money(
            sum((Decimal(m["market_value"]) for m in materials), Decimal(0))
        )

        return {
            "recipe_id": recipe.id,
            "name": recipe.name,
            "expected_success_rate": float(recipe.expected_success_rate),
            "theoretical_unit_cost": float(theoretical_unit),
            "theoretical_output_value": float(theoretical_output_value),
            "market_opportunity_cost": float(market_opportunity),
            "materials": materials,
            "outputs": outputs,
        }

    def _market_value(self, item_id: int, quantity: Decimal) -> Decimal:
        """材料按市场价估值（机会成本）。"""
        v = self.valuation.value(item_id, quantity, "market")
        return v.base_currency_value
