from fastapi import APIRouter, Depends, Header, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.user_service import get_or_create_user
from app.services.mistake_service import list_mistakes, get_mistake, review_mistake
from app.schemas.mistake import (
    MistakeResponse,
    MistakeListResponse,
    ReviewRequest,
)

router = APIRouter(prefix="/mistakes", tags=["mistakes"])


@router.get("", response_model=MistakeListResponse)
async def get_mistakes(
    subject: str | None = None,
    review_due: bool = False,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    x_user_id: str = Header(None, alias="X-User-Id"),
):
    user = await get_or_create_user(db, x_user_id or "anonymous")
    items, total = await list_mistakes(db, user.id, subject, review_due, page, size)
    return MistakeListResponse(
        items=[MistakeResponse.model_validate(m) for m in items],
        total=total,
        page=page,
    )


@router.get("/{mistake_id}", response_model=MistakeResponse)
async def get_mistake_detail(
    mistake_id: int,
    db: AsyncSession = Depends(get_db),
    x_user_id: str = Header(None, alias="X-User-Id"),
):
    user = await get_or_create_user(db, x_user_id or "anonymous")
    mistake = await get_mistake(db, mistake_id, user.id)
    if not mistake:
        raise HTTPException(status_code=404, detail="错题不存在")
    return MistakeResponse.model_validate(mistake)


@router.post("/{mistake_id}/review", response_model=MistakeResponse)
async def review_mistake_api(
    mistake_id: int,
    body: ReviewRequest,
    db: AsyncSession = Depends(get_db),
    x_user_id: str = Header(None, alias="X-User-Id"),
):
    user = await get_or_create_user(db, x_user_id or "anonymous")
    mistake = await get_mistake(db, mistake_id, user.id)
    if not mistake:
        raise HTTPException(status_code=404, detail="错题不存在")
    updated = await review_mistake(db, mistake, body.correct)
    return MistakeResponse.model_validate(updated)
