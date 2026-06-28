"""家长端学生档案：增删改查、归属校验、活跃孩子切换。"""

import pytest

from app.services.student_service import (
    activate_student,
    create_student,
    delete_student,
    get_active_student,
    list_students,
    update_student,
)
from tests.conftest import make_user


@pytest.mark.asyncio
async def test_create_first_student_is_active(db):
    user = await make_user(db)
    a = await create_student(db, user.id, "小明", 3)
    assert a.is_active is True  # 第一个孩子自动设为当前
    b = await create_student(db, user.id, "小红", 4)
    assert b.is_active is False
    assert len(await list_students(db, user.id)) == 2


@pytest.mark.asyncio
async def test_update_student_changes_fields_and_ignores_none(db):
    user = await make_user(db)
    s = await create_student(db, user.id, "小明", 3, "👦")
    updated = await update_student(db, s.id, user.id, name="小明明", grade=5, avatar_tag=None)
    assert updated is not None
    assert updated.name == "小明明"
    assert updated.grade == 5
    assert updated.avatar_tag == "👦"  # None 值被忽略，不覆盖


@pytest.mark.asyncio
async def test_update_other_users_student_returns_none(db):
    u1 = await make_user(db)
    u2 = await make_user(db)
    s = await create_student(db, u1.id, "小明", 3)
    assert await update_student(db, s.id, u2.id, name="改不了") is None
    again = (await list_students(db, u1.id))[0]
    assert again.name == "小明"  # 未被他人篡改


@pytest.mark.asyncio
async def test_delete_student_ownership(db):
    u1 = await make_user(db)
    u2 = await make_user(db)
    s = await create_student(db, u1.id, "小明", 3)
    assert await delete_student(db, s.id, u2.id) is False  # 非本人不可删
    assert await delete_student(db, s.id, u1.id) is True
    assert await list_students(db, u1.id) == []


@pytest.mark.asyncio
async def test_delete_active_promotes_next(db):
    user = await make_user(db)
    a = await create_student(db, user.id, "老大", 3)  # 自动 active
    b = await create_student(db, user.id, "老二", 4)
    assert a.is_active and not b.is_active

    assert await delete_student(db, a.id, user.id) is True
    active = await get_active_student(db, user.id)
    assert active is not None and active.id == b.id  # 删除当前孩子后自动顶上


@pytest.mark.asyncio
async def test_activate_switches_only_one_active(db):
    user = await make_user(db)
    await create_student(db, user.id, "老大", 3)
    b = await create_student(db, user.id, "老二", 4)

    res = await activate_student(db, b.id, user.id)
    assert res is not None and res.is_active is True

    actives = [s for s in await list_students(db, user.id) if s.is_active]
    assert len(actives) == 1 and actives[0].id == b.id  # 同时只有一个当前孩子


@pytest.mark.asyncio
async def test_activate_nonexistent_returns_none(db):
    user = await make_user(db)
    await create_student(db, user.id, "老大", 3)
    assert await activate_student(db, 99999, user.id) is None
