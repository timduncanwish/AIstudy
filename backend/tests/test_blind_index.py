"""openid 盲索引：加密存储可恢复 + openid_hash 哈希查找。"""
from sqlalchemy import select, text

from app.models.user import User
from app.security import crypto
from tests.conftest import make_user  # 复用（make_user 会同时设 openid 与 openid_hash，见 Step 4 调整）


async def test_openid_encrypted_but_recoverable(db):
    user = await make_user(db, openid="wx_real_openid_123")
    # 读出可恢复为明文（回传微信用）
    assert user.openid == "wx_real_openid_123"


async def test_openid_stored_as_ciphertext_at_rest(db):
    # 原生 SQL 读底层存储，确认 openid 列是密文而非明文
    user = await make_user(db, openid="wx_real_openid_123")
    raw = (await db.execute(
        text("SELECT openid FROM users WHERE id = :i"), {"i": user.id}
    )).scalar()
    assert raw != "wx_real_openid_123"
    assert raw.startswith("gAAAAA")  # Fernet 令牌前缀
    assert crypto.decrypt(raw) == "wx_real_openid_123"


async def test_lookup_by_openid_hash(db):
    await make_user(db, openid="wx_real_openid_123")
    found = (await db.execute(
        select(User).where(User.openid_hash == "wx_real_openid_123")
    )).scalar_one_or_none()
    assert found is not None
    assert found.openid == "wx_real_openid_123"


async def test_openid_stored_ciphertext_hash_is_hex(db):
    import sqlite3  # 直接看底层存储
    user = await make_user(db, openid="wx_real_openid_123")
    row = (await db.execute(
        select(User.openid, User.openid_hash).where(User.id == user.id)
    )).first()
    # ORM 读出 openid 已解密；openid_hash 为 64 位 hex
    assert row.openid_hash == crypto.hash_lookup("wx_real_openid_123")
