"""炼金 / 生产 API：Recipe CRUD + 生产记录 + 配方分析。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.recipe import (
    ProductionRecord,
    Recipe,
    RecipeMaterial,
    RecipeOutput,
)
from app.schemas.recipe import (
    ProductionRecordCreate,
    ProductionRecordOut,
    RecipeCreate,
    RecipeMaterialOut,
    RecipeOut,
    RecipeOutputOut,
    RecipeUpdate,
)
from app.services.recipe import RecipeService

router = APIRouter(prefix="/recipes", tags=["recipes"])
prod_router = APIRouter(prefix="/production-records", tags=["production-records"])


def _recipe_out(db: Session, r: Recipe) -> RecipeOut:
    out = RecipeOut.model_validate(r)
    mats = []
    for m in r.materials:
        mo = RecipeMaterialOut.model_validate(m)
        mo.item_name = m.item.name if m.item else None
        mo.icon_url = m.item.icon_url if m.item else None
        mats.append(mo)
    outs = []
    for o in r.outputs:
        oo = RecipeOutputOut.model_validate(o)
        oo.item_name = o.item.name if o.item else None
        oo.icon_url = o.item.icon_url if o.item else None
        outs.append(oo)
    out.materials = mats
    out.outputs = outs
    return out


@router.get("", response_model=dict)
def list_recipes(db: Session = Depends(get_db)):
    rows = db.execute(select(Recipe).order_by(Recipe.name)).scalars().all()
    return {"total": len(rows), "items": [_recipe_out(db, r).model_dump() for r in rows]}


@router.post("", response_model=RecipeOut, status_code=201)
def create_recipe(payload: RecipeCreate, db: Session = Depends(get_db)):
    existing = db.execute(select(Recipe).where(Recipe.name == payload.name)).scalar_one_or_none()
    if existing:
        raise HTTPException(409, "配方名称已存在")
    r = Recipe(
        name=payload.name,
        category=payload.category,
        description=payload.description,
        expected_success_rate=payload.expected_success_rate,
    )
    db.add(r)
    db.flush()
    for m in payload.materials:
        db.add(RecipeMaterial(recipe_id=r.id, item_id=m.item_id, quantity=m.quantity))
    for o in payload.outputs:
        db.add(RecipeOutput(recipe_id=r.id, item_id=o.item_id, quantity=o.quantity))
    db.flush()
    from app.services.relation import RelationService

    RelationService(db).sync_recipe(r)
    db.commit()
    db.refresh(r)
    return _recipe_out(db, r)


@router.get("/{recipe_id}", response_model=RecipeOut)
def get_recipe(recipe_id: int, db: Session = Depends(get_db)):
    r = db.get(Recipe, recipe_id)
    if r is None:
        raise HTTPException(404, "配方不存在")
    return _recipe_out(db, r)


@router.get("/{recipe_id}/analysis", response_model=dict)
def recipe_analysis(recipe_id: int, db: Session = Depends(get_db)):
    try:
        return RecipeService(db).recipe_analysis(recipe_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))


@router.put("/{recipe_id}", response_model=RecipeOut)
def update_recipe(recipe_id: int, payload: RecipeUpdate, db: Session = Depends(get_db)):
    r = db.get(Recipe, recipe_id)
    if r is None:
        raise HTTPException(404, "配方不存在")
    data = payload.model_dump(exclude_unset=True, exclude={"materials", "outputs"})
    for k, v in data.items():
        setattr(r, k, v)
    # 更新材料/产出（若提供）
    if payload.materials is not None:
        for m in list(r.materials):
            db.delete(m)
        db.flush()
        for m in payload.materials:
            db.add(RecipeMaterial(recipe_id=r.id, item_id=m.item_id, quantity=m.quantity))
    if payload.outputs is not None:
        for o in list(r.outputs):
            db.delete(o)
        db.flush()
        for o in payload.outputs:
            db.add(RecipeOutput(recipe_id=r.id, item_id=o.item_id, quantity=o.quantity))
    if payload.materials is not None or payload.outputs is not None:
        db.flush()
        from app.services.relation import RelationService

        RelationService(db).sync_recipe(r)
    db.commit()
    db.refresh(r)
    return _recipe_out(db, r)


@router.delete("/{recipe_id}", status_code=204)
def delete_recipe(recipe_id: int, db: Session = Depends(get_db)):
    r = db.get(Recipe, recipe_id)
    if r is None:
        raise HTTPException(404, "配方不存在")
    r.is_active = False
    db.commit()
    return None


# ---- Production Records ----

def _prod_out(db: Session, p: ProductionRecord) -> ProductionRecordOut:
    out = ProductionRecordOut.model_validate(p)
    out.recipe_name = p.recipe.name if p.recipe else None
    return out


@prod_router.post("", response_model=ProductionRecordOut, status_code=201)
def create_production_record(payload: ProductionRecordCreate, db: Session = Depends(get_db)):
    try:
        record = RecipeService(db).create_production_record(payload)
        db.commit()
        db.refresh(record)
        return _prod_out(db, record)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(400, str(exc))


@prod_router.get("", response_model=dict)
def list_production_records(
    recipe_id: int = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    from sqlalchemy import func

    stmt = select(ProductionRecord)
    count_stmt = select(func.count()).select_from(ProductionRecord)
    if recipe_id is not None:
        stmt = stmt.where(ProductionRecord.recipe_id == recipe_id)
        count_stmt = count_stmt.where(ProductionRecord.recipe_id == recipe_id)
    total = db.execute(count_stmt).scalar_one()
    rows = (
        db.execute(
            stmt.order_by(ProductionRecord.started_at.desc())
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
        "items": [_prod_out(db, p).model_dump() for p in rows],
    }


@prod_router.put("/{record_id}", response_model=ProductionRecordOut)
def update_production_record(
    record_id: int, payload: ProductionRecordCreate, db: Session = Depends(get_db)
):
    try:
        record = RecipeService(db).update_production_record(record_id, payload)
        db.commit()
        db.refresh(record)
        return _prod_out(db, record)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(400, str(exc))


@prod_router.delete("/{record_id}", status_code=204)
def delete_production_record(record_id: int, db: Session = Depends(get_db)):
    record = db.get(ProductionRecord, record_id)
    if record is None:
        raise HTTPException(404, "生产记录不存在")
    from app.services.activity import ActivityService

    ActivityService(db).delete_by_ref("production_record", record_id)
    db.delete(record)
    db.commit()
    return None
