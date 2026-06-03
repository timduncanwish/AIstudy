import json

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.user_service import get_or_create_user
from app.services.challenge_service import (
    get_or_create_daily_task,
    generate_challenge,
    submit_answer,
    get_user_stats,
)
from app.schemas.challenge import (
    ChallengeOption,
    ChallengeQuestion,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
    DailyTaskResponse,
    UserStatsResponse,
)

router = APIRouter(prefix="/challenge", tags=["challenge"])


@router.get("/daily", response_model=DailyTaskResponse)
async def get_daily_task(
    subject: str = Query("chinese"),
    grade: int = Query(3),
    db: AsyncSession = Depends(get_db),
    x_user_id: str = Header(None, alias="X-User-Id"),
):
    user = await get_or_create_user(db, x_user_id or "anonymous", grade)
    task = await get_or_create_daily_task(db, user.id, subject, grade)
    words = json.loads(task.words_json)
    return DailyTaskResponse(
        task_date=task.task_date,
        subject=task.subject,
        total=task.total,
        completed=task.completed,
        remaining=max(0, task.total - task.completed),
        words=words,
    )


@router.get("/question", response_model=ChallengeQuestion | None)
async def get_challenge_question(
    subject: str = Query("chinese"),
    grade: int = Query(3),
    db: AsyncSession = Depends(get_db),
    x_user_id: str = Header(None, alias="X-User-Id"),
):
    user = await get_or_create_user(db, x_user_id or "anonymous", grade)
    challenge = await generate_challenge(db, user.id, subject, grade)
    if not challenge:
        return None

    options = [
        ChallengeOption(text=opt["text"], index=opt["index"])
        for opt in challenge.get("options", [])
    ]

    return ChallengeQuestion(
        word=challenge.get("word", ""),
        pinyin=challenge.get("pinyin", ""),
        level=challenge.get("level", 1),
        level_name=challenge.get("level_name", ""),
        question_text=challenge.get("question_text", ""),
        hint=challenge.get("hint", ""),
        options=options,
        correct_answer=challenge.get("correct_answer", ""),
    )


@router.post("/submit", response_model=SubmitAnswerResponse)
async def submit_challenge_answer(
    body: SubmitAnswerRequest,
    db: AsyncSession = Depends(get_db),
    x_user_id: str = Header(None, alias="X-User-Id"),
):
    user = await get_or_create_user(db, x_user_id or "anonymous", body.grade)
    result = await submit_answer(
        db=db,
        user_id=user.id,
        word_str=body.word,
        subject=body.subject,
        grade=body.grade,
        level=body.level,
        answer=body.answer,
        streak=body.streak,
    )
    return SubmitAnswerResponse(**result)


@router.get("/stats", response_model=UserStatsResponse)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    x_user_id: str = Header(None, alias="X-User-Id"),
):
    user = await get_or_create_user(db, x_user_id or "anonymous")
    stats = await get_user_stats(db, user.id)
    return UserStatsResponse(**stats)
