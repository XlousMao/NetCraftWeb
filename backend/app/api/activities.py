"""活动 API：统一活动账本。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.activity import Activity, ActivityRecord
from app.schemas.activity import (
    ActivityOut,
    ActivityRecordCreate,
    ActivityRecordOut,
    ActivityRecordUpdate,
)
from app.services.activity import ActivityService

router = APIRouter(prefix="/activities", tags=["activities"])


@router.get("", response_model=list)
def list_activities(db: Session = Depends(get_db)):
    rows = db.execute(select(Activity).order_by(Activity.id)).scalars().all()
    return [ActivityOut.model_validate(a).model_dump() for a in rows]


@router.get("/records", response_model=dict)
def list_records(
    activity_type: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    stmt = select(ActivityRecord)
    count_stmt = select(func.count()).select_from(ActivityRecord)
    if activity_type:
        stmt = stmt.where(ActivityRecord.activity_type == activity_type)
        count_stmt = count_stmt.where(ActivityRecord.activity_type == activity_type)
    total = db.execute(count_stmt).scalar_one()
    rows = (
        db.execute(
            stmt.order_by(ActivityRecord.started_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [ActivityRecordOut.model_validate(r).model_dump() for r in rows],
    }


@router.post("/records", response_model=ActivityRecordOut, status_code=201)
def create_record(payload: ActivityRecordCreate, db: Session = Depends(get_db)):
    record = ActivityService(db).create_manual(
        activity_type=payload.activity_type,
        label=payload.label,
        started_at=payload.started_at,
        ended_at=payload.ended_at,
        gross_value=payload.gross_value,
        total_cost=payload.total_cost,
        notes=payload.notes,
    )
    db.commit()
    db.refresh(record)
    return ActivityRecordOut.model_validate(record)


@router.put("/records/{record_id}", response_model=ActivityRecordOut)
def update_record(record_id: int, payload: ActivityRecordUpdate, db: Session = Depends(get_db)):
    record = db.get(ActivityRecord, record_id)
    if record is None:
        raise HTTPException(404, "活动记录不存在")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(record, k, v)
    # 重算净收益与每小时收益
    from app.analysis.economy_calculator import calculate_profit_per_hour

    record.net_profit = record.gross_value - record.total_cost
    duration = (
        (record.ended_at - record.started_at).total_seconds() / 60
        if record.ended_at and record.ended_at > record.started_at
        else 0
    )
    record.duration_minutes = duration
    record.profit_per_hour = calculate_profit_per_hour(record.net_profit, duration)
    db.commit()
    db.refresh(record)
    return ActivityRecordOut.model_validate(record)


@router.delete("/records/{record_id}", status_code=204)
def delete_record(record_id: int, db: Session = Depends(get_db)):
    record = db.get(ActivityRecord, record_id)
    if record is None:
        raise HTTPException(404, "活动记录不存在")
    db.delete(record)
    db.commit()
    return None
