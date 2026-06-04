from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.mistake import Mistake

_knowledge_service = None

def _get_knowledge_service():
    global _knowledge_service
    if _knowledge_service is None:
        try:
            from app.services import knowledge_service as ks
            _knowledge_service = ks
        except ImportError:
            pass
    return _knowledge_service


REVIEW_INTERVALS = [1, 2, 4, 7, 14, 30]


async def list_mistakes(
    db: AsyncSession,
    user_id: int,
    subject: str | None = None,
    review_due: bool = False,
    topic: str | None = None,
    page: int = 1,
    size: int = 20,
) -> tuple[list[Mistake], int]:
    query = select(Mistake).where(Mistake.user_id == user_id)
    count_query = select(func.count()).select_from(Mistake).where(Mistake.user_id == user_id)

    if subject:
        query = query.where(Mistake.subject == subject)
        count_query = count_query.where(Mistake.subject == subject)

    if topic:
        query = query.where(Mistake.topic == topic)
        count_query = count_query.where(Mistake.topic == topic)

    if review_due:
        query = query.where(Mistake.next_review <= datetime.now())
        count_query = count_query.where(Mistake.next_review <= datetime.now())

    query = query.order_by(Mistake.next_review.asc())
    query = query.offset((page - 1) * size).limit(size)

    total = (await db.execute(count_query)).scalar() or 0
    result = await db.execute(query)
    items = list(result.scalars().all())

    return items, total


async def get_mistake(db: AsyncSession, mistake_id: int, user_id: int) -> Mistake | None:
    result = await db.execute(
        select(Mistake).where(Mistake.id == mistake_id, Mistake.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def review_mistake(
    db: AsyncSession, mistake: Mistake, correct: bool
) -> Mistake:
    mistake.review_count += 1

    if correct:
        mistake.mastery = min(5, mistake.mastery + 1)
    else:
        mistake.mastery = max(0, mistake.mastery - 1)

    interval_days = REVIEW_INTERVALS[min(mistake.mastery, len(REVIEW_INTERVALS) - 1)]
    mistake.next_review = datetime.now() + timedelta(days=interval_days)

    await db.commit()
    await db.refresh(mistake)
    try:
        ks = _get_knowledge_service()
        if ks:
            await ks.update_mistake_in_kb(mistake)
    except Exception:
        pass
    return mistake


async def get_relevant_mistakes(
    db: AsyncSession,
    user_id: int,
    subject: str,
    limit: int = 5,
) -> list[Mistake]:
    query = (
        select(Mistake)
        .where(Mistake.user_id == user_id, Mistake.subject == subject)
        .order_by(Mistake.mastery.asc(), Mistake.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_mistake_stats(db: AsyncSession, user_id: int) -> dict:
    total_q = select(func.count()).select_from(Mistake).where(Mistake.user_id == user_id)
    mastered_q = select(func.count()).select_from(Mistake).where(
        Mistake.user_id == user_id, Mistake.mastery >= 4
    )
    reviewing_q = select(func.count()).select_from(Mistake).where(
        Mistake.user_id == user_id, Mistake.mastery >= 1, Mistake.mastery <= 3
    )
    new_q = select(func.count()).select_from(Mistake).where(
        Mistake.user_id == user_id, Mistake.mastery == 0
    )

    topic_q = (
        select(Mistake.topic, func.count().label("count"), func.avg(Mistake.mastery).label("avg_mastery"))
        .where(Mistake.user_id == user_id, Mistake.topic != "", Mistake.topic.isnot(None))
        .group_by(Mistake.topic)
        .order_by(func.count().desc())
        .limit(10)
    )

    subject_q = (
        select(Mistake.subject, func.count().label("count"))
        .where(Mistake.user_id == user_id)
        .group_by(Mistake.subject)
    )

    total = (await db.execute(total_q)).scalar() or 0
    mastered = (await db.execute(mastered_q)).scalar() or 0
    reviewing = (await db.execute(reviewing_q)).scalar() or 0
    new = (await db.execute(new_q)).scalar() or 0

    topic_rows = (await db.execute(topic_q)).all()
    topics = [
        {"topic": r[0], "count": r[1], "avg_mastery": round(float(r[2]), 1)}
        for r in topic_rows
    ]

    subject_rows = (await db.execute(subject_q)).all()
    subject_dist = {r[0]: r[1] for r in subject_rows}

    return {
        "total_mistakes": total,
        "mastered_count": mastered,
        "reviewing_count": reviewing,
        "new_count": new,
        "topics": topics,
        "subject_dist": subject_dist,
    }
