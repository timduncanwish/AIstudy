"""验证 init_db() 能把"迁移前"的旧库安全升级成按孩子隔离闯关数据的新库。

背景：user_stats 曾是 UNIQUE(user_id)（一人一行），SQLite 不支持直接 DROP
约束，database.py 的 init_db() 检测到这个旧约束时会做一次表重建（保留数据）。
这里手工搭一个"迁移前"的旧库（真实的 UNIQUE(user_id) 约束、没有 student_id
列），跑一遍真正的 init_db()，确认：
1. 旧数据（积分/徽章）没丢；
2. 旧行被回填到正确的孩子（唯一/活跃的那个）；
3. 旧的 UNIQUE(user_id) 约束被拆掉，同一个 user 现在能有第二个孩子的统计行。
"""
import os
import tempfile

import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app import database as database_module


@pytest_asyncio.fixture
async def legacy_db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    engine = create_async_engine(f"sqlite+aiosqlite:///{path}", echo=False)
    async with engine.begin() as conn:
        await conn.execute(text(
            "CREATE TABLE users ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, device_id VARCHAR(255) UNIQUE NOT NULL, "
            "openid VARCHAR(255), openid_hash VARCHAR(64), nickname VARCHAR(255), "
            "avatar_url VARCHAR(255), grade INTEGER, notify_subscribed INTEGER DEFAULT 0, "
            "notify_time VARCHAR(5), created_at DATETIME)"
        ))
        await conn.execute(text(
            "CREATE TABLE students ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, "
            "name VARCHAR(255) NOT NULL, grade INTEGER, avatar_tag VARCHAR(10), "
            "is_active BOOLEAN, created_at DATETIME)"
        ))
        # 旧版 user_stats：一人一行，UNIQUE(user_id)，没有 student_id 列
        await conn.execute(text(
            "CREATE TABLE user_stats ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL UNIQUE, "
            "total_points INTEGER, streak_days INTEGER, last_practice_date VARCHAR(10), "
            "words_mastered INTEGER, badges_json TEXT, created_at DATETIME, updated_at DATETIME)"
        ))
        await conn.execute(text(
            "INSERT INTO users (id, device_id, nickname, created_at) "
            "VALUES (1, 'wx_legacy_user', '家长', datetime('now'))"
        ))
        await conn.execute(text(
            "INSERT INTO students (id, user_id, name, grade, is_active, created_at) "
            "VALUES (1, 1, '哥哥', 3, 1, datetime('now'))"
        ))
        await conn.execute(text(
            "INSERT INTO user_stats "
            "(id, user_id, total_points, streak_days, words_mastered, badges_json, created_at, updated_at) "
            "VALUES (1, 1, 42, 3, 5, '[\"first_word\"]', datetime('now'), datetime('now'))"
        ))
    await engine.dispose()

    try:
        yield path
    finally:
        os.remove(path)


async def test_init_db_rebuilds_legacy_user_stats_and_preserves_data(legacy_db_path, monkeypatch):
    engine = create_async_engine(f"sqlite+aiosqlite:///{legacy_db_path}", echo=False)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(database_module, "engine", engine)
    monkeypatch.setattr(database_module, "async_session", session_maker)

    await database_module.init_db()

    async with engine.connect() as conn:
        idx_result = await conn.execute(text("PRAGMA index_list('user_stats')"))
        assert not any(row[3] == "u" for row in idx_result.fetchall()), "旧的 UNIQUE(user_id) 约束应该被拆掉"

        row = (await conn.execute(text(
            "SELECT user_id, student_id, total_points, badges_json FROM user_stats WHERE id = 1"
        ))).first()
        assert row.user_id == 1
        assert row.student_id == 1  # 回填到唯一的孩子
        assert row.total_points == 42  # 旧数据没丢
        assert row.badges_json == '["first_word"]'

    await engine.dispose()


async def test_init_db_allows_second_childs_stats_row_after_migration(legacy_db_path, monkeypatch):
    engine = create_async_engine(f"sqlite+aiosqlite:///{legacy_db_path}", echo=False)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(database_module, "engine", engine)
    monkeypatch.setattr(database_module, "async_session", session_maker)

    await database_module.init_db()

    async with engine.begin() as conn:
        # 迁移前这一步会因 UNIQUE(user_id) 报 IntegrityError；迁移后应该能成功
        await conn.execute(text(
            "INSERT INTO user_stats "
            "(user_id, student_id, total_points, streak_days, words_mastered, badges_json, created_at, updated_at) "
            "VALUES (1, 2, 0, 0, 0, '[]', datetime('now'), datetime('now'))"
        ))
        count = (await conn.execute(text(
            "SELECT COUNT(*) FROM user_stats WHERE user_id = 1"
        ))).scalar()
        assert count == 2

    await engine.dispose()
