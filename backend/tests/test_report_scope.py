"""每日报告聚合的多孩子作用域测试：只统计当前活跃孩子的数据。"""
from datetime import datetime

from app.services.report_service import get_daily_report
from app.models.homework import Homework
from app.models.chat_history import ChatHistory
from tests.conftest import make_user, make_student, make_mistake


async def _add_homework(db, user_id, student_id):
    db.add(Homework(user_id=user_id, student_id=student_id, subject="chinese",
                    image_url="x.jpg", status="done", created_at=datetime.now()))
    await db.commit()


async def _add_chat(db, user_id, student_id, role="user"):
    db.add(ChatHistory(user_id=user_id, student_id=student_id, session_id="s",
                       subject="chinese", grade=3, role=role, content="hi",
                       created_at=datetime.now()))
    await db.commit()


async def test_daily_report_counts_only_active_student(db):
    user = await make_user(db)
    s1 = await make_student(db, user.id, name="老大", is_active=True)
    s2 = await make_student(db, user.id, name="老二", is_active=False)

    # 活跃孩子(老大)：2作业 / 2错题 / 1对话
    await _add_homework(db, user.id, s1.id)
    await _add_homework(db, user.id, s1.id)
    await make_mistake(db, user.id, student_id=s1.id)
    await make_mistake(db, user.id, student_id=s1.id)
    await _add_chat(db, user.id, s1.id)
    # 非活跃孩子(老二)：1作业 / 1错题 / 1对话（不应计入）
    await _add_homework(db, user.id, s2.id)
    await make_mistake(db, user.id, student_id=s2.id)
    await _add_chat(db, user.id, s2.id)

    today = datetime.now().strftime("%Y-%m-%d")
    report = await get_daily_report(db, user.id, today)

    assert report["homework_count"] == 2
    assert report["mistakes_count"] == 2
    assert report["chat_count"] == 1
