"""测试基建：每个测试用独立的临时 SQLite 数据库，互不污染，也不碰真实库。

service 函数大多以 `db: AsyncSession` 为首参，可直接传入测试 session 测纯逻辑。
"""
import os
import tempfile

import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.database import Base
# 导入全部模型，确保 Base.metadata 完整
from app.models import (  # noqa: F401
    User, Homework, Mistake, WordProgress, DailyTask, UserStats,
    Student, ChatHistory, DailyPractice,
)


@pytest_asyncio.fixture
async def db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_async_engine(f"sqlite+aiosqlite:///{path}", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with Session() as session:
            yield session
    finally:
        await engine.dispose()
        os.remove(path)


async def make_user(db, *, nickname="家长", openid=None, notify_subscribed=0, device_id=None):
    import uuid
    user = User(
        device_id=device_id or f"dev_{uuid.uuid4().hex[:12]}",
        nickname=nickname,
        openid=openid,
        notify_subscribed=notify_subscribed,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def make_student(db, user_id, *, name="孩子", is_active=False):
    s = Student(user_id=user_id, name=name, is_active=is_active)
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


async def make_mistake(db, user_id, *, student_id=None, subject="chinese",
                       topic="拼音", mastery=0, review_count=0, next_review=None):
    from datetime import datetime
    m = Mistake(
        user_id=user_id,
        student_id=student_id,
        subject=subject,
        question_text="给汉字注音",
        correct_answer="bā",
        student_answer="bá",
        explanation="声调错了",
        topic=topic,
        mastery=mastery,
        review_count=review_count,
        next_review=next_review or datetime.now(),
    )
    db.add(m)
    await db.commit()
    await db.refresh(m)
    return m
