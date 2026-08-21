"""副本服务：创建副本记录并在事务内完成掉落/消耗/维修的估值与收益计算。

关键原则：所有实际发生的交易、掉落、消耗、生产成本都保存估值快照，
历史记录不被当前价格污染。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from app.analysis.economy_calculator import (
    calculate_net_profit,
    calculate_profit_per_hour,
    calculate_total_cost,
    calculate_total_duration,
)
from app.models.dungeon import (
    Dungeon,
    DungeonConsumption,
    DungeonLoot,
    DungeonRepair,
    DungeonRun,
)
from app.models.equipment import Equipment
from app.schemas.dungeon import (
    ConsumptionCreate,
    DungeonRunCreate,
    LootCreate,
    RepairLineCreate,
)
from app.services.activity import ActivityService
from app.services.valuation import ValuationService


class DungeonService:
    def __init__(self, db: Session):
        self.db = db
        self.valuation = ValuationService(db)
        self.activity = ActivityService(db)

    def create_run(self, payload: DungeonRunCreate) -> DungeonRun:
        """创建副本记录（事务由调用方保证）。"""
        now = datetime.now(timezone.utc)

        run = DungeonRun(
            dungeon_id=payload.dungeon_id,
            started_at=payload.started_at,
            ended_at=payload.ended_at,
            travel_minutes=payload.travel_minutes,
            combat_minutes=payload.combat_minutes,
            death_count=payload.death_count,
            notes=payload.notes,
        )
        self.db.add(run)
        self.db.flush()  # 取得 run.id

        # 1. 掉落估值
        gross_value = 0.0
        for loot in payload.loots:
            unit_price, source = self.valuation.get_unit_price(
                loot.item_id, loot.policy, run.started_at
            )
            total = round(unit_price * loot.quantity, 4)
            gross_value += total
            self.db.add(
                DungeonLoot(
                    dungeon_run_id=run.id,
                    item_id=loot.item_id,
                    quantity=loot.quantity,
                    valuation_unit_price=unit_price,
                    valuation_total=total,
                    valuation_source=source,
                    valuation_time=run.started_at,
                )
            )

        # 2. 消耗品估值
        consumable_cost = 0.0
        for cons in payload.consumptions:
            unit_price, source = self.valuation.get_unit_price(
                cons.item_id, cons.policy, run.started_at
            )
            total = round(unit_price * cons.quantity, 4)
            consumable_cost += total
            self.db.add(
                DungeonConsumption(
                    dungeon_run_id=run.id,
                    item_id=cons.item_id,
                    quantity=cons.quantity,
                    valuation_unit_price=unit_price,
                    valuation_total=total,
                    valuation_source=source,
                    valuation_time=run.started_at,
                )
            )

        # 3. 维修估值
        repair_cost = 0.0
        for repair in payload.repairs:
            repair_cost += self._apply_repair(run, repair)

        run.gross_value = round(gross_value, 4)
        run.repair_cost = round(repair_cost, 4)
        run.consumable_cost = round(consumable_cost, 4)
        run.other_cost = round(payload.other_cost, 4)
        run.total_cost = calculate_total_cost(
            run.repair_cost, run.consumable_cost, run.other_cost
        )
        run.net_profit = calculate_net_profit(run.gross_value, run.total_cost)
        run.total_duration_minutes = calculate_total_duration(
            run.travel_minutes, run.combat_minutes
        )
        run.profit_per_hour = calculate_profit_per_hour(
            run.net_profit, run.total_duration_minutes
        )
        run.ended_at = run.ended_at or now

        self.db.flush()

        # 同步活动账本
        self.activity.sync_dungeon_run(run)

        return run

    def _apply_repair(self, run: DungeonRun, repair: RepairLineCreate) -> float:
        """处理一条维修：支持按装备模板自动展开，或手动指定材料。返回本次维修总成本。"""
        total_cost = repair.currency_cost

        if repair.equipment_id is not None:
            equipment = self.db.get(Equipment, repair.equipment_id)
            if equipment is None:
                raise ValueError(f"装备 {repair.equipment_id} 不存在")
            for req in equipment.repair_requirements:
                unit_price, source = self.valuation.get_unit_price(
                    req.item_id, repair.policy or "auto", run.started_at
                )
                material_cost = round(unit_price * req.quantity, 4)
                total_cost += material_cost
                self.db.add(
                    DungeonRepair(
                        dungeon_run_id=run.id,
                        equipment_id=equipment.id,
                        item_id=req.item_id,
                        quantity=req.quantity,
                        currency_cost=req.currency_cost,
                        material_cost=material_cost,
                        valuation_source=source,
                    )
                )
            # 装备模板自带的 currency_cost 也要计入
            template_currency = sum(
                r.currency_cost for r in equipment.repair_requirements
            )
            total_cost += template_currency
        elif repair.item_id is not None:
            unit_price, source = self.valuation.get_unit_price(
                repair.item_id, repair.policy or "auto", run.started_at
            )
            material_cost = round(unit_price * (repair.quantity or 0), 4)
            total_cost += material_cost
            self.db.add(
                DungeonRepair(
                    dungeon_run_id=run.id,
                    item_id=repair.item_id,
                    quantity=repair.quantity or 0,
                    currency_cost=repair.currency_cost,
                    material_cost=material_cost,
                    valuation_source=source,
                )
            )

        return round(total_cost, 4)

    def get_run(self, run_id: int) -> Optional[DungeonRun]:
        return self.db.get(DungeonRun, run_id)

    def list_runs(
        self, dungeon_id: Optional[int] = None, limit: int = 50, offset: int = 0
    ) -> tuple[List[DungeonRun], int]:
        from sqlalchemy import func, select

        stmt = select(DungeonRun)
        count_stmt = select(func.count()).select_from(DungeonRun)
        if dungeon_id is not None:
            stmt = stmt.where(DungeonRun.dungeon_id == dungeon_id)
            count_stmt = count_stmt.where(DungeonRun.dungeon_id == dungeon_id)
        total = self.db.execute(count_stmt).scalar_one()
        rows = (
            self.db.execute(
                stmt.order_by(DungeonRun.started_at.desc())
                .offset(offset)
                .limit(limit)
            )
            .scalars()
            .all()
        )
        return rows, total
