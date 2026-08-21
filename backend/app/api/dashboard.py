"""Dashboard API。"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.analysis import service as analysis

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=dict)
def dashboard(db: Session = Depends(get_db)):
    return analysis.dashboard(db)
