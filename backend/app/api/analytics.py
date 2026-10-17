from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_staff_read
from app.models import User
from app.schemas.analytics import DashboardAnalytics
from app.services.analytics import build_dashboard


router = APIRouter(prefix="/admin/analytics", tags=["admin-analytics"])


@router.get("/dashboard", response_model=DashboardAnalytics)
def dashboard(
    days: int = Query(30, ge=7, le=365),
    _: User = Depends(require_staff_read),
    db: Session = Depends(get_db),
):
    return build_dashboard(db, days)
