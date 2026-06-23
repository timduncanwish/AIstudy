"""grade_homework 注入 OCR 提示测试：mock AI 客户端，捕获发出的 prompt。"""
from app.services import ai_service


class _Msg:
    content = '{"questions": [], "score": 90, "summary": "", "encouragement": ""}'


class _Choice:
    message = _Msg()


class _Resp:
    choices = [_Choice()]


def _capture_create(monkeypatch):
    captured = {}

    async def _fake_create(**kwargs):
        captured["messages"] = kwargs["messages"]
        return _Resp()

    monkeypatch.setattr(ai_service._client.chat.completions, "create", _fake_create)
    return captured


def _text_part(captured):
    # content 是 [image_url, text] 两段，取 text 段
    return captured["messages"][0]["content"][1]["text"]


async def test_ocr_hint_injected_into_prompt(monkeypatch):
    captured = _capture_create(monkeypatch)
    await ai_service.grade_homework("imgb64", "chinese", 3, ocr_hint="第一题 1+1=2")
    assert "第一题 1+1=2" in _text_part(captured)


async def test_no_hint_prompt_has_no_ocr_section(monkeypatch):
    captured = _capture_create(monkeypatch)
    await ai_service.grade_homework("imgb64", "chinese", 3)
    assert "OCR" not in _text_part(captured)
