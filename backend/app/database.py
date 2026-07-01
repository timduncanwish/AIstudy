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
    from app.models import User, Homework, Mistake, WordProgress, DailyTask, UserStats, Student, ChatHistory, DailyPractice, PreviewProgress  # noqa: F401

    from sqlalchemy import text

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # user_stats 曾是 UNIQUE(user_id)（一人一行）；现按孩子分别记分，需要
        # 放开这个约束。SQLite 不支持直接 DROP 约束，只能重建表；只在检测到
        # 旧的 UNIQUE 索引时才做一次，全新安装/已迁移过的库这里是空操作。
        try:
            idx_result = await conn.execute(text("PRAGMA index_list('user_stats')"))
            has_legacy_unique = any(row[3] == "u" for row in idx_result.fetchall())
        except Exception:
            has_legacy_unique = False

        if has_legacy_unique:
            await conn.execute(text(
                "CREATE TABLE user_stats_new ("
                "id INTEGER NOT NULL PRIMARY KEY, "
                "user_id INTEGER NOT NULL, "
                "student_id INTEGER, "
                "total_points INTEGER, "
                "streak_days INTEGER, "
                "last_practice_date VARCHAR(10), "
                "words_mastered INTEGER, "
                "badges_json TEXT, "
                "created_at DATETIME, "
                "updated_at DATETIME, "
                "FOREIGN KEY(user_id) REFERENCES users (id), "
                "FOREIGN KEY(student_id) REFERENCES students (id)"
                ")"
            ))
            await conn.execute(text(
                "INSERT INTO user_stats_new "
                "(id, user_id, total_points, streak_days, last_practice_date, "
                " words_mastered, badges_json, created_at, updated_at) "
                "SELECT id, user_id, total_points, streak_days, last_practice_date, "
                "       words_mastered, badges_json, created_at, updated_at "
                "FROM user_stats"
            ))
            await conn.execute(text("DROP TABLE user_stats"))
            await conn.execute(text("ALTER TABLE user_stats_new RENAME TO user_stats"))

        # Add new columns to existing tables (idempotent ALTER TABLE)
        for stmt in [
            "ALTER TABLE users ADD COLUMN notify_subscribed INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN notify_time VARCHAR(5)",
            # 多孩子数据隔离：给学习数据表加 student_id
            "ALTER TABLE mistakes ADD COLUMN student_id INTEGER",
            "ALTER TABLE homework ADD COLUMN student_id INTEGER",
            "ALTER TABLE daily_practices ADD COLUMN student_id INTEGER",
            "ALTER TABLE chat_history ADD COLUMN student_id INTEGER",
            # 闯关/字词掌握度体系也按孩子隔离（原先只按 user 记，多孩子会共享一份积分/徽章）
            "ALTER TABLE word_progress ADD COLUMN student_id INTEGER",
            "ALTER TABLE daily_tasks ADD COLUMN student_id INTEGER",
            "ALTER TABLE user_stats ADD COLUMN student_id INTEGER",
            "ALTER TABLE users ADD COLUMN openid_hash VARCHAR(64)",
        ]:
            try:
                await conn.execute(text(stmt))
            except Exception:
                pass  # column already exists

        # 回填：存量行归属到该 user 的活跃孩子（无活跃则取最早创建的孩子）
        for table in (
            "mistakes", "homework", "daily_practices", "chat_history",
            "word_progress", "daily_tasks", "user_stats",
        ):
            try:
                await conn.execute(text(
                    f"UPDATE {table} SET student_id = ("
                    f"  SELECT s.id FROM students s WHERE s.user_id = {table}.user_id "
                    f"  ORDER BY s.is_active DESC, s.created_at ASC LIMIT 1"
                    f") WHERE student_id IS NULL"
                ))
            except Exception:
                pass
