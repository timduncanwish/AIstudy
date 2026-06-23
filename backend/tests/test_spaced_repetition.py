"""间隔重复算法测试（覆盖 review_mistake 的 mastery/next_review 更新）。"""
from datetime import datetime, timedelta

import pytest

from app.services import mistake_service
from app.services.mistake_service import review_mistake, REVIEW_INTERVALS
from tests.conftest import make_user, make_mistake


@pytest.fixture(autouse=True)
def _no_kb(monkeypatch):
    # 屏蔽知识库（否则会触发嵌入 AI 调用 / 网络）
    monkeypatch.setattr(mistake_service, "_get_knowledge_service", lambda: None)


async def test_correct_raises_mastery_and_pushes_review(db):
    user = await make_user(db)
    m = await make_mistake(db, user.id, mastery=1, review_count=2)

    before = datetime.now()
    updated = await review_mistake(db, m, correct=True)

    assert updated.mastery == 2
    assert updated.review_count == 3
    # next_review = now + REVIEW_INTERVALS[mastery] 天
    expected_days = REVIEW_INTERVALS[2]
    delta = updated.next_review - before
    assert timedelta(days=expected_days - 1) < delta < timedelta(days=expected_days + 1)


async def test_wrong_lowers_mastery_not_below_zero(db):
    user = await make_user(db)
    m = await make_mistake(db, user.id, mastery=0)

    updated = await review_mistake(db, m, correct=False)

    assert updated.mastery == 0  # 不低于 0
    assert updated.review_count == 1


async def test_mastery_capped_at_five(db):
    user = await make_user(db)
    m = await make_mistake(db, user.id, mastery=5)

    updated = await review_mistake(db, m, correct=True)

    assert updated.mastery == 5  # 不超过 5
    # mastery=5 时仍能安全索引 REVIEW_INTERVALS（min 保护）
    assert updated.next_review > datetime.now()
