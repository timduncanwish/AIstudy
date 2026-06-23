from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.config import DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        yield session


@asynccontextmanager
async def get_db_context():
    async with async_session() as session:
        yield session


async def init_db():
    from app.models import User, Homework, Mistake, WordProgress, DailyTask, UserStats, Student, ChatHistory, DailyPractice  # noqa: F401

    from sqlalchemy import text

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Add new columns to existing tables (idempotent ALTER TABLE)
        for stmt in [
            "ALTER TABLE users ADD COLUMN notify_subscribed INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN notify_time VARCHAR(5)",
            # 多孩子数据隔离：给学习数据表加 student_id
            "ALTER TABLE mistakes ADD COLUMN student_id INTEGER",
            "ALTER TABLE homework ADD COLUMN student_id INTEGER",
            "ALTER TABLE daily_practices ADD COLUMN student_id INTEGER",
            "ALTER TABLE chat_history ADD COLUMN student_id INTEGER",
        ]:
            try:
                await conn.execute(text(stmt))
            except Exception:
                pass  # column already exists

        # 回填：存量行归属到该 user 的活跃孩子（无活跃则取最早创建的孩子）
        for table in ("mistakes", "homework", "daily_practices", "chat_history"):
            try:
                await conn.execute(text(
                    f"UPDATE {table} SET student_id = ("
                    f"  SELECT s.id FROM students s WHERE s.user_id = {table}.user_id "
                    f"  ORDER BY s.is_active DESC, s.created_at ASC LIMIT 1"
                    f") WHERE student_id IS NULL"
                ))
            except Exception:
                pass
