# 儿童数据加密与合规 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为最敏感字段加字段级透明加密——身份字段 HMAC 哈希（盲索引）、内容字段 Fernet 可逆加密，业务代码几乎不改，渐进迁移不停机。

**Architecture:** `app/security/crypto.py` 提供 `encrypt/decrypt`（MultiFernet，支持密钥轮换）与 `hash_lookup`（HMAC）。`app/security/types.py` 提供两个 SQLAlchemy TypeDecorator（`EncryptedText` 读时容错、`HashedKey` 写读都哈希且幂等）。openid 用盲索引（加密存 + `openid_hash` 哈希列查找），device_id 直接哈希。一次性迁移脚本回填查找字段。

**Tech Stack:** FastAPI、SQLAlchemy 2.0、cryptography（Fernet/MultiFernet）、Python stdlib hmac/hashlib、pytest。

## Global Constraints

- 测试运行：`cd backend && PYTHONPATH="venv_local;." python -m pytest`（Windows 分隔符 `;`）。
- `EncryptedText` 读时必须容错：解密失败返回原值（老明文照读）——支持渐进迁移。
- `HashedKey` 必须幂等：值已是 64 位小写 hex 则不再哈希（消除往返二次哈希、兼作迁移幂等判据）。
- openid 必须可恢复（回传微信推送 `touser=openid`）；查找走 `openid_hash` 盲索引。
- `openid` 列去掉 `unique`（Fernet 非确定性，密文唯一约束无意义）；唯一性由 `openid_hash`（确定性哈希）承担。
- 密钥变更会使所有密文不可解、所有哈希失配——生产须设固定 `DATA_ENCRYPTION_KEY`。
- commit 信息用中文；不改前端。

---

### Task 1: 加密原语 `crypto.py`（含依赖与配置）

**Files:**
- Modify: `backend/requirements.txt`（追加 cryptography）
- Modify: `backend/app/config.py`（追加 DATA_ENCRYPTION_KEY）
- Create: `backend/app/security/__init__.py`（空文件）
- Create: `backend/app/security/crypto.py`
- Test: `backend/tests/test_crypto.py`

**Interfaces:**
- Consumes: `app.config.DATA_ENCRYPTION_KEY`（str，默认 ""）、`app.config.JWT_SECRET`
- Produces: `crypto.encrypt(text:str)->str`、`crypto.decrypt(token:str)->str`（非法抛 `cryptography.fernet.InvalidToken`）、`crypto.hash_lookup(text:str)->str`（64 位 hex）

- [ ] **Step 1: 装依赖并登记**

```bash
cd backend && python -m pip install --target venv_local cryptography --quiet --disable-pip-version-check
```
在 `backend/requirements.txt` 末尾追加一行：
```
cryptography==49.0.0
```

- [ ] **Step 2: 加配置项**

在 `backend/app/config.py` 的 `JWT_SECRET = os.getenv(...)` 行之后追加：
```python
# 数据加密密钥（逗号分隔支持轮换：第一个加密、全部解密）。不设则从 JWT_SECRET 派生
DATA_ENCRYPTION_KEY = os.getenv("DATA_ENCRYPTION_KEY", "")
```

- [ ] **Step 3: 写失败测试**

创建 `backend/tests/test_crypto.py`：
```python
"""加密原语测试。"""
import re

import pytest
from cryptography.fernet import InvalidToken

from app.security import crypto


def test_encrypt_decrypt_roundtrip():
    for s in ["小明的作业", "hello", ""]:
        assert crypto.decrypt(crypto.encrypt(s)) == s


def test_encrypt_is_not_plaintext():
    token = crypto.encrypt("小明")
    assert "小明" not in token


def test_decrypt_invalid_raises():
    with pytest.raises(InvalidToken):
        crypto.decrypt("not-a-valid-token")


def test_hash_lookup_deterministic_and_hex():
    h = crypto.hash_lookup("wx_openid_abc")
    assert h == crypto.hash_lookup("wx_openid_abc")
    assert re.fullmatch(r"[0-9a-f]{64}", h)
    assert crypto.hash_lookup("a") != crypto.hash_lookup("b")


def test_rotation_old_key_still_decrypts(monkeypatch):
    # 用旧密钥加密的令牌，在「新,旧」多密钥下仍可解
    from cryptography.fernet import Fernet
    old_key = Fernet.generate_key()
    new_key = Fernet.generate_key()
    old_token = Fernet(old_key).encrypt("历史数据".encode()).decode()

    monkeypatch.setattr(crypto, "_multi", crypto._build_multifernet(
        [new_key.decode(), old_key.decode()]
    ))
    assert crypto.decrypt(old_token) == "历史数据"
```

