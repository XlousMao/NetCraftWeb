"""物品 API：CRUD / 图片上传 / 市场观察 / 关系 / 关系图。"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.item import Item, ItemImage, ItemRelation, ItemRole
from app.models.market import MarketObservation
from app.repositories.item import ItemRepository
from app.schemas.item import (
    ItemCreate,
    ItemDetailOut,
    ItemImageOut,
    ItemOut,
    ItemRelationOut,
    ItemUpdate,
    MarketObservationCreate,
    MarketObservationOut,
)
from app.services.image import ImageService
from app.services.valuation import ValuationService
from app.core.config import settings

router = APIRouter(prefix="/items", tags=["items"])


def _item_out(db: Session, item: Item) -> ItemOut:
    img, rel = ItemRepository(db).with_counts(item.id)
    roles = [r.role for r in item.roles]
    return ItemOut(
        id=item.id,
        name=item.name,
        display_name=item.display_name,
        category=item.category,
        subcategory=item.subcategory,
        description=item.description,
        icon_url=item.icon_url,
        rarity=item.rarity,
        level=item.level,
        stack_size=item.stack_size,
        tags=item.tags or [],
        roles=roles,
        importance_score=item.importance_score,
        is_active=item.is_active,
        created_at=item.created_at,
        updated_at=item.updated_at,
        image_count=img,
        relation_count=rel,
    )


@router.get("", response_model=dict)
def list_items(
    q: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    tags: Optional[str] = Query(None),
    sort: str = Query("name"),
    order: str = Query("asc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    tag_list = [t for t in (tags or "").split(",") if t]
    rows, total = ItemRepository(db).search(
        q=q,
        category=category,
        tags=tag_list or None,
        sort=sort,
        order=order,
        limit=page_size,
        offset=(page - 1) * page_size,
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_item_out(db, i).model_dump() for i in rows],
    }


@router.get("/categories", response_model=list)
def list_categories(db: Session = Depends(get_db)):
    rows = db.execute(select(Item.category).distinct()).all()
    return [r[0] for r in rows if r[0]]


@router.post("", response_model=ItemOut, status_code=201)
def create_item(payload: ItemCreate, db: Session = Depends(get_db)):
    existing = db.execute(select(Item).where(Item.name == payload.name)).scalar_one_or_none()
    if existing:
        raise HTTPException(409, f"物品名称「{payload.name}」已存在")
    data = payload.model_dump(exclude={"roles"})
    item = Item(**data)
    db.add(item)
    db.flush()
    for role in payload.roles:
        db.add(ItemRole(item_id=item.id, role=role))
    db.commit()
    db.refresh(item)
    return _item_out(db, item)


@router.get("/{item_id}", response_model=ItemDetailOut)
def get_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(404, "物品不存在")
    base = _item_out(db, item).model_dump()
    base["images"] = [ItemImageOut.model_validate(img).model_dump() for img in item.images]
    base["market_observations"] = [
        MarketObservationOut.model_validate(o).model_dump()
        for o in sorted(item.market_observations, key=lambda x: x.observed_at, reverse=True)
    ]
    base["relations"] = [
        ItemRelationOut.model_validate(r).model_dump() for r in item.relations_out
    ]
    vs = ValuationService(db)
    try:
        base["current_value"] = vs.value(item.id, 1, "auto").as_dict()
    except Exception:
        base["current_value"] = None
    base["market_summary"] = vs.market_summary(item.id)
    base["price_history"] = vs.price_history(item.id)
    return base


@router.patch("/{item_id}", response_model=ItemOut)
def update_item(item_id: int, payload: ItemUpdate, db: Session = Depends(get_db)):
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(404, "物品不存在")
    data = payload.model_dump(exclude_unset=True, exclude={"roles"})
    for k, v in data.items():
        setattr(item, k, v)
    if payload.roles is not None:
        for r in item.roles:
            db.delete(r)
        for role in payload.roles:
            db.add(ItemRole(item_id=item.id, role=role))
    db.commit()
    db.refresh(item)
    return _item_out(db, item)


@router.delete("/{item_id}", status_code=204)
def delete_item(item_id: int, db: Session = Depends(get_db)):
    """软删除：历史数据严禁因主数据删除而消失。"""
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(404, "物品不存在")
    item.is_active = False
    db.commit()
    return None


# ---- 图片 ----

@router.post("/{item_id}/images", response_model=ItemImageOut, status_code=201)
async def upload_image(
    item_id: int,
    file: UploadFile = File(...),
    image_type: str = "icon",
    is_primary: bool = False,
    db: Session = Depends(get_db),
):
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(404, "物品不存在")
    data = await file.read()
    if len(data) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(413, "文件过大")
    image = ImageService(db).upload(
        item_id, data, file.filename or "image.png", image_type, is_primary
    )
    db.commit()
    db.refresh(image)
    return ItemImageOut.model_validate(image)


@router.post("/{item_id}/images/paste", response_model=ItemImageOut, status_code=201)
async def paste_image(item_id: int, request: Request, db: Session = Depends(get_db)):
    """Ctrl+V 粘贴截图：body 为原始图片字节。"""
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(404, "物品不存在")
    data = await request.body()
    if not data:
        raise HTTPException(400, "未收到图片数据")
    if len(data) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(413, "文件过大")
    image = ImageService(db).upload(item_id, data, "pasted.png", "screenshot", False)
    db.commit()
    db.refresh(image)
    return ItemImageOut.model_validate(image)


@router.post("/{item_id}/images/{image_id}/primary", response_model=ItemImageOut)
def set_primary(item_id: int, image_id: int, db: Session = Depends(get_db)):
    image = ImageService(db).set_primary(item_id, image_id)
    if image is None:
        raise HTTPException(404, "图片不存在")
    db.commit()
    db.refresh(image)
    return ItemImageOut.model_validate(image)


# ---- 市场观察 ----

@router.get("/{item_id}/market", response_model=list)
def list_market(item_id: int, db: Session = Depends(get_db)):
    rows = db.execute(
        select(MarketObservation)
        .where(MarketObservation.item_id == item_id)
        .order_by(MarketObservation.observed_at.desc())
    ).scalars().all()
    return [MarketObservationOut.model_validate(o).model_dump() for o in rows]


@router.post("/{item_id}/market", response_model=MarketObservationOut, status_code=201)
def record_market(item_id: int, payload: MarketObservationCreate, db: Session = Depends(get_db)):
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(404, "物品不存在")
    obs = ValuationService(db).record_observation(
        item_id,
        observation_type=payload.observation_type,
        price_quantity=payload.price_quantity,
        quantity=payload.quantity,
        price_item_id=payload.price_item_id,
        seller_name=payload.seller_name,
        location=payload.location,
        source=payload.source,
        observed_at=payload.observed_at,
        note=payload.note,
    )
    db.commit()
    db.refresh(obs)
    return MarketObservationOut.model_validate(obs)


@router.get("/{item_id}/market/summary", response_model=dict)
def market_summary(item_id: int, db: Session = Depends(get_db)):
    return ValuationService(db).market_summary(item_id)


# ---- 关系 ----

@router.get("/{item_id}/relations", response_model=list)
def get_relations(item_id: int, db: Session = Depends(get_db)):
    rows = db.execute(
        select(ItemRelation).where(ItemRelation.target_item_id == item_id)
    ).scalars().all()
    return [ItemRelationOut.model_validate(r).model_dump() for r in rows]


@router.get("/{item_id}/relation-graph", response_model=dict)
def relation_graph(item_id: int, depth: int = Query(1, ge=1, le=3), db: Session = Depends(get_db)):
    """返回以 item 为中心的关系图（节点 + 边）。"""
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(404, "物品不存在")

    nodes = {f"item:{item.id}": {"id": f"item:{item.id}", "label": item.name, "type": "item"}}
    edges = []

    relations = db.execute(
        select(ItemRelation).where(ItemRelation.target_item_id == item_id)
    ).scalars().all()
    for r in relations:
        src_id = f"{r.source_type}:{r.source_id}"
        src_label = _resolve_source_label(db, r.source_type, r.source_id)
        nodes[src_id] = {"id": src_id, "label": src_label, "type": r.source_type}
        edges.append(
            {
                "from": src_id,
                "to": f"item:{item.id}",
                "label": r.relation_type,
                "relation_type": r.relation_type,
                "quantity": r.quantity,
            }
        )

    return {"nodes": list(nodes.values()), "edges": edges}


def _resolve_source_label(db: Session, source_type: str, source_id: int) -> str:
    from app.models.dungeon import Dungeon
    from app.models.equipment import Equipment
    from app.models.recipe import Recipe

    if source_type == "dungeon":
        obj = db.get(Dungeon, source_id)
    elif source_type == "equipment":
        obj = db.get(Equipment, source_id)
    elif source_type == "recipe":
        obj = db.get(Recipe, source_id)
    else:
        obj = None
    return obj.name if obj else f"{source_type}#{source_id}"
