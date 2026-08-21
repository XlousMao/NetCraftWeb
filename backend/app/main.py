"""GEAP FastAPI 应用入口。"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import api_router
from app.core.config import settings
from app.db.init_db import init_db
from app.utils.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    init_db()
    # 初始化活动类型目录
    from app.db.session import SessionLocal
    from app.services.activity import ActivityService

    db = SessionLocal()
    try:
        ActivityService(db).ensure_activity_types()
        db.commit()
    finally:
        db.close()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="游戏经济分析、生产成本与副本收益决策平台",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """统一异常处理，返回友好错误格式。"""
    from app.utils.logging import get_logger

    get_logger("geap").error("未处理异常: %s", exc, exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "服务器内部错误"})


app.include_router(api_router, prefix=settings.API_PREFIX)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "app": settings.APP_NAME}


# 静态图片服务
import os  # noqa: E402

_storage_dir = os.path.abspath(settings.UPLOAD_DIR)
os.makedirs(_storage_dir, exist_ok=True)
app.mount("/storage", StaticFiles(directory=_storage_dir), name="storage")