- [ ] **Step 4: 运行测试确认失败**

Run: `cd backend && PYTHONPATH="venv_local;." python -m pytest tests/test_crypto.py -q`
Expected: FAIL（`ModuleNotFoundError: app.security.crypto`）

- [ ] **Step 5: 实现 crypto.py**

创建 `backend/app/security/__init__.py`（空）。创建 `backend/app/security/crypto.py`：
```python
"""数据加密原语：Fernet 可逆加密（支持密钥轮换）+ HMAC 不可逆哈希。"""
import base64
import hashlib
import hmac

from cryptography.fernet import Fernet, MultiFernet

from app.config import DATA_ENCRYPTION_KEY, JWT_SECRET


def _derive_fernet_key(secret: str) -> bytes:
    return base64.urlsafe_b64encode(hashlib.sha256(("fernet:" + secret).encode()).digest())


def _build_multifernet(keys: list[str]) -> MultiFernet:
    return MultiFernet([Fernet(k.encode() if isinstance(k, str) else k) for k in keys])


# 密钥来源：DATA_ENCRYPTION_KEY（逗号分隔）首段为主密钥；未设则从 JWT_SECRET 派生
if DATA_ENCRYPTION_KEY.strip():
    _keys = [k.strip() for k in DATA_ENCRYPTION_KEY.split(",") if k.strip()]
    _primary_secret = _keys[0]
else:
    _keys = [_derive_fernet_key(JWT_SECRET).decode()]
    _primary_secret = JWT_SECRET

_multi = _build_multifernet(_keys)
_hmac_key = hashlib.sha256(("hmac:" + _primary_secret).encode()).digest()


def encrypt(text: str) -> str:
    return _multi.encrypt(text.encode("utf-8")).decode("ascii")


def decrypt(token: str) -> str:
    return _multi.decrypt(token.encode("ascii")).decode("utf-8")


def hash_lookup(text: str) -> str:
    return hmac.new(_hmac_key, text.encode("utf-8"), hashlib.sha256).hexdigest()
```

- [ ] **Step 6: 运行测试确认通过**

Run: `cd backend && PYTHONPATH="venv_local;." python -m pytest tests/test_crypto.py -q`
Expected: PASS（5 passed）

- [ ] **Step 7: 提交**

```bash
git add backend/requirements.txt backend/app/config.py backend/app/security/__init__.py backend/app/security/crypto.py backend/tests/test_crypto.py
git commit -m "feat: 新增加密原语 crypto（Fernet可逆加密+HMAC哈希+密钥轮换）"
```

---

### Task 2: TypeDecorators `types.py`

**Files:**
- Create: `backend/app/security/types.py`
- Test: `backend/tests/test_encrypted_types.py`

**Interfaces:**
- Consumes: `crypto.encrypt/decrypt/hash_lookup`（Task 1）
- Produces: `EncryptedText`（SQLAlchemy TypeDecorator）、`HashedKey`（TypeDecorator，构造接受长度）

- [ ] **Step 1: 写失败测试**

