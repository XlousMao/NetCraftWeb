"""分析 API：周期经济、排行、活动效率、估值、导入导出。"""

from __future__ import annotations

import csv
import io
import json
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.analysis import service as analysis
from app.models.dungeon import DungeonLoot, DungeonRun
from app.models.item import Item, ItemPriceHistory
from app.models.recipe import ProductionRecord
from app.schemas.common import ValuationRequest, ValuationResult
from app.services.valuation import ValuationService

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/period", response_model=dict)
def period(start: Optional[str] = Query(None), end: Optional[str] = Query(None), db: Session = Depends(get_db)):
    return analysis.analyze_period(db, start, end)


@router.get("/dungeon-rankings", response_model=list)
def dungeon_rankings(start: Optional[str] = Query(None), end: Optional[str] = Query(None), db: Session = Depends(get_db)):
    return analysis.dungeon_rankings(db, start, end)


@router.get("/recipe-rankings", response_model=list)
def recipe_rankings(db: Session = Depends(get_db)):
    return analysis.recipe_rankings(db)


@router.get("/activity-efficiency", response_model=dict)
def activity_efficiency(start: Optional[str] = Query(None), end: Optional[str] = Query(None), db: Session = Depends(get_db)):
    return analysis.activity_efficiency(db, start, end)


@router.post("/value", response_model=ValuationResult)
def value(payload: ValuationRequest, db: Session = Depends(get_db)):
    from datetime import datetime

    observed_at = datetime.fromisoformat(payload.observed_at) if payload.observed_at else None
    result = ValuationService(db).value(
        payload.item_id, payload.quantity, payload.policy, observed_at
    )
    return result.as_dict()


@router.post("/recompute-importance", response_model=dict)
def recompute_importance(db: Session = Depends(get_db)):
    count = analysis.recompute_all_importance(db)
    db.commit()
    return {"updated": count}


# ---- 导出 ----

def _rows_to_csv(headers: list[str], rows: list[list]) -> StreamingResponse:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    writer.writerows(rows)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=export.csv"},
    )


@router.get("/export/items")
def export_items(fmt: str = Query("csv"), db: Session = Depends(get_db)):
    items = db.execute(select(Item)).scalars().all()
    if fmt == "json":
        data = [
            {"id": i.id, "name": i.name, "category": i.category,
             "vendor_buy_price": i.vendor_buy_price, "market_price": i.market_price,
             "manual_price": i.manual_price, "importance_score": i.importance_score}
            for i in items
        ]
        return StreamingResponse(
            iter([json.dumps(data, ensure_ascii=False, indent=2)]),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=items.json"},
        )
    headers = ["id", "name", "category", "vendor_buy_price", "market_price", "manual_price", "importance_score"]
    rows = [[i.id, i.name, i.category, i.vendor_buy_price, i.market_price, i.manual_price, i.importance_score] for i in items]
    return _rows_to_csv(headers, rows)


@router.get("/export/dungeon-runs")
def export_runs(start: Optional[str] = Query(None), end: Optional[str] = Query(None), db: Session = Depends(get_db)):
    s, e = analysis.period_bounds(start, end)
    runs = db.execute(
        select(DungeonRun).where(DungeonRun.started_at >= s, DungeonRun.started_at <= e)
    ).scalars().all()
    headers = ["id", "dungeon", "started_at", "gross_value", "repair_cost", "consumable_cost", "net_profit", "profit_per_hour"]
    rows = [
        [r.id, r.dungeon.name if r.dungeon else "", r.started_at.isoformat(),
         r.gross_value, r.repair_cost, r.consumable_cost, r.net_profit, r.profit_per_hour]
        for r in runs
    ]
    return _rows_to_csv(headers, rows)
