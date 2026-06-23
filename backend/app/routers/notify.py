from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import WX_TMPL_PRACTICE, WX_TMPL_DAILY
from app.database import get_db
from app.models.user import User

router = APIRouter(prefix="/notify", tags=["notify"])


class SubscribeRequest(BaseModel):
    user_id: int
    subscribed: bool


class NotifyTimeRequest(BaseModel):
    user_id: int
    notify_time: str  # "HH:MM"


@router.get("/config")
async def get_notify_config():
    """返回前端订阅所需的微信模板 ID 列表"""
    tmpl_ids = [t for t in [WX_TMPL_PRACTICE, WX_TMPL_DAILY] if t]
    return {"tmpl_ids": tmpl_ids}


@router.post("/subscribe")
async def set_subscribe(body: SubscribeRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == body.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.notify_subscribed = 1 if body.subscribed else 0
    await db.commit()
    return {"ok": True}


@router.post("/time")
async def set_notify_time(body: NotifyTimeRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == body.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.notify_time = body.notify_time
    await db.commit()
    return {"ok": True}


@router.get("/status/{user_id}")
async def get_notify_status(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {
        "subscribed": bool(user.notify_subscribed),
        "notify_time": user.notify_time or "",
    }
