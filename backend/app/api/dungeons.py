"""副本 API：Dungeon CRUD + Dungeon Run（掉落/消耗/维修 + 自动收益计算）。"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.dungeon import Dungeon, DungeonRun
from app.schemas.dungeon import (
    DungeonCreate,
    DungeonOut,
    DungeonRunCreate,
    DungeonRunOut,
    DungeonUpdate,
)
from app.services.dungeon import DungeonService

router = APIRouter(tags=["dungeons"])

dungeon_router = APIRouter(prefix="/dungeons", tags=["dungeons"])
run_router = APIRouter(prefix="/dungeon-runs", tags=["dungeon-runs"])


@dungeon_router.get("", response_model=dict)
def list_dungeons(db: Session = Depends(get_db)):
    rows = db.execute(select(Dungeon).order_by(Dungeon.name)).scalars().all()
    return {"total": len(rows), "items": [DungeonOut.model_validate(d).model_dump() for d in rows]}


@dungeon_router.post("", response_model=DungeonOut, status_code=201)
def create_dungeon(payload: DungeonCreate, db: Session = Depends(get_db)):
    existing = db.execute(select(Dungeon).where(Dungeon.name == payload.name)).scalar_one_or_none()
    if existing:
        raise HTTPException(409, "副本名称已存在")
    d = Dungeon(**payload.model_dump())
    db.add(d)
    db.commit()
    db.refresh(d)
    return DungeonOut.model_validate(d)


@dungeon_router.get("/{dungeon_id}", response_model=DungeonOut)
def get_dungeon(dungeon_id: int, db: Session = Depends(get_db)):
    d = db.get(Dungeon, dungeon_id)
    if d is None:
        raise HTTPException(404, "副本不存在")
    return DungeonOut.model_validate(d)


@dungeon_router.patch("/{dungeon_id}", response_model=DungeonOut)
def update_dungeon(dungeon_id: int, payload: DungeonUpdate, db: Session = Depends(get_db)):
    d = db.get(Dungeon, dungeon_id)
    if d is None:
        raise HTTPException(404, "副本不存在")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(d, k, v)
    db.commit()
    db.refresh(d)
    return DungeonOut.model_validate(d)


@dungeon_router.delete("/{dungeon_id}", status_code=204)
def delete_dungeon(dungeon_id: int, db: Session = Depends(get_db)):
    d = db.get(Dungeon, dungeon_id)
    if d is None:
        raise HTTPException(404, "副本不存在")
    d.is_active = False
    db.commit()
    return None


# ---- Dungeon Run ----

def _run_out(db: Session, run: DungeonRun) -> DungeonRunOut:
    from app.schemas.dungeon import ConsumptionOut, LootOut

    loots = []
    for l in run.loots:
        lo = LootOut.model_validate(l)
        lo.item_name = l.item.name if l.item else None
        loots.append(lo)
    consumptions = []
    for c in run.consumptions:
        co = ConsumptionOut.model_validate(c)
        co.item_name = c.item.name if c.item else None
        consumptions.append(co)
    out = DungeonRunOut.model_validate(run)
    out.dungeon_name = run.dungeon.name if run.dungeon else None
    out.loots = loots
    out.consumptions = consumptions
    return out


@run_router.post("", response_model=DungeonRunOut, status_code=201)
def create_run(payload: DungeonRunCreate, db: Session = Depends(get_db)):
    """创建副本记录：事务内完成掉落/消耗/维修估值与收益计算。"""
    d = db.get(Dungeon, payload.dungeon_id)
    if d is None:
        raise HTTPException(404, "副本不存在")
    try:
        run = DungeonService(db).create_run(payload)
        from app.services.relation import RelationService

        RelationService(db).sync_dungeon_run_drops(run)
        db.commit()
        db.refresh(run)
        return _run_out(db, run)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(400, str(exc))


@run_router.get("", response_model=dict)
def list_runs(
    dungeon_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    rows, total = DungeonService(db).list_runs(
        dungeon_id, limit=page_size, offset=(page - 1) * page_size
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_run_out(db, r).model_dump() for r in rows],
    }


@run_router.get("/{run_id}", response_model=DungeonRunOut)
def get_run(run_id: int, db: Session = Depends(get_db)):
    run = db.get(DungeonRun, run_id)
    if run is None:
        raise HTTPException(404, "副本记录不存在")
    return _run_out(db, run)


@run_router.delete("/{run_id}", status_code=204)
def delete_run(run_id: int, db: Session = Depends(get_db)):
    run = db.get(DungeonRun, run_id)
    if run is None:
        raise HTTPException(404, "副本记录不存在")
    db.delete(run)
    db.commit()
    return None
