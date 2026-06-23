"""多孩子数据隔离测试（覆盖 active_student_id 与 list_mistakes 的 student 作用域）。"""
import pytest

from app.scope import active_student_id
from app.services import mistake_service
from app.services.mistake_service import list_mistakes, get_mistake
from tests.conftest import make_user, make_student, make_mistake


@pytest.fixture(autouse=True)
def _no_kb(monkeypatch):
    monkeypatch.setattr(mistake_service, "_get_knowledge_service", lambda: None)


async def test_active_student_id_returns_active(db):
    user = await make_user(db)
    await make_student(db, user.id, name="老大", is_active=False)
    active = await make_student(db, user.id, name="老二", is_active=True)

    sid = await active_student_id(db, user.id)
    assert sid == active.id


async def test_active_student_id_none_without_students(db):
    user = await make_user(db)
    assert await active_student_id(db, user.id) is None


async def test_list_mistakes_isolated_by_active_student(db):
    user = await make_user(db)
    s1 = await make_student(db, user.id, name="老大", is_active=True)
    s2 = await make_student(db, user.id, name="老二", is_active=False)
    await make_mistake(db, user.id, student_id=s1.id, topic="老大的错题")
    await make_mistake(db, user.id, student_id=s1.id, topic="老大的错题2")
    await make_mistake(db, user.id, student_id=s2.id, topic="老二的错题")

    items, total = await list_mistakes(db, user.id, None, False, None, 1, 50)

    # 只应返回当前活跃孩子(老大)的 2 道错题
    assert total == 2
    assert all(m.student_id == s1.id for m in items)


async def test_get_mistake_respects_scope(db):
    user = await make_user(db)
    s1 = await make_student(db, user.id, name="老大", is_active=True)
    s2 = await make_student(db, user.id, name="老二", is_active=False)
    other_child_mistake = await make_mistake(db, user.id, student_id=s2.id)

    # 当前活跃是老大，取老二的错题应取不到（被作用域隔离）
    got = await get_mistake(db, other_child_mistake.id, user.id)
    assert got is None
