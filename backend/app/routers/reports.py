from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.user_service import get_or_create_user
from app.services.report_service import get_daily_report, get_weekly_report
from app.schemas.report import DailyReport, WeeklyReport

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/daily", response_model=DailyReport)
async def daily_report(
    date: str = Query(default=None),
    db: AsyncSession = Depends(get_db),
    x_user_id: str = Header(None, alias="X-User-Id"),
):
    user = await get_or_create_user(db, x_user_id or "anonymous")
    target_date = date or datetime.now().strftime("%Y-%m-%d")
    return await get_daily_report(db, user.id, target_date)


@router.get("/weekly", response_model=WeeklyReport)
async def weekly_report(
    week_start: str = Query(default=None),
    db: AsyncSession = Depends(get_db),
    x_user_id: str = Header(None, alias="X-User-Id"),
):
    user = await get_or_create_user(db, x_user_id or "anonymous")
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())
    target = week_start or start_of_week.strftime("%Y-%m-%d")
    return await get_weekly_report(db, user.id, target)
