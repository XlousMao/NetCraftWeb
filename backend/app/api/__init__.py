"""API 路由汇总。"""

from fastapi import APIRouter

from app.api import (
    activities,
    ai,
    analysis,
    currency,
    dashboard,
    dungeons,
    equipments,
    items,
    recipes,
)

api_router = APIRouter()
api_router.include_router(items.router)
api_router.include_router(currency.router)
api_router.include_router(dungeons.dungeon_router)
api_router.include_router(dungeons.run_router)
api_router.include_router(equipments.router)
api_router.include_router(recipes.router)
api_router.include_router(recipes.prod_router)
api_router.include_router(activities.router)
api_router.include_router(analysis.router)
api_router.include_router(dashboard.router)
api_router.include_router(ai.router)
