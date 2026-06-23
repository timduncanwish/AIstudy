"""每日一练测试：答题计分 + AI 出题失败时抛 503 不落库空练习。"""
import json

import pytest
from fastapi import HTTPException

from app.services import practice_service
from app.services.practice_service import submit_practice, generate_daily_practice
from app.models.daily_practice import DailyPractice
from tests.conftest import make_user


async def _make_practice(db, user_id, questions):
    p = DailyPractice(
        user_id=user_id,
        subject="chinese",
        topic="拼音",
        questions_json=json.dumps(questions, ensure_ascii=False),
        total=len(questions),
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


async def test_submit_scores_correctly(db):
    user = await make_user(db)
    questions = [
        {"question": "q1", "options": ["a", "b"], "correct_index": 0, "explanation": ""},
        {"question": "q2", "options": ["a", "b"], "correct_index": 1, "explanation": ""},
        {"question": "q3", "options": ["a", "b"], "correct_index": 0, "explanation": ""},
    ]
    p = await _make_practice(db, user.id, questions)

    # 答案：对、错、对 → 得分 2
    result = await submit_practice(db, p.id, user.id, [0, 0, 0])

    assert result.score == 2
    assert result.total == 3


async def test_submit_handles_fewer_answers_than_questions(db):
    user = await make_user(db)
    questions = [
        {"question": "q1", "options": ["a", "b"], "correct_index": 0, "explanation": ""},
        {"question": "q2", "options": ["a", "b"], "correct_index": 1, "explanation": ""},
    ]
    p = await _make_practice(db, user.id, questions)

    # 只答了一题，不应越界
    result = await submit_practice(db, p.id, user.id, [0])
    assert result.score == 1


async def test_generate_raises_503_when_ai_returns_empty(db, monkeypatch):
    user = await make_user(db)

    async def _empty(*args, **kwargs):
        return []

    monkeypatch.setattr(practice_service, "_generate_questions", _empty)

    with pytest.raises(HTTPException) as exc:
        await generate_daily_practice(db, user.id, "chinese")
    assert exc.value.status_code == 503

    # 确认没有落库空练习
    from sqlalchemy import select, func
    count = (await db.execute(select(func.count()).select_from(DailyPractice))).scalar()
    assert count == 0
