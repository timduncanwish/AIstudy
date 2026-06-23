"""百度OCR服务测试：全程 mock httpx，不发真实请求。"""
import pytest

from app.services import ocr_service


@pytest.fixture(autouse=True)
def _reset_token_cache():
    ocr_service._token_cache.update({"token": "", "expires_at": 0})
    yield
    ocr_service._token_cache.update({"token": "", "expires_at": 0})


class _FakeResp:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


def _install_fake_httpx(monkeypatch, *, token_data=None, ocr_data=None,
                        get_raises=False, post_raises=False):
    calls = {"get": 0, "post": 0}

    class _FakeClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, url, params=None):
            calls["get"] += 1
            if get_raises:
                raise RuntimeError("boom")
            return _FakeResp(token_data or {})

        async def post(self, url, params=None, data=None, headers=None):
            calls["post"] += 1
            if post_raises:
                raise RuntimeError("boom")
            return _FakeResp(ocr_data or {})

    monkeypatch.setattr(ocr_service.httpx, "AsyncClient", _FakeClient)
    return calls


def _configure(monkeypatch):
    monkeypatch.setattr(ocr_service, "BAIDU_OCR_API_KEY", "key")
    monkeypatch.setattr(ocr_service, "BAIDU_OCR_SECRET_KEY", "secret")


async def test_unconfigured_returns_empty_without_request(monkeypatch):
    monkeypatch.setattr(ocr_service, "BAIDU_OCR_API_KEY", "")
    monkeypatch.setattr(ocr_service, "BAIDU_OCR_SECRET_KEY", "")
    calls = _install_fake_httpx(monkeypatch)
    assert await ocr_service.recognize_text(b"img") == ""
    assert calls["get"] == 0 and calls["post"] == 0


async def test_recognizes_and_joins_lines(monkeypatch):
    _configure(monkeypatch)
    _install_fake_httpx(
        monkeypatch,
        token_data={"access_token": "t", "expires_in": 2592000},
        ocr_data={"words_result": [{"words": "第一题"}, {"words": "1+1=2"}]},
    )
    assert await ocr_service.recognize_text(b"img") == "第一题\n1+1=2"


async def test_token_failure_returns_empty(monkeypatch):
    _configure(monkeypatch)
    calls = _install_fake_httpx(monkeypatch, token_data={})  # 无 access_token
    assert await ocr_service.recognize_text(b"img") == ""
    assert calls["post"] == 0  # 没拿到 token 不应调 OCR


async def test_ocr_exception_returns_empty(monkeypatch):
    _configure(monkeypatch)
    _install_fake_httpx(
        monkeypatch,
        token_data={"access_token": "t", "expires_in": 2592000},
        post_raises=True,
    )
    assert await ocr_service.recognize_text(b"img") == ""


async def test_access_token_is_cached(monkeypatch):
    _configure(monkeypatch)
    calls = _install_fake_httpx(
        monkeypatch,
        token_data={"access_token": "t", "expires_in": 2592000},
        ocr_data={"words_result": [{"words": "x"}]},
    )
    await ocr_service.recognize_text(b"img")
    await ocr_service.recognize_text(b"img")
    assert calls["get"] == 1  # token 命中缓存，不重复获取
    assert calls["post"] == 2