创建 `backend/tests/test_encrypted_types.py`：
```python
"""TypeDecorator 单元测试：直接测 bind/result 处理逻辑。"""
from app.security.types import EncryptedText, HashedKey
from app.security import crypto


def test_encrypted_text_bind_then_result_roundtrip():
    t = EncryptedText()
    stored = t.process_bind_param("小明的对话", None)
    assert stored is not None and "小明的对话" not in stored
    assert t.process_result_value(stored, None) == "小明的对话"


def test_encrypted_text_none_passthrough():
    t = EncryptedText()
    assert t.process_bind_param(None, None) is None
    assert t.process_result_value(None, None) is None


def test_encrypted_text_tolerates_legacy_plaintext():
    t = EncryptedText()
    # 老明文（非合法令牌）读出原样返回
    assert t.process_result_value("老明文内容", None) == "老明文内容"


def test_hashed_key_hashes_on_bind():
    k = HashedKey(64)
    stored = k.process_bind_param("wx_openid_abc", None)
    assert stored == crypto.hash_lookup("wx_openid_abc")
    assert k.process_result_value(stored, None) == stored  # 读出即哈希


def test_hashed_key_idempotent_on_existing_hash():
    k = HashedKey(64)
    once = k.process_bind_param("wx_openid_abc", None)
    twice = k.process_bind_param(once, None)  # 已是 64 位 hex，不再哈希
    assert twice == once


def test_hashed_key_none_passthrough():
    k = HashedKey(64)
    assert k.process_bind_param(None, None) is None
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && PYTHONPATH="venv_local;." python -m pytest tests/test_encrypted_types.py -q`
Expected: FAIL（`ModuleNotFoundError: app.security.types`）

- [ ] **Step 3: 实现 types.py**

创建 `backend/app/security/types.py`：
```python
"""SQLAlchemy 透明加密列类型。"""
import re

from sqlalchemy import String, Text
from sqlalchemy.types import TypeDecorator
from cryptography.fernet import InvalidToken

from app.security import crypto

_HEX64 = re.compile(r"[0-9a-f]{64}")


class EncryptedText(TypeDecorator):
    """写时 Fernet 加密、读时解密；解密失败返回原值（容错老明文）。"""
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return crypto.encrypt(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        try:
            return crypto.decrypt(value)
        except InvalidToken:
            return value


class HashedKey(TypeDecorator):
    """写入与查询比较都做 HMAC 哈希（透明匹配）；幂等：已是 64 位 hex 则不再哈希。"""
    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if _HEX64.fullmatch(value):
            return value
        return crypto.hash_lookup(value)

    def process_result_value(self, value, dialect):
        return value
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && PYTHONPATH="venv_local;." python -m pytest tests/test_encrypted_types.py -q`
Expected: PASS（6 passed）

- [ ] **Step 5: 提交**

```bash
git add backend/app/security/types.py backend/tests/test_encrypted_types.py
git commit -m "feat: 新增透明加密列类型 EncryptedText / HashedKey（含容错与幂等）"
```

---

### Task 3: 应用到模型 + 盲索引 + init_db 迁移

**Files:**
- Modify: `backend/app/models/user.py`
- Modify: `backend/app/models/student.py:14`
- Modify: `backend/app/models/chat_history.py`（import + 第16行 content）
- Modify: `backend/app/models/mistake.py`（import + 17-20 行）
- Modify: `backend/app/services/auth_service.py`（wx_login 查找改盲索引）
- Modify: `backend/app/database.py`（init_db 加 openid_hash 列）
- Test: `backend/tests/test_blind_index.py`

**Interfaces:**
- Consumes: `EncryptedText`、`HashedKey`（Task 2）
- Produces: `User.openid_hash`（HashedKey 列）；`wx_login` 按 openid_hash 查找

- [ ] **Step 1: 写失败测试**

创建 `backend/tests/test_blind_index.py`：
```python
"""openid 盲索引：加密存储可恢复 + openid_hash 哈希查找。"""
from sqlalchemy import select

from app.models.user import User
from app.security import crypto
from tests.conftest import make_user  # 复用（make_user 会同时设 openid 与 openid_hash，见 Step 4 调整）


async def test_openid_encrypted_but_recoverable(db):
    user = await make_user(db, openid="wx_real_openid_123")
    # 读出可恢复为明文（回传微信用）
    assert user.openid == "wx_real_openid_123"


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
```

> 该测试依赖 conftest 的 `make_user` 同时设置 `openid` 与 `openid_hash`。Step 4 调整 conftest。

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && PYTHONPATH="venv_local;." python -m pytest tests/test_blind_index.py -q`
Expected: FAIL（`AttributeError: openid_hash` 或 conftest 未设 openid_hash）

- [ ] **Step 3: 改模型**

`backend/app/models/user.py`：替换 import 与 openid/device_id 行，新增 openid_hash：
```python
from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.security.types import EncryptedText, HashedKey
```
把
```python
    device_id = mapped_column(String(64), unique=True, nullable=False)
    openid = mapped_column(String(100), unique=True, nullable=True)
