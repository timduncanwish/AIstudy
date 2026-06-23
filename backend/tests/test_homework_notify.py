"""作业批改通知测试：score=None 时不推送（避免误报"0分"），有分数且已订阅才推送。"""
import os
import tempfile

import pytest

from app.services import homework_service
from app.services import notify_service
from app.services.homework_service import process_homework
from tests.conftest import make_user


@pytest.fixture(autouse=True)
def _no_kb(monkeypatch):
    monkeypatch.setattr(homework_service, "_get_knowledge_service", lambda: None)


@pytest.fixture
def fake_image():
    fd, path = tempfile.mkstemp(suffix=".jpg")
    os.write(fd, b"\xff\xd8\xff\xe0fake-jpeg-bytes")
    os.close(fd)
    yield path
    os.remove(path)


def _spy_notify(monkeypatch):
    calls = []

    async def _fake(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr(notify_service, "notify_practice_done", _fake)
    return calls


async def test_no_notify_when_score_is_none(db, monkeypatch, fake_image):
    user = await make_user(db, openid="wx_openid_1", notify_subscribed=1)

    async def _grade(*a, **k):
        return {"questions": [], "score": None, "summary": "", "encouragement": ""}

    monkeypatch.setattr(homework_service, "grade_homework", _grade)
    calls = _spy_notify(monkeypatch)

    result = await process_homework(db, user.id, "chinese", 3, fake_image)

    assert result["score"] is None
    assert calls == []  # score 为 None → 不应推送


async def test_notify_when_score_present_and_subscribed(db, monkeypatch, fake_image):
    user = await make_user(db, openid="wx_openid_2", notify_subscribed=1)

    async def _grade(*a, **k):
        return {
            "questions": [{"is_correct": True, "question_text": "q", "topic": "拼音"}],
            "score": 88, "summary": "不错", "encouragement": "加油",
        }

    monkeypatch.setattr(homework_service, "grade_homework", _grade)
    calls = _spy_notify(monkeypatch)

    await process_homework(db, user.id, "chinese", 3, fake_image)

    assert len(calls) == 1
    assert calls[0]["score"] == 88
    assert calls[0]["total"] == 100


async def test_no_notify_when_not_subscribed(db, monkeypatch, fake_image):
    user = await make_user(db, openid="wx_openid_3", notify_subscribed=0)

    async def _grade(*a, **k):
        return {"questions": [], "score": 90, "summary": "", "encouragement": ""}

    monkeypatch.setattr(homework_service, "grade_homework", _grade)
    calls = _spy_notify(monkeypatch)

    await process_homework(db, user.id, "chinese", 3, fake_image)

    assert calls == []  # 未订阅 → 不推送
