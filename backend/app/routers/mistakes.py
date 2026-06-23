from datetime import datetime

from fastapi import APIRouter, Depends, Header, Query, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.mistake import Mistake
from app.services.user_service import get_or_create_user
from app.scope import active_student_id
from app.services.mistake_service import (
    list_mistakes, get_mistake, review_mistake, get_mistake_stats,
    get_knowledge_map, get_topic_detail, generate_practice_questions,
)
from app.schemas.mistake import (
    MistakeResponse,
    MistakeListResponse,
    ReviewRequest,
    MistakeStatsResponse,
    KnowledgeMapResponse,
    KnowledgeTopic,
    TopicDetailResponse,
    PracticeRequest,
    PracticeResponse,
    PracticeQuestion,
)

router = APIRouter(prefix="/mistakes", tags=["mistakes"])


@router.get("/due-count")
async def get_due_count(
    db: AsyncSession = Depends(get_db),
    x_user_id: str = Header(None, alias="X-User-Id"),
):
    """返回今日待复习错题数量，供首页 badge 使用"""
    user = await get_or_create_user(db, x_user_id or "anonymous")
    sid = await active_student_id(db, user.id)
    student_conds = [Mistake.student_id == sid] if sid is not None else []
    now = datetime.now()
    result = await db.execute(
        select(func.count()).select_from(Mistake).where(
            Mistake.user_id == user.id,
            *student_conds,
            Mistake.mastery < 5,
            Mistake.next_review <= now,
        )
    )
    return {"count": result.scalar() or 0}


@router.get("", response_model=MistakeListResponse)
async def get_mistakes(
    subject: str | None = None,
    topic: str | None = None,
    review_due: bool = False,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    x_user_id: str = Header(None, alias="X-User-Id"),
):
    user = await get_or_create_user(db, x_user_id or "anonymous")
    items, total = await list_mistakes(db, user.id, subject, review_due, topic, page, size)
    return MistakeListResponse(
        items=[MistakeResponse.model_validate(m) for m in items],
        total=total,
        page=page,
    )


@router.get("/stats", response_model=MistakeStatsResponse)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    x_user_id: str = Header(None, alias="X-User-Id"),
):
    user = await get_or_create_user(db, x_user_id or "anonymous")
    stats = await get_mistake_stats(db, user.id)
    return MistakeStatsResponse(**stats)


@router.get("/knowledge-map", response_model=KnowledgeMapResponse)
async def knowledge_map(
    db: AsyncSession = Depends(get_db),
    x_user_id: str = Header(None, alias="X-User-Id"),
):
    user = await get_or_create_user(db, x_user_id or "anonymous")
    data = await get_knowledge_map(db, user.id)
    return KnowledgeMapResponse(
        subjects={
            s: [KnowledgeTopic(**t) for t in topics]
            for s, topics in data["subjects"].items()
        }
    )


@router.get("/topic/{subject}/{topic:path}", response_model=TopicDetailResponse)
async def topic_detail(
    subject: str,
    topic: str,
    db: AsyncSession = Depends(get_db),
    x_user_id: str = Header(None, alias="X-User-Id"),
):
    user = await get_or_create_user(db, x_user_id or "anonymous")
    data = await get_topic_detail(db, user.id, subject, topic)
    if not data:
        raise HTTPException(status_code=404, detail="知识点不存在")
    return TopicDetailResponse(
        topic=data["topic"],
        subject=data["subject"],
        count=data["count"],
        avg_mastery=data["avg_mastery"],
        mistakes=[MistakeResponse.model_validate(m) for m in data["mistakes"]],
    )


@router.post("/practice", response_model=PracticeResponse)
async def practice(
    body: PracticeRequest,
    db: AsyncSession = Depends(get_db),
    x_user_id: str = Header(None, alias="X-User-Id"),
):
    user = await get_or_create_user(db, x_user_id or "anonymous")
    questions = await generate_practice_questions(db, user.id, body.subject, body.topic)
    return PracticeResponse(
        topic=body.topic,
        questions=[PracticeQuestion(**q) for q in questions],
    )


@router.post("/build-kb")
async def build_knowledge_base(
    db: AsyncSession = Depends(get_db),
    x_user_id: str = Header(None, alias="X-User-Id"),
):
    try:
        from app.services import knowledge_service
    except ImportError:
        raise HTTPException(status_code=503, detail="知识库服务未安装，请先安装 chromadb")

    user = await get_or_create_user(db, x_user_id or "anonymous")
    sid = await active_student_id(db, user.id)
    student_conds = [Mistake.student_id == sid] if sid is not None else []
    result = await db.execute(
        select(Mistake).where(Mistake.user_id == user.id, *student_conds)
    )
    mistakes = list(result.scalars().all())

    added = 0
    for m in mistakes:
        try:
            await knowledge_service.add_mistake_to_kb(m)
            added += 1
        except Exception:
            pass

    return {"detail": f"已将 {added} 条错题导入知识库", "total": len(mistakes), "added": added}


@router.get("/detail/{mistake_id}", response_model=MistakeResponse)
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


@router.post("/detail/{mistake_id}/review", response_model=MistakeResponse)
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