```
改为
```python
    device_id = mapped_column(HashedKey(64), unique=True, nullable=False)
    openid = mapped_column(EncryptedText, nullable=True)  # 可恢复，回传微信
    openid_hash = mapped_column(HashedKey(64), unique=True, nullable=True, index=True)  # 盲索引
```

`backend/app/models/student.py`：import 加 `from app.security.types import EncryptedText`，把
`name = mapped_column(String(50), nullable=False)` 改为
`name = mapped_column(EncryptedText, nullable=False)`。

`backend/app/models/chat_history.py`：import 加 `from app.security.types import EncryptedText`，把
`content = Column(Text, nullable=False)` 改为 `content = Column(EncryptedText, nullable=False)`。

`backend/app/models/mistake.py`：import 加 `from app.security.types import EncryptedText`，把 17-20 行改为：
```python
    question_text = mapped_column(EncryptedText, nullable=False)
    correct_answer = mapped_column(EncryptedText, nullable=False)
    student_answer = mapped_column(EncryptedText, nullable=True)
    explanation = mapped_column(EncryptedText, nullable=True)
```

- [ ] **Step 4: 改 wx_login、init_db、conftest**

`backend/app/services/auth_service.py` 的 `wx_login`：把
```python
    result = await db.execute(select(User).where(User.openid == openid))
```
改为
```python
    result = await db.execute(select(User).where(User.openid_hash == openid))
```
并在创建 User 处（`user = User(device_id=device_id, openid=openid, ...)`）增加 `openid_hash=openid`：
```python
        user = User(
            device_id=device_id,
            openid=openid,
            openid_hash=openid,
            ...
        )
```
（保持原有其它字段不变，只新增 `openid_hash=openid` 一行。）

`backend/app/database.py` 的 `init_db` 幂等 ALTER 列表中追加一条：
```python
            "ALTER TABLE users ADD COLUMN openid_hash VARCHAR(64)",
```

`backend/tests/conftest.py` 的 `make_user`：在 `User(...)` 构造里把 openid 同时写入 openid_hash。
把
```python
    user = User(
        device_id=device_id or f"dev_{uuid.uuid4().hex[:12]}",
        nickname=nickname,
        openid=openid,
        notify_subscribed=notify_subscribed,
    )
```
改为
```python
    user = User(
        device_id=device_id or f"dev_{uuid.uuid4().hex[:12]}",
        nickname=nickname,
        openid=openid,
        openid_hash=openid,
        notify_subscribed=notify_subscribed,
    )
```

- [ ] **Step 5: 运行新测试 + 全套回归**

Run: `cd backend && PYTHONPATH="venv_local;." python -m pytest tests/test_blind_index.py -q`
Expected: PASS（3 passed）

Run: `cd backend && PYTHONPATH="venv_local;." python -m pytest -q`
Expected: PASS（既有全套 + 新增，全绿）

> 若既有用例因 openid 透明加密失败，多半是断言了底层存储格式——按"读出为明文"修正断言，不要回退加密。

- [ ] **Step 6: 提交**

```bash
git add backend/app/models/ backend/app/services/auth_service.py backend/app/database.py backend/tests/conftest.py backend/tests/test_blind_index.py
git commit -m "feat: 敏感字段透明加密 + openid 盲索引（device_id哈希）"
```

---

### Task 4: 渐进迁移脚本

**Files:**
- Create: `backend/scripts/__init__.py`（空）
- Create: `backend/scripts/migrate_encrypt.py`
- Test: `backend/tests/test_migrate_encrypt.py`

**Interfaces:**
- Consumes: `crypto.encrypt/hash_lookup`（Task 1）、`app.database`
- Produces: `migrate_encrypt.run(conn, *, encrypt_content: bool, dry_run: bool) -> dict`（返回各表计数）

- [ ] **Step 1: 写失败测试**

创建 `backend/tests/test_migrate_encrypt.py`：
```python
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
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && PYTHONPATH="venv_local;." python -m pytest tests/test_migrate_encrypt.py -q`
Expected: FAIL（`ModuleNotFoundError: scripts.migrate_encrypt`）

- [ ] **Step 3: 实现迁移脚本**

创建 `backend/scripts/__init__.py`（空）。创建 `backend/scripts/migrate_encrypt.py`：
```python
"""渐进加密迁移：默认回填查找字段（device_id 哈希、openid_hash 盲索引）；
--encrypt-content 额外加密存量内容。走原生 SQL，幂等，可 --dry-run。

用法：
    cd backend && PYTHONPATH="venv_local;." python -m scripts.migrate_encrypt [--encrypt-content] [--dry-run]
运行前请先备份数据库。
"""
import argparse
import asyncio
import re

