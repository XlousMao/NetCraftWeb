"""AI 分析 API。

安全原则：AI 只读取结构化分析数据、生成文本，绝不直接修改数据库。
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.analysis import service as analysis
from app.services.ai import build_analysis_payload, generate_analysis

router = APIRouter(prefix="/ai", tags=["ai"])


class AIRequest(BaseModel):
    question: Optional[str] = None


@router.post("/analyze", response_model=dict)
async def analyze(payload: AIRequest, db: Session = Depends(get_db)):
    dashboard_data = analysis.dashboard(db)
    structured = build_analysis_payload(dashboard_data, payload.question)
    result = await generate_analysis(structured)
    return {
        "provider": result.get("provider"),
        "content": result.get("content"),
        "structured_data": structured,
    }
