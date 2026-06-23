from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.mistake import Mistake
from app.scope import active_student_id


def _scope(user_id: int, student_id: int | None):
    """返回错题作用域条件：user 级 + （若有活跃孩子）student 级。"""
    conds = [Mistake.user_id == user_id]
    if student_id is not None:
        conds.append(Mistake.student_id == student_id)
    return conds


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
    sid = await active_student_id(db, user_id)
    query = select(Mistake).where(*_scope(user_id, sid))
    count_query = select(func.count()).select_from(Mistake).where(*_scope(user_id, sid))

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
    sid = await active_student_id(db, user_id)
    result = await db.execute(
        select(Mistake).where(Mistake.id == mistake_id, *_scope(user_id, sid))
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
    sid = await active_student_id(db, user_id)
    query = (
        select(Mistake)
        .where(*_scope(user_id, sid), Mistake.subject == subject)
        .order_by(Mistake.mastery.asc(), Mistake.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_mistake_stats(db: AsyncSession, user_id: int) -> dict:
    sid = await active_student_id(db, user_id)
    scope = _scope(user_id, sid)
    total_q = select(func.count()).select_from(Mistake).where(*scope)
    mastered_q = select(func.count()).select_from(Mistake).where(
        *scope, Mistake.mastery >= 4
    )
    reviewing_q = select(func.count()).select_from(Mistake).where(
        *scope, Mistake.mastery >= 1, Mistake.mastery <= 3
    )
    new_q = select(func.count()).select_from(Mistake).where(
        *scope, Mistake.mastery == 0
    )

    topic_q = (
        select(Mistake.topic, func.count().label("count"), func.avg(Mistake.mastery).label("avg_mastery"))
        .where(*scope, Mistake.topic != "", Mistake.topic.isnot(None))
        .group_by(Mistake.topic)
        .order_by(func.count().desc())
        .limit(10)
    )

    subject_q = (
        select(Mistake.subject, func.count().label("count"))
        .where(*scope)
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


async def get_knowledge_map(db: AsyncSession, user_id: int) -> dict:
    sid = await active_student_id(db, user_id)
    stmt = (
        select(
            Mistake.subject,
            Mistake.topic,
            func.count().label("count"),
            func.avg(Mistake.mastery).label("avg_mastery"),
            func.max(Mistake.created_at).label("latest"),
        )
        .where(*_scope(user_id, sid), Mistake.topic != "", Mistake.topic.isnot(None))
        .group_by(Mistake.subject, Mistake.topic)
        .order_by(Mistake.subject, func.count().desc())
    )
    rows = (await db.execute(stmt)).all()

    subjects: dict[str, list[dict]] = {}
    for r in rows:
        subjects.setdefault(r[0], []).append({
            "topic": r[1],
            "subject": r[0],
            "count": r[2],
            "avg_mastery": round(float(r[3]), 1),
            "latest_mistake_at": str(r[4]),
        })
    return {"subjects": subjects}


async def get_topic_detail(
    db: AsyncSession, user_id: int, subject: str, topic: str
) -> dict | None:
    sid = await active_student_id(db, user_id)
    scope = _scope(user_id, sid)
    avg_stmt = select(
        func.count().label("count"),
        func.avg(Mistake.mastery).label("avg_mastery"),
    ).where(
        *scope,
        Mistake.subject == subject,
        Mistake.topic == topic,
    )
    row = (await db.execute(avg_stmt)).one()
    if not row or row[0] == 0:
        return None

    stmt = (
        select(Mistake)
        .where(*scope, Mistake.subject == subject, Mistake.topic == topic)
        .order_by(Mistake.mastery.asc(), Mistake.created_at.desc())
    )
    mistakes = list((await db.execute(stmt)).scalars().all())

    return {
        "topic": topic,
        "subject": subject,
        "count": row[0],
        "avg_mastery": round(float(row[1]), 1),
        "mistakes": mistakes,
    }


async def generate_practice_questions(
    db: AsyncSession, user_id: int, subject: str, topic: str
) -> list[dict]:
    detail = await get_topic_detail(db, user_id, subject, topic)
    if not detail:
        return []

    weak_mistakes = [m for m in detail["mistakes"] if m.mastery <= 3][:3]
    if not weak_mistakes:
        weak_mistakes = detail["mistakes"][:3]

    context_parts = []
    for m in weak_mistakes:
        context_parts.append(
            f"题目: {m.question_text}\n正确答案: {m.correct_answer}\n学生错误答案: {m.student_answer}"
        )
    context = "\n\n".join(context_parts)

    from app.services.ai_service import _client
    from app.config import ZHIPU_MODEL

    if subject == "chinese":
        prompt = (
            f"你是一位小学语文老师。学生以下题目做错了，请根据这些错题生成3道类似但不同的练习题。\n"
            f"知识点: {topic}\n\n"
            f"学生错题:\n{context}\n\n"
            f"直接返回JSON数组，每项格式: {{\"question\": \"题目\", \"options\": [\"A选项\", \"B选项\", \"C选项\", \"D选项\"], "
            f"\"correct_index\": 正确选项索引(0-3), \"explanation\": \"解析\"}}\n"
            f"不要加markdown标记。"
        )
    else:
        prompt = (
            f"You are an elementary English teacher. The student got these questions wrong. "
            f"Generate 3 similar but different practice questions.\n"
            f"Topic: {topic}\n\n"
            f"Student mistakes:\n{context}\n\n"
            f"Return a raw JSON array. Each item: {{\"question\": \"...\", \"options\": [\"A\", \"B\", \"C\", \"D\"], "
            f"\"correct_index\": 0-3, \"explanation\": \"...in Chinese...\"}}\n"
            f"No markdown."
        )

    response = await _client.chat.completions.create(
        model=ZHIPU_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1024,
        temperature=0.7,
    )
    text = response.choices[0].message.content

    import json, re
    cleaned = re.sub(r'```json\s*', '', text)
    cleaned = re.sub(r'```\s*', '', cleaned).strip()
    arr_match = re.search(r'\[[\s\S]*\]', cleaned)
    if arr_match:
        try:
            return json.loads(arr_match.group())
        except json.JSONDecodeError:
            pass
    return []
