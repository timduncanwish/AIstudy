import json
import re
from datetime import datetime, timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.daily_practice import DailyPractice
from app.models.mistake import Mistake
from app.models.user import User
from app.services.ai_service import _client
from app.config import ZHIPU_MODEL
from app.scope import active_student_id


async def get_weakest_topic(db: AsyncSession, user_id: int, subject: str) -> dict | None:
    sid = await active_student_id(db, user_id)
    student_conds = [Mistake.student_id == sid] if sid is not None else []
    stmt = (
        select(
            Mistake.topic,
            func.count().label("count"),
            func.avg(Mistake.mastery).label("avg_mastery"),
        )
        .where(
            Mistake.user_id == user_id,
            *student_conds,
            Mistake.subject == subject,
            Mistake.topic != "",
            Mistake.topic.isnot(None),
        )
        .group_by(Mistake.topic)
        .order_by(func.avg(Mistake.mastery).asc())
        .limit(1)
    )
    row = (await db.execute(stmt)).first()
    if not row:
        return None
    return {"topic": row[0], "count": row[1], "avg_mastery": float(row[2])}


async def generate_daily_practice(
    db: AsyncSession, user_id: int, subject: str
) -> DailyPractice:
    weak = await get_weakest_topic(db, user_id, subject)
    if weak:
        topic = weak["topic"]
        context_mistakes = await _get_weak_mistakes(db, user_id, subject, topic)
    else:
        topic = "综合练习"
        context_mistakes = []

    questions = await _generate_questions(subject, topic, context_mistakes)

    sid = await active_student_id(db, user_id)
    practice = DailyPractice(
        user_id=user_id,
        student_id=sid,
        subject=subject,
        topic=topic,
        questions_json=json.dumps(questions, ensure_ascii=False),
        total=len(questions),
    )
    db.add(practice)
    await db.commit()
    await db.refresh(practice)
    return practice


async def _get_weak_mistakes(
    db: AsyncSession, user_id: int, subject: str, topic: str, limit: int = 3
) -> list[Mistake]:
    sid = await active_student_id(db, user_id)
    student_conds = [Mistake.student_id == sid] if sid is not None else []
    stmt = (
        select(Mistake)
        .where(Mistake.user_id == user_id, *student_conds, Mistake.subject == subject, Mistake.topic == topic)
        .order_by(Mistake.mastery.asc())
        .limit(limit)
    )
    return list((await db.execute(stmt)).scalars().all())


async def _generate_questions(
    subject: str, topic: str, context_mistakes: list[Mistake]
) -> list[dict]:
    context = ""
    if context_mistakes:
        parts = []
        for m in context_mistakes:
            parts.append(f"题目: {m.question_text}\n正确答案: {m.correct_answer}\n学生错误: {m.student_answer}")
        context = f"\n\n学生相关错题:\n" + "\n\n".join(parts)

    if subject == "chinese":
        prompt = (
            f"你是小学语文老师。请生成5道选择题，知识点范围: {topic}。"
            f"题目要有趣味性，适合3-6年级学生。{context}\n"
            f"直接返回JSON数组: [{{\"question\": \"题目\", \"options\": [\"A\", \"B\", \"C\", \"D\"], "
            f"\"correct_index\": 0-3, \"explanation\": \"解析\"}}]\n"
            f"不要markdown标记。"
        )
    else:
        prompt = (
            f"You are an elementary English teacher. Generate 5 multiple choice questions about: {topic}. "
            f"Fun and suitable for grades 3-6.{context}\n"
            f"Return raw JSON array: [{{\"question\": \"...\", \"options\": [\"A\", \"B\", \"C\", \"D\"], "
            f"\"correct_index\": 0-3, \"explanation\": \"...in Chinese...\"}}]\n"
            f"No markdown."
        )

    response = await _client.chat.completions.create(
        model=ZHIPU_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1500,
        temperature=0.7,
    )
    text = response.choices[0].message.content

    cleaned = re.sub(r'```json\s*', '', text)
    cleaned = re.sub(r'```\s*', '', cleaned).strip()
    arr_match = re.search(r'\[[\s\S]*\]', cleaned)
    if arr_match:
        try:
            return json.loads(arr_match.group())
        except json.JSONDecodeError:
            pass
    return []


async def submit_practice(
    db: AsyncSession, practice_id: int, user_id: int, answers: list[int]
) -> DailyPractice:
    stmt = select(DailyPractice).where(
        DailyPractice.id == practice_id, DailyPractice.user_id == user_id
    )
    practice = (await db.execute(stmt)).scalar_one_or_none()
    if not practice:
        return None

    questions = json.loads(practice.questions_json)
    score = sum(
        1 for i, ans in enumerate(answers)
        if i < len(questions) and ans == questions[i].get("correct_index")
    )

    practice.answers_json = json.dumps(answers)
    practice.score = score
    await db.commit()
    await db.refresh(practice)

    # 即时通知家长
    try:
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if user and user.notify_subscribed and user.openid:
            from app.services.notify_service import notify_practice_done
            await notify_practice_done(
                openid=user.openid,
                subject=practice.subject,
                topic=practice.topic or "综合练习",
                score=score,
                total=practice.total,
            )
    except Exception:
        pass  # 通知失败不影响主流程

    return practice


async def get_practice_history(
    db: AsyncSession, user_id: int, limit: int = 30
) -> dict:
    sid = await active_student_id(db, user_id)
    student_conds = [DailyPractice.student_id == sid] if sid is not None else []
    stmt = (
        select(DailyPractice)
        .where(DailyPractice.user_id == user_id, *student_conds, DailyPractice.score.isnot(None))
        .order_by(DailyPractice.created_at.desc())
        .limit(limit)
    )
    items = list((await db.execute(stmt)).scalars().all())

    streak = 0
    if items:
        today = datetime.now().date()
        practice_dates = set()
        for item in items:
            practice_dates.add(item.created_at.date())

        check = today
        while check in practice_dates:
            streak += 1
            check -= timedelta(days=1)

    return {"items": items, "streak": streak}