from sqlalchemy import text

from app.database import get_db_context
from app.security import crypto

_HEX64 = re.compile(r"[0-9a-f]{64}")

# 内容字段：(表, 主键, [列...])
_CONTENT = [
    ("students", "id", ["name"]),
    ("chat_history", "id", ["content"]),
    ("mistakes", "id", ["question_text", "correct_answer", "student_answer", "explanation"]),
    ("users", "id", ["openid"]),
]


def _is_encrypted(v: str) -> bool:
    if v is None:
        return False
    try:
        crypto.decrypt(v)
        return True
    except Exception:
        return False


async def run(conn, *, encrypt_content: bool, dry_run: bool) -> dict:
    counts = {}

    # 1) 查找字段（必跑）：device_id 哈希、openid_hash 回填
    rows = (await conn.execute(text("SELECT id, device_id, openid, openid_hash FROM users"))).all()
    n = 0
    for r in rows:
        updates = {}
        if r.device_id and not _HEX64.fullmatch(r.device_id):
            updates["device_id"] = crypto.hash_lookup(r.device_id)
        if r.openid and not r.openid_hash:
            updates["openid_hash"] = crypto.hash_lookup(r.openid)
        if updates:
            n += 1
            if not dry_run:
                set_clause = ", ".join(f"{k}=:{k}" for k in updates)
                await conn.execute(text(f"UPDATE users SET {set_clause} WHERE id=:id"),
                                   {**updates, "id": r.id})
    counts["users"] = n
    if not dry_run:
        await conn.commit()

    # 2) 内容字段（可选）：加密存量明文（顺序在身份回填之后，openid 才安全加密）
    if encrypt_content:
        for table, pk, cols in _CONTENT:
            collist = ", ".join([pk] + cols)
            rows = (await conn.execute(text(f"SELECT {collist} FROM {table}"))).all()
            m = 0
            for r in rows:
                updates = {}
                for c in cols:
                    v = getattr(r, c)
                    if v is not None and not _is_encrypted(v):
                        updates[c] = crypto.encrypt(v)
                if updates:
                    m += 1
                    if not dry_run:
                        set_clause = ", ".join(f"{k}=:{k}" for k in updates)
                        await conn.execute(text(f"UPDATE {table} SET {set_clause} WHERE {pk}=:pk"),
                                           {**updates, "pk": getattr(r, pk)})
            counts[f"{table}_content"] = m
            if not dry_run:
                await conn.commit()

    return counts


async def _main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--encrypt-content", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    async with get_db_context() as conn:
        counts = await run(conn, encrypt_content=args.encrypt_content, dry_run=args.dry_run)
    mode = "DRY-RUN" if args.dry_run else "已写入"
    print(f"[{mode}] 处理计数：{counts}")


