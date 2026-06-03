from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.homework import Homework
from app.models.mistake import Mistake
from app.models.word_progress import WordProgress
from app.models.daily_task import DailyTask
from app.models.user_stats import UserStats


async def get_daily_report(db: AsyncSession, user_id: int, date: str) -> dict:
    target = datetime.strptime(date, "%Y-%m-%d")
    next_day = target + timedelta(days=1)

    homework_count = await _count_range(db, Homework, user_id, target, next_day)
    mistakes = await _get_mistakes_range(db, user_id, target, next_day)
    mistakes_count = len(mistakes)

    words_result = await db.execute(
        select(func.count()).select_from(WordProgress).where(
            WordProgress.user_id == user_id,
            WordProgress.updated_at >= target,
            WordProgress.updated_at < next_day,
        )
    )
    words_learned = words_result.scalar() or 0

    review_result = await db.execute(
        select(func.count()).select_from(WordProgress).where(
            WordProgress.user_id == user_id,
            WordProgress.review_count > 0,
            WordProgress.updated_at >= target,
            WordProgress.updated_at < next_day,
        )
    )
    review_count = review_result.scalar() or 0

    chinese_hw = await _count_range(db, Homework, user_id, target, next_day, "chinese")
    english_hw = await _count_range(db, Homework, user_id, target, next_day, "english")
    chinese_m = sum(1 for m in mistakes if m.subject == "chinese")
    english_m = sum(1 for m in mistakes if m.subject == "english")

    subject_dist = {
        "chinese": chinese_hw + chinese_m,
        "english": english_hw + english_m,
    }

    topic_counts: dict[str, int] = {}
    for m in mistakes:
        if m.topic:
            topic_counts[m.topic] = topic_counts.get(m.topic, 0) + 1
    weak_topics = sorted(
        [{"topic": k, "count": v} for k, v in topic_counts.items()],
        key=lambda x: x["count"],
        reverse=True,
    )[:3]

    total = homework_count + words_learned + review_count

    return {
        "date": date,
        "chat_count": 0,
        "homework_count": homework_count,
        "words_learned": words_learned,
        "mistakes_count": mistakes_count,
        "review_count": review_count,
        "subject_dist": subject_dist,
        "weak_topics": weak_topics,
        "total_interactions": total,
    }


async def get_weekly_report(db: AsyncSession, user_id: int, week_start: str) -> dict:
    start = datetime.strptime(week_start, "%Y-%m-%d")
    end = start + timedelta(days=7)

    daily_trend = []
    total = 0
    for i in range(7):
        day = start + timedelta(days=i)
        day_str = day.strftime("%Y-%m-%d")
        day_next = day + timedelta(days=1)

        hw = await _count_range(db, Homework, user_id, day, day_next)
        wp = await _count_range(db, WordProgress, user_id, day, day_next)
        count = hw + wp
        daily_trend.append({"date": day_str, "count": count})
        total += count

    words_learned_result = await db.execute(
        select(func.count()).select_from(WordProgress).where(
            WordProgress.user_id == user_id,
            WordProgress.updated_at >= start,
            WordProgress.updated_at < end,
        )
    )
    words_learned = words_learned_result.scalar() or 0

    words_mastered_result = await db.execute(
        select(func.count()).select_from(WordProgress).where(
            WordProgress.user_id == user_id,
            WordProgress.level >= 4,
            WordProgress.updated_at >= start,
            WordProgress.updated_at < end,
        )
    )
    words_mastered = words_mastered_result.scalar() or 0

    mistakes_reviewed = await db.execute(
        select(func.count()).select_from(Mistake).where(
            Mistake.user_id == user_id,
            Mistake.review_count > 0,
            Mistake.created_at >= start,
            Mistake.created_at < end,
        )
    )
    reviewed = mistakes_reviewed.scalar() or 0

    all_mistakes = await _get_mistakes_range(db, user_id, start, end)
    chinese_count = sum(1 for m in all_mistakes if m.subject == "chinese")
    english_count = sum(1 for m in all_mistakes if m.subject == "english")
    subject_dist = {"chinese": chinese_count, "english": english_count}

    topic_counts: dict[str, int] = {}
    for m in all_mistakes:
        if m.topic:
            topic_counts[m.topic] = topic_counts.get(m.topic, 0) + 1
    weak_topics = sorted(
        [{"topic": k, "count": v} for k, v in topic_counts.items()],
        key=lambda x: x["count"],
        reverse=True,
    )[:3]

    last_week_start = start - timedelta(days=7)
    last_total = 0
    for i in range(7):
        day = last_week_start + timedelta(days=i)
        day_next = day + timedelta(days=1)
        last_total += await _count_range(db, Homework, user_id, day, day_next)

    return {
        "week_start": week_start,
        "week_end": end.strftime("%Y-%m-%d"),
        "total_interactions": total,
        "words_learned": words_learned,
        "words_mastered": words_mastered,
        "mistakes_reviewed": reviewed,
        "daily_trend": daily_trend,
        "subject_dist": subject_dist,
        "weak_topics": weak_topics,
        "vs_last_week": {
            "interactions": total - last_total,
            "words": words_learned,
        },
    }


async def _count_range(
    db: AsyncSession, model, user_id: int, start: datetime, end: datetime, subject: str | None = None
) -> int:
    q = select(func.count()).select_from(model).where(
        model.user_id == user_id,
        model.created_at >= start,
        model.created_at < end,
    )
    if subject:
        q = q.where(model.subject == subject)
    result = await db.execute(q)
    return result.scalar() or 0


async def _get_mistakes_range(db: AsyncSession, user_id: int, start: datetime, end: datetime) -> list:
    result = await db.execute(
        select(Mistake).where(
            Mistake.user_id == user_id,
            Mistake.created_at >= start,
            Mistake.created_at < end,
        )
    )
    return list(result.scalars().all())
