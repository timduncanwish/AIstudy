"""作业批改接入OCR流程测试：spy recognize_text 与 grade_homework，验证 hint 传递与降级。"""
import os
import tempfile

import pytest

from app.services import homework_service
from tests.conftest import make_user


@pytest.fixture(autouse=True)
def _no_kb(monkeypatch):
    monkeypatch.setattr(homework_service, "_get_knowledge_service", lambda: None)


@pytest.fixture
def fake_image():
    fd, path = tempfile.mkstemp(suffix=".jpg")
    os.write(fd, b"\xff\xd8\xff\xe0fake")
    os.close(fd)
    yield path
    os.remove(path)


def _spy_grade(monkeypatch):
    seen = {}

    async def _fake_grade(image_base64, subject, grade, ocr_hint=""):
        seen["ocr_hint"] = ocr_hint
        return {"questions": [], "score": 90, "summary": "", "encouragement": ""}

    monkeypatch.setattr(homework_service, "grade_homework", _fake_grade)
    return seen


async def test_ocr_text_passed_to_grading(db, monkeypatch, fake_image):
    user = await make_user(db)

    async def _fake_ocr(image_bytes):
        return "第一题 1+1=2"

    monkeypatch.setattr(homework_service.ocr_service, "recognize_text", _fake_ocr)
    seen = _spy_grade(monkeypatch)

    await homework_service.process_homework(db, user.id, "chinese", 3, fake_image)
    assert seen["ocr_hint"] == "第一题 1+1=2"


async def test_ocr_empty_degrades_to_blank_hint(db, monkeypatch, fake_image):
    user = await make_user(db)

    async def _fake_ocr(image_bytes):
        return ""

    monkeypatch.setattr(homework_service.ocr_service, "recognize_text", _fake_ocr)
    seen = _spy_grade(monkeypatch)

    await homework_service.process_homework(db, user.id, "chinese", 3, fake_image)
    assert seen["ocr_hint"] == ""
