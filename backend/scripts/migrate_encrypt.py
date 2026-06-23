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

from app.database import get_db_context, init_db
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
    # 先确保表结构就绪（幂等加 openid_hash 列），脚本才能独立于应用启动运行
    await init_db()
    async with get_db_context() as conn:
        counts = await run(conn, encrypt_content=args.encrypt_content, dry_run=args.dry_run)
    mode = "DRY-RUN" if args.dry_run else "已写入"
    print(f"[{mode}] 处理计数：{counts}")


if __name__ == "__main__":
    asyncio.run(_main())
