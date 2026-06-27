from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import ZHIPU_API_KEY
from app.database import get_db
from app.limiter import limiter
from app.schemas.preview import (
    CompletePreviewItemRequest,
    CompletePreviewItemResponse,
    BadgeInfo,
    ChallengeQuestion,
    ChallengeResultRequest,
    ChallengeResultResponse,
    ExplainPreviewItemRequest,
    ExplainPreviewItemResponse,
    ParentSummaryResponse,
    PreviewUnitDetailResponse,
    PreviewUnitItem,
    PreviewUnitsResponse,
    StudiedUnit,
    TextbookOption,
    TextbookOptionsResponse,
    UnitChallengeResponse,
)
from app.services.ai_service import explain_preview_item
from app.services.challenge_service import record_preview_challenge
from app.services.preview_service import (
    build_unit_challenge,
    complete_preview_item,
    get_parent_preview_summary,
    get_preview_unit_detail,
    get_preview_units,
    list_textbook_options,
)
from app.services.user_service import get_or_create_user

router = APIRouter(prefix="/preview", tags=["preview"])


@router.get("/textbooks", response_model=TextbookOptionsResponse)
async def textbooks():
    return TextbookOptionsResponse(items=[TextbookOption(**item) for item in list_textbook_options()])


@router.get("/units", response_model=PreviewUnitsResponse)
async def units(
    subject: str = Query("chinese"),
    grade: int = Query(3),
    semester: str = Query("上册"),
    textbook_version: str = Query(""),
    db: AsyncSession = Depends(get_db),
    x_user_id: str = Header(None, alias="X-User-Id"),
):
    user = await get_or_create_user(db, x_user_id or "anonymous", grade)
    version = textbook_version or ("统编版" if subject == "chinese" else "PEP人教版")
    data = await get_preview_units(db, user.id, subject, grade, semester, version)
    return PreviewUnitsResponse(
        subject=subject,
        grade=grade,
        semester=semester,
        textbook_version=version,
        units=[PreviewUnitItem(**item) for item in data],
    )


@router.get("/units/{unit_no}", response_model=PreviewUnitDetailResponse)
async def unit_detail(
    unit_no: int,
    subject: str = Query("chinese"),
    grade: int = Query(3),
    semester: str = Query("上册"),
    textbook_version: str = Query(""),
    db: AsyncSession = Depends(get_db),
    x_user_id: str = Header(None, alias="X-User-Id"),
):
    user = await get_or_create_user(db, x_user_id or "anonymous", grade)
    version = textbook_version or ("统编版" if subject == "chinese" else "PEP人教版")
    data = await get_preview_unit_detail(db, user.id, subject, grade, semester, version, unit_no)
    if not data:
        raise HTTPException(status_code=404, detail="暂无该教材单元预习数据")
    return PreviewUnitDetailResponse(**data)


@router.post("/complete", response_model=CompletePreviewItemResponse)
async def complete(
    body: CompletePreviewItemRequest,
    db: AsyncSession = Depends(get_db),
    x_user_id: str = Header(None, alias="X-User-Id"),
):
    user = await get_or_create_user(db, x_user_id or "anonymous", body.grade)
    progress = await complete_preview_item(
        db=db,
        user_id=user.id,
        subject=body.subject,
        grade=body.grade,
        semester=body.semester,
        textbook_version=body.textbook_version,
        unit=body.unit,
        item_key=body.item_key,
        item_type=body.item_type,
    )
    return CompletePreviewItemResponse(
        item_key=progress.item_key,
        completed=True,
        completed_at=progress.completed_at,
    )


@router.post("/explain", response_model=ExplainPreviewItemResponse)
@limiter.limit("20/minute")
async def explain(request: Request, body: ExplainPreviewItemRequest):
    if body.subject not in ("chinese", "english"):
        raise HTTPException(status_code=400, detail="科目仅支持 chinese 或 english")
    if not 1 <= body.grade <= 9:
        raise HTTPException(status_code=400, detail="年级范围为1-9年级")
    if not body.word.strip():
        raise HTTPException(status_code=400, detail="缺少要讲解的字/词")
    if not ZHIPU_API_KEY or ZHIPU_API_KEY == "your_api_key_here":
        raise HTTPException(status_code=503, detail="AI服务未配置，请在 .env 设置 ZHIPU_API_KEY")

    try:
        explanation = await explain_preview_item(
            subject=body.subject,
            grade=body.grade,
            word=body.word,
            item_type=body.item_type,
            category_label=body.category_label,
            unit_title=body.unit_title,
            meaning=body.meaning,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI服务调用失败: {str(e)}")

    return ExplainPreviewItemResponse(word=body.word, explanation=explanation)


@router.get("/unit-challenge", response_model=UnitChallengeResponse)
async def unit_challenge(
    subject: str = Query("chinese"),
    grade: int = Query(3),
    semester: str = Query("上册"),
    unit_no: int = Query(...),
):
    if subject not in ("chinese", "english"):
        raise HTTPException(status_code=400, detail="科目仅支持 chinese 或 english")
    questions = build_unit_challenge(subject, grade, semester, unit_no)
    if not questions:
        raise HTTPException(status_code=404, detail="该单元暂无可闯关的字词")
    return UnitChallengeResponse(
        subject=subject,
        grade=grade,
        semester=semester,
        unit=unit_no,
        questions=[ChallengeQuestion(**q) for q in questions],
    )


@router.post("/challenge-result", response_model=ChallengeResultResponse)
async def challenge_result(
    body: ChallengeResultRequest,
    db: AsyncSession = Depends(get_db),
    x_user_id: str = Header(None, alias="X-User-Id"),
):
    if body.subject not in ("chinese", "english"):
        raise HTTPException(status_code=400, detail="科目仅支持 chinese 或 english")
    user = await get_or_create_user(db, x_user_id or "anonymous", body.grade)
    data = await record_preview_challenge(
        db, user.id, body.subject, body.grade,
        [{"word": r.word, "correct": r.correct} for r in body.results],
    )
    return ChallengeResultResponse(
        points_earned=data["points_earned"],
        correct_count=data["correct_count"],
        total=data["total"],
        total_points=data["total_points"],
        streak_days=data["streak_days"],
        words_mastered=data["words_mastered"],
        new_badges=[BadgeInfo(**b) for b in data["new_badges"]],
    )


@router.get("/parent-summary", response_model=ParentSummaryResponse)
async def parent_summary(
    days: int = Query(7, ge=1, le=31),
    grade: int = Query(3),
    db: AsyncSession = Depends(get_db),
    x_user_id: str = Header(None, alias="X-User-Id"),
):
    user = await get_or_create_user(db, x_user_id or "anonymous", grade)
    data = await get_parent_preview_summary(db, user.id, days)
    return ParentSummaryResponse(
        period_days=data["period_days"],
        weekly_completed=data["weekly_completed"],
        subject_breakdown=data["subject_breakdown"],
        studied_units=[StudiedUnit(**u) for u in data["studied_units"]],
        review_suggestions=data["review_suggestions"],
    )
