"""迁移脚本测试：身份字段回填 + 内容加密 + 幂等 + dry-run。"""
import pytest
import pytest_asyncio
from sqlalchemy import text

from app.security import crypto
from scripts import migrate_encrypt


@pytest_asyncio.fixture
async def raw_conn(db):
    # 用 conftest 的临时库连接；插入明文行（绕 ORM）
    await db.execute(text(
        "INSERT INTO users (device_id, openid, nickname, grade, notify_subscribed) "
        "VALUES ('plain_device', 'plain_openid', '家长', 3, 0)"
    ))
    await db.commit()
    return db


async def test_default_backfills_identity(raw_conn):
    res = await migrate_encrypt.run(raw_conn, encrypt_content=False, dry_run=False)
    row = (await raw_conn.execute(text(
        "SELECT device_id, openid, openid_hash FROM users WHERE openid='plain_openid'"
    ))).first()
    assert row.device_id == crypto.hash_lookup("plain_device")
    assert row.openid_hash == crypto.hash_lookup("plain_openid")
    assert res["users"] >= 1


async def test_idempotent_second_run(raw_conn):
    await migrate_encrypt.run(raw_conn, encrypt_content=False, dry_run=False)
    before = (await raw_conn.execute(text(
        "SELECT device_id, openid_hash FROM users WHERE openid='plain_openid'"
    ))).first()
    await migrate_encrypt.run(raw_conn, encrypt_content=False, dry_run=False)
    after = (await raw_conn.execute(text(
        "SELECT device_id, openid_hash FROM users WHERE openid='plain_openid'"
    ))).first()
    assert before.device_id == after.device_id  # 不二次哈希
    assert before.openid_hash == after.openid_hash


async def test_dry_run_does_not_write(raw_conn):
    await migrate_encrypt.run(raw_conn, encrypt_content=False, dry_run=True)
    row = (await raw_conn.execute(text(
        "SELECT device_id FROM users WHERE openid='plain_openid'"
    ))).first()
    assert row.device_id == "plain_device"  # 仍是明文，未改


async def test_encrypt_content_encrypts_openid(raw_conn):
    # 先回填身份，再加密内容（脚本内部保证顺序）
    await migrate_encrypt.run(raw_conn, encrypt_content=True, dry_run=False)
    row = (await raw_conn.execute(text(
        "SELECT openid FROM users WHERE openid_hash=:h"
    ), {"h": crypto.hash_lookup("plain_openid")})).first()
    assert crypto.decrypt(row.openid) == "plain_openid"  # 已加密且可解
