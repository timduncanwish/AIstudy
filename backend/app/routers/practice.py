from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.user_service import get_or_create_user
from app.services.practice_service import (
    generate_daily_practice,
    submit_practice,
    get_practice_history,
)
from app.schemas.practice import (
    DailyPracticeGenerateRequest,
    DailyPracticeResponse,
    PracticeQuestionItem,
    SubmitPracticeRequest,
    PracticeHistoryItem,
    PracticeHistoryResponse,
)

router = APIRouter(prefix="/practice", tags=["practice"])


@router.post("/generate", response_model=DailyPracticeResponse)
async def generate(
    body: DailyPracticeGenerateRequest,
    db: AsyncSession = Depends(get_db),
    x_user_id: str = Header(None, alias="X-User-Id"),
):
    user = await get_or_create_user(db, x_user_id or "anonymous")
    import json
    practice = await generate_daily_practice(db, user.id, body.subject)
    questions = json.loads(practice.questions_json)
    return DailyPracticeResponse(
        id=practice.id,
        subject=practice.subject,
        topic=practice.topic,
        questions=[PracticeQuestionItem(**q) for q in questions],
        score=practice.score,
        total=practice.total,
        created_at=practice.created_at,
    )


@router.post("/{practice_id}/submit", response_model=DailyPracticeResponse)
async def submit(
    practice_id: int,
    body: SubmitPracticeRequest,
    db: AsyncSession = Depends(get_db),
    x_user_id: str = Header(None, alias="X-User-Id"),
):
    user = await get_or_create_user(db, x_user_id or "anonymous")
    import json
    practice = await submit_practice(db, practice_id, user.id, body.answers)
    if not practice:
        raise HTTPException(status_code=404, detail="练习不存在")
    questions = json.loads(practice.questions_json)
    return DailyPracticeResponse(
        id=practice.id,
        subject=practice.subject,
        topic=practice.topic,
        questions=[PracticeQuestionItem(**q) for q in questions],
        score=practice.score,
        total=practice.total,
        created_at=practice.created_at,
    )


@router.get("/history", response_model=PracticeHistoryResponse)
async def history(
    db: AsyncSession = Depends(get_db),
    x_user_id: str = Header(None, alias="X-User-Id"),
):
    user = await get_or_create_user(db, x_user_id or "anonymous")
    data = await get_practice_history(db, user.id)
    return PracticeHistoryResponse(
        items=[
            PracticeHistoryItem(
                id=item.id,
                subject=item.subject,
                topic=item.topic,
                score=item.score,
                total=item.total,
                created_at=item.created_at,
            )
            for item in data["items"]
        ],
        streak=data["streak"],
    )