if __name__ == "__main__":
    asyncio.run(_main())
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && PYTHONPATH="venv_local;." python -m pytest tests/test_migrate_encrypt.py -q`
Expected: PASS（4 passed）

- [ ] **Step 5: 提交**

```bash
git add backend/scripts/__init__.py backend/scripts/migrate_encrypt.py backend/tests/test_migrate_encrypt.py
git commit -m "feat: 渐进加密迁移脚本（身份回填+内容加密，幂等+dry-run）"
```

---

### Task 5: 启动告警 + 文档

**Files:**
- Modify: `backend/app/main.py`（startup 告警）
- Modify: `backend/.env.example`
- Modify: `backend/README.md`

**Interfaces:** 无

- [ ] **Step 1: 加启动告警**

`backend/app/main.py`：在 import 段把 config 导入补上 `DATA_ENCRYPTION_KEY`（与现有 `from app.config import ...` 合并），在 `startup()` 现有 JWT 告警块之后追加：
```python
    if not DEBUG and not DATA_ENCRYPTION_KEY:
        logger.warning(
            "⚠️ 未设置 DATA_ENCRYPTION_KEY，正在用 JWT_SECRET 派生数据加密密钥。"
            "生产请设置固定的 DATA_ENCRYPTION_KEY，且永不更换（更换将导致密文不可解、哈希失配）。"
        )
```
（`DATA_ENCRYPTION_KEY` 需加入 `from app.config import ...` 的导入列表。）

- [ ] **Step 2: 更新 .env.example**

在 `backend/.env.example` 的「安全」段（`JWT_SECRET=` 之后）追加：
```
# 数据加密密钥（强烈建议生产设置；不设则从 JWT_SECRET 派生）
# 支持逗号分隔多个密钥做轮换：第一个加密、全部用于解密（旧密文仍可解）
# 注意：HMAC 哈希字段（openid_hash/device_id）不支持轮换；且密钥永不应更换
DATA_ENCRYPTION_KEY=
```

- [ ] **Step 3: 更新 README**

在 `backend/README.md` 的「关键设计」小节追加：
```markdown
- **儿童数据加密**：身份字段（device_id、openid_hash）HMAC 哈希、内容字段（openid、
  孩子姓名、对话、错题文本）Fernet 可逆加密，经 SQLAlchemy 透明列类型自动加解密。
  openid 用盲索引（加密存储 + openid_hash 查找），仍可解密回传微信推送。
```
在「生产部署须知」小节追加：
```markdown
- **`DATA_ENCRYPTION_KEY`**：生产须设固定强随机值并**永不更换**（更换将使所有密文不可解、
  哈希失配）。部署后跑一次 `python -m scripts.migrate_encrypt` 回填存量查找字段
  （加 `--encrypt-content` 可一并加密存量内容；先 `--dry-run` 预览，务必先备份）。
- `chroma_data/` 与 `uploads/` 仍为明文（属"全面加密"后续项），生产须对这两个目录
  做操作系统级访问控制。
```

- [ ] **Step 4: 跑全套回归确认无碍**

Run: `cd backend && PYTHONPATH="venv_local;." python -m pytest -q`
Expected: PASS（全绿）

- [ ] **Step 5: 提交**

```bash
git add backend/app/main.py backend/.env.example backend/README.md
git commit -m "feat: 数据加密密钥生产告警 + 文档（迁移/轮换/明文边界）"
```

---

## Self-Review

**Spec coverage：**
- crypto 原语（encrypt/decrypt/hash_lookup）+ 密钥轮换 → Task 1 ✓
- EncryptedText 容错、HashedKey 幂等 → Task 2 ✓
- 字段映射（openid 加密+盲索引、device_id 哈希、name/content/mistake 加密）→ Task 3 ✓
- openid 去 unique、openid_hash unique → Task 3 模型改动 ✓
- wx_login 盲索引、init_db ALTER openid_hash → Task 3 ✓
- 渐进迁移（默认身份、--encrypt-content、--dry-run、试解密幂等）→ Task 4 ✓
- 启动告警、密钥不可更换、chroma/图片边界文档 → Task 5 ✓
- 测试不依赖真实密钥（从 JWT 派生即可跑）→ 全部 ✓

**Placeholder scan：** 无 TBD/TODO；所有代码与命令完整。

**Type consistency：** `encrypt/decrypt/hash_lookup` 在 Task 1 定义，Task 2/4 按此调用；
`EncryptedText`/`HashedKey` 在 Task 2 定义，Task 3 按此用于列；`migrate_encrypt.run(conn, *, encrypt_content, dry_run)` 在 Task 4 定义与测试一致。`_build_multifernet`/`_multi` 在 Task 1 crypto.py 定义，Task 1 轮换测试引用一致。
