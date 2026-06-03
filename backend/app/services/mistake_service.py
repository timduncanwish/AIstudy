from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.mistake import Mistake


REVIEW_INTERVALS = [1, 2, 4, 7, 14, 30]


async def list_mistakes(
    db: AsyncSession,
    user_id: int,
    subject: str | None = None,
    review_due: bool = False,
    page: int = 1,
    size: int = 20,
) -> tuple[list[Mistake], int]:
    query = select(Mistake).where(Mistake.user_id == user_id)
    count_query = select(func.count()).select_from(Mistake).where(Mistake.user_id == user_id)

    if subject:
        query = query.where(Mistake.subject == subject)
        count_query = count_query.where(Mistake.subject == subject)

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
    return mistake
