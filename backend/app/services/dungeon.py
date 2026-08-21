"""副本服务：创建/更新副本记录并在事务内完成掉落/消耗/维修的估值与收益计算。

V2 关键：
  - 所有掉落/消耗/维修保存估值快照（unit_price + currency + base_currency_value + fiat_value）。
  - 维修由任意 Item 组成（材料 + 钻石 + 钻石块…），统一走货币引擎换算。
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
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
from app.services.currency import q_money
from app.services.valuation import ValuationResult, ValuationService


class DungeonService:
    def __init__(self, db: Session):
        self.db = db
        self.valuation = ValuationService(db)
        self.activity = ActivityService(db)

    def create_run(self, payload: DungeonRunCreate) -> DungeonRun:
        """创建副本记录（事务由调用方保证）。"""
        run = DungeonRun(
            dungeon_id=payload.dungeon_id,
            started_at=payload.started_at,
            ended_at=payload.ended_at,
            travel_minutes=Decimal(payload.travel_minutes),
            combat_minutes=Decimal(payload.combat_minutes),
            death_count=payload.death_count,
            notes=payload.notes,
        )
        self.db.add(run)
        self.db.flush()  # 取得 run.id

        self._apply_details(run, payload)
        self.db.flush()
        self.activity.sync_dungeon_run(run)
        return run

    def update_run(self, run_id: int, payload: DungeonRunCreate) -> DungeonRun:
        """更新副本记录：删除旧明细，按新数据重新估值。"""
        run = self.db.get(DungeonRun, run_id)
        if run is None:
            raise ValueError(f"副本记录 {run_id} 不存在")

        # 更新基本字段
        run.dungeon_id = payload.dungeon_id
        run.started_at = payload.started_at
        run.ended_at = payload.ended_at
        run.travel_minutes = Decimal(payload.travel_minutes)
        run.combat_minutes = Decimal(payload.combat_minutes)
        run.death_count = payload.death_count
        run.notes = payload.notes

        # 删除旧明细
        for l in list(run.loots):
            self.db.delete(l)
        for c in list(run.consumptions):
            self.db.delete(c)
        for r in list(run.repairs):
            self.db.delete(r)
        self.db.flush()

        self._apply_details(run, payload)
        self.db.flush()
        self.activity.sync_dungeon_run(run)
        return run

    def _apply_details(self, run: DungeonRun, payload: DungeonRunCreate) -> None:
        """对 run 应用掉落/消耗/维修并计算收益快照（复用，供创建与更新调用）。"""
        now = datetime.now(timezone.utc)

        # 1. 掉落估值
        gross_value = Decimal(0)
        gross_fiat = Decimal(0)
        has_fiat = False
        for loot in payload.loots:
            v: ValuationResult = self.valuation.value(
                loot.item_id, Decimal(loot.quantity), loot.policy, run.started_at
            )
            gross_value += v.base_currency_value
            if v.fiat_value is not None:
                gross_fiat += v.fiat_value
                has_fiat = True
            self.db.add(
                DungeonLoot(
                    dungeon_run_id=run.id,
                    item_id=loot.item_id,
                    quantity=v.quantity,
                    valuation_unit_price=v.unit_price,
                    valuation_total=v.total,
                    valuation_source=v.source,
                    valuation_currency_item_id=v.currency_item_id,
                    base_currency_value=v.base_currency_value,
                    fiat_value=v.fiat_value,
                    valuation_time=run.started_at,
                )
            )

        # 2. 消耗品估值
        consumable_cost = Decimal(0)
        consumable_fiat = Decimal(0)
        for cons in payload.consumptions:
            v = self.valuation.value(
                cons.item_id, Decimal(cons.quantity), cons.policy, run.started_at
            )
            consumable_cost += v.base_currency_value
            if v.fiat_value is not None:
                consumable_fiat += v.fiat_value
                has_fiat = True
            self.db.add(
                DungeonConsumption(
                    dungeon_run_id=run.id,
                    item_id=cons.item_id,
                    quantity=v.quantity,
                    valuation_unit_price=v.unit_price,
                    valuation_total=v.total,
                    valuation_source=v.source,
                    valuation_currency_item_id=v.currency_item_id,
                    base_currency_value=v.base_currency_value,
                    fiat_value=v.fiat_value,
                    valuation_time=run.started_at,
                )
            )

        # 3. 维修估值（多物品，无 currency_cost）
        repair_cost = Decimal(0)
        repair_fiat = Decimal(0)
        for repair in payload.repairs:
            rc, rf, rf_has = self._apply_repair(run, repair)
            repair_cost += rc
            repair_fiat += rf
            has_fiat = has_fiat or rf_has

        run.gross_value = q_money(gross_value)
        run.repair_cost = q_money(repair_cost)
        run.consumable_cost = q_money(consumable_cost)
        run.other_cost = q_money(Decimal(payload.other_cost))
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

        # RMB 估值快照
        run.gross_value_fiat = None
        run.net_profit_fiat = None
        run.profit_per_hour_fiat = None
        if has_fiat:
            total_fiat = gross_fiat - (consumable_fiat + repair_fiat)
            run.gross_value_fiat = q_money(gross_fiat)
            run.net_profit_fiat = q_money(total_fiat)
            run.profit_per_hour_fiat = calculate_profit_per_hour(
                total_fiat, run.total_duration_minutes
            )

    def _apply_repair(
        self, run: DungeonRun, repair: RepairLineCreate
    ) -> tuple[Decimal, Decimal, bool]:
        """处理一条维修，返回 (base_currency_cost, fiat_cost, has_fiat)。

        支持按装备模板自动展开，或手动指定 item + quantity。
        维修消耗的任意 Item（材料/钻石/钻石块）都走统一估值。
        """
        items: list[tuple[int, Decimal]] = []

        if repair.equipment_id is not None:
            equipment = self.db.get(Equipment, repair.equipment_id)
            if equipment is None:
                raise ValueError(f"装备 {repair.equipment_id} 不存在")
            for req in equipment.repair_requirements:
                items.append((req.item_id, Decimal(req.quantity)))
        elif repair.item_id is not None:
            items.append((repair.item_id, Decimal(repair.quantity or 0)))

        total_cost = Decimal(0)
        total_fiat = Decimal(0)
        has_fiat = False
        for item_id, quantity in items:
            v = self.valuation.value(
                item_id, quantity, repair.policy or "auto", run.started_at
            )
            total_cost += v.base_currency_value
            if v.fiat_value is not None:
                total_fiat += v.fiat_value
                has_fiat = True
            self.db.add(
                DungeonRepair(
                    dungeon_run_id=run.id,
                    equipment_id=repair.equipment_id,
                    item_id=item_id,
                    quantity=quantity,
                    valuation_unit_price=v.unit_price,
                    material_cost=v.total,
                    valuation_source=v.source,
                    valuation_currency_item_id=v.currency_item_id,
                    base_currency_value=v.base_currency_value,
                    fiat_value=v.fiat_value,
                )
            )
        return q_money(total_cost), q_money(total_fiat), has_fiat

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
