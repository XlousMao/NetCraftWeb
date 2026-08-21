"""装备 API：Equipment CRUD + 维修需求模板。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.equipment import Equipment, EquipmentRepairRequirement
from app.schemas.equipment import (
    EquipmentCreate,
    EquipmentOut,
    EquipmentUpdate,
    RepairRequirementOut,
)

router = APIRouter(prefix="/equipments", tags=["equipments"])


def _equipment_out(db: Session, eq: Equipment) -> EquipmentOut:
    out = EquipmentOut.model_validate(eq)
    reqs = []
    for r in eq.repair_requirements:
        ro = RepairRequirementOut.model_validate(r)
        ro.item_name = r.item.name if r.item else None
        ro.icon_url = r.item.icon_url if r.item else None
        reqs.append(ro)
    out.repair_requirements = reqs
    return out


@router.get("", response_model=dict)
def list_equipments(db: Session = Depends(get_db)):
    rows = db.execute(select(Equipment).order_by(Equipment.name)).scalars().all()
    return {"total": len(rows), "items": [_equipment_out(db, e).model_dump() for e in rows]}


@router.post("", response_model=EquipmentOut, status_code=201)
def create_equipment(payload: EquipmentCreate, db: Session = Depends(get_db)):
    existing = db.execute(select(Equipment).where(Equipment.name == payload.name)).scalar_one_or_none()
    if existing:
        raise HTTPException(409, "装备名称已存在")
    eq = Equipment(
        name=payload.name,
        description=payload.description,
        icon_url=payload.icon_url,
    )
    db.add(eq)
    db.flush()
    for req in payload.repair_requirements:
        db.add(
            EquipmentRepairRequirement(
                equipment_id=eq.id,
                item_id=req.item_id,
                quantity=req.quantity,
            )
        )
    db.flush()
    from app.services.relation import RelationService

    RelationService(db).sync_equipment(eq)
    db.commit()
    db.refresh(eq)
    return _equipment_out(db, eq)


@router.get("/{equipment_id}", response_model=EquipmentOut)
def get_equipment(equipment_id: int, db: Session = Depends(get_db)):
    eq = db.get(Equipment, equipment_id)
    if eq is None:
        raise HTTPException(404, "装备不存在")
    return _equipment_out(db, eq)


@router.patch("/{equipment_id}", response_model=EquipmentOut)
def update_equipment(equipment_id: int, payload: EquipmentUpdate, db: Session = Depends(get_db)):
    eq = db.get(Equipment, equipment_id)
    if eq is None:
        raise HTTPException(404, "装备不存在")
    data = payload.model_dump(exclude_unset=True, exclude={"repair_requirements"})
    for k, v in data.items():
        setattr(eq, k, v)
    # 更新维修需求（若提供）
    if payload.repair_requirements is not None:
        for r in list(eq.repair_requirements):
            db.delete(r)
        db.flush()
        for req in payload.repair_requirements:
            db.add(
                EquipmentRepairRequirement(
                    equipment_id=eq.id,
                    item_id=req.item_id,
                    quantity=req.quantity,
                )
            )
        db.flush()
        from app.services.relation import RelationService

        RelationService(db).sync_equipment(eq)
    db.commit()
    db.refresh(eq)
    return _equipment_out(db, eq)


@router.delete("/{equipment_id}", status_code=204)
def delete_equipment(equipment_id: int, db: Session = Depends(get_db)):
    eq = db.get(Equipment, equipment_id)
    if eq is None:
        raise HTTPException(404, "装备不存在")
    eq.is_active = False
    db.commit()
    return None
