"""货币体系 API：体系/面额/换算规则/法币观察/换算。"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.currency import CurrencySystem, FiatExchangeObservation
from app.services.currency import CurrencyService
from app.services.fiat import FiatService

router = APIRouter(prefix="/currency", tags=["currency"])


class ConvertRequest(BaseModel):
    amount: float
    from_item_id: int
    to_item_id: int


class FiatObservationCreate(BaseModel):
    currency_item_id: int
    quantity: float
    fiat_currency: str = "CNY"
    fiat_amount: float
    observed_at: Optional[datetime] = None
    source: Optional[str] = None
    notes: Optional[str] = None


@router.get("/systems", response_model=list)
def list_systems(db: Session = Depends(get_db)):
    rows = db.execute(select(CurrencySystem)).scalars().all()
    return [
        {
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "base_currency_item_id": s.base_currency_item_id,
            "is_active": s.is_active,
        }
        for s in rows
    ]


@router.get("/summary", response_model=dict)
def summary(db: Session = Depends(get_db)):
    """默认货币体系概览：面额 + 换算规则 + 基础货币 + 当前 RMB 汇率。"""
    svc = CurrencyService(db)
    system = svc.get_default_system()
    if system is None:
        return {"system": None, "base_currency": None, "denominations": [], "rules": [],
                "rmb_rate": None}
    from app.models.item import Item

    base_item = db.get(Item, system.base_currency_item_id)
    fiat = FiatService(db)
    return {
        "system": {
            "id": system.id,
            "name": system.name,
            "base_currency_item_id": system.base_currency_item_id,
        },
        "base_currency": base_item.name if base_item else None,
        "denominations": svc.denomination_items(system.id),
        "rules": svc.rules(system.id),
        "rmb_rate": float(fiat.base_currency_rate()) if fiat.base_currency_rate() else None,
    }


@router.post("/convert", response_model=dict)
def convert(payload: ConvertRequest, db: Session = Depends(get_db)):
    try:
        result = CurrencyService(db).convert(
            Decimal(str(payload.amount)), payload.from_item_id, payload.to_item_id
        )
        return {"amount": float(result)}
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@router.get("/fiat", response_model=list)
def list_fiat(db: Session = Depends(get_db)):
    rows = db.execute(
        select(FiatExchangeObservation).order_by(FiatExchangeObservation.observed_at.desc())
    ).scalars().all()
    from app.models.item import Item

    result = []
    for r in rows:
        item = db.get(Item, r.currency_item_id)
        result.append(
            {
                "id": r.id,
                "currency_item_id": r.currency_item_id,
                "currency_item_name": item.name if item else None,
                "quantity": float(r.quantity),
                "fiat_currency": r.fiat_currency,
                "fiat_amount": float(r.fiat_amount),
                "observed_at": r.observed_at.isoformat(),
                "source": r.source,
                "notes": r.notes,
            }
        )
    return result


@router.post("/fiat", response_model=dict, status_code=201)
def record_fiat(payload: FiatObservationCreate, db: Session = Depends(get_db)):
    obs = FiatExchangeObservation(
        currency_item_id=payload.currency_item_id,
        quantity=Decimal(str(payload.quantity)),
        fiat_currency=payload.fiat_currency,
        fiat_amount=Decimal(str(payload.fiat_amount)),
        observed_at=payload.observed_at or datetime.now(timezone.utc),
        source=payload.source,
        notes=payload.notes,
    )
    db.add(obs)
    db.commit()
    db.refresh(obs)
    return {"id": obs.id, "status": "created"}
