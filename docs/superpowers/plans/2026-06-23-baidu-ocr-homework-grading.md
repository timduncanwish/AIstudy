# 百度OCR增强作业批改 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 作业批改前先用百度OCR识别文字，连同图片一起喂给视觉模型提升准确率；任何OCR失败无声降级为现有纯视觉批改。

**Architecture:** 新增 `ocr_service.recognize_text(image_bytes) -> str`（百度手写识别 + access_token 缓存 + 全程 try/except 降级）。`grade_homework` 增加可选 `ocr_hint` 参注入批改 prompt。`process_homework` 在批改前调用 OCR。纯后端，前端不动。

**Tech Stack:** FastAPI、httpx（异步）、百度OCR REST API、pytest + pytest-asyncio。

## Global Constraints

- OCR 为可选增强：未配置或任何失败必须返回 `""`，使批改退回纯视觉，对外行为零变化。
- 不发真实百度请求即可让测试全绿（mock httpx）。
- 测试运行命令：`cd backend && PYTHONPATH="venv_local;." python -m pytest`（Windows 路径分隔符为 `;`）。
- commit 信息用中文；沿用项目「AI 失败韧性」与隐私保护原则。
- 不抽象多服务商框架，不改前端，不改 `process_homework` 对外返回结构。

---

### Task 1: OCR 服务 `ocr_service.recognize_text`（含配置）

**Files:**
- Modify: `backend/app/config.py`（在 WX_SECRET 段后追加两行配置）
- Create: `backend/app/services/ocr_service.py`
- Test: `backend/tests/test_ocr_service.py`

**Interfaces:**
- Consumes: `app.config.BAIDU_OCR_API_KEY`, `app.config.BAIDU_OCR_SECRET_KEY`（str，默认 ""）
- Produces: `async ocr_service.recognize_text(image_bytes: bytes) -> str`（失败/未配置返回 ""）

- [ ] **Step 1: 加配置项**

在 `backend/app/config.py` 的 `WX_SECRET = os.getenv("WX_SECRET", "")` 之后追加：

```python
# 百度OCR（可选；不配则作业批改仅用视觉模型）
BAIDU_OCR_API_KEY = os.getenv("BAIDU_OCR_API_KEY", "")
BAIDU_OCR_SECRET_KEY = os.getenv("BAIDU_OCR_SECRET_KEY", "")
```

- [ ] **Step 2: 写失败测试**

创建 `backend/tests/test_ocr_service.py`：

```python
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
```

- [ ] **Step 3: 运行测试确认失败**

Run: `cd backend && PYTHONPATH="venv_local;." python -m pytest tests/test_ocr_service.py -q`
Expected: FAIL（`ModuleNotFoundError: app.services.ocr_service` 或 AttributeError）

- [ ] **Step 4: 实现 ocr_service**

创建 `backend/app/services/ocr_service.py`：

```python
"""百度OCR手写文字识别。可选增强，任何失败返回 ""，由调用方退回纯视觉批改。"""
import base64
import time
import logging

import httpx

from app.config import BAIDU_OCR_API_KEY, BAIDU_OCR_SECRET_KEY

logger = logging.getLogger(__name__)

_TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"
_OCR_URL = "https://aip.baidubce.com/rest/2.0/ocr/v1/handwriting"

_token_cache: dict = {"token": "", "expires_at": 0}


async def _get_access_token() -> str:
    if _token_cache["token"] and time.time() < _token_cache["expires_at"]:
        return _token_cache["token"]
    if not BAIDU_OCR_API_KEY or not BAIDU_OCR_SECRET_KEY:
        return ""
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(_TOKEN_URL, params={
                "grant_type": "client_credentials",
                "client_id": BAIDU_OCR_API_KEY,
                "client_secret": BAIDU_OCR_SECRET_KEY,
            })
            data = resp.json()
    except Exception:
        logger.warning("baidu ocr token request failed", exc_info=True)
        return ""
    token = data.get("access_token", "")
    expires_in = data.get("expires_in", 2592000)
    if token:
        _token_cache["token"] = token
        _token_cache["expires_at"] = time.time() + expires_in - 86400  # 提前1天刷新
    return token


async def recognize_text(image_bytes: bytes) -> str:
    if not BAIDU_OCR_API_KEY or not BAIDU_OCR_SECRET_KEY:
        return ""
    token = await _get_access_token()
    if not token:
        return ""
    try:
        img_b64 = base64.b64encode(image_bytes).decode("utf-8")
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.post(
                _OCR_URL,
                params={"access_token": token},
                data={"image": img_b64},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            data = resp.json()
    except Exception:
        logger.warning("baidu ocr request failed", exc_info=True)
        return ""
    words = data.get("words_result") or []
    lines = [w.get("words", "") for w in words if w.get("words")]
    return "\n".join(lines)
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd backend && PYTHONPATH="venv_local;." python -m pytest tests/test_ocr_service.py -q`
Expected: PASS（5 passed）

- [ ] **Step 6: 提交**

```bash
git add backend/app/config.py backend/app/services/ocr_service.py backend/tests/test_ocr_service.py
git commit -m "feat: 新增百度OCR手写识别服务（带token缓存与全程降级）"
```

---

### Task 2: `grade_homework` 注入 OCR 提示

**Files:**
- Modify: `backend/app/services/ai_service.py:131-160`（`grade_homework`）
- Test: `backend/tests/test_grade_homework_hint.py`

**Interfaces:**
- Consumes: 无（独立改造）
- Produces: `async grade_homework(image_base64: str, subject: str, grade: int, ocr_hint: str = "") -> dict`

- [ ] **Step 1: 写失败测试**

创建 `backend/tests/test_grade_homework_hint.py`：

```python
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
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && PYTHONPATH="venv_local;." python -m pytest tests/test_grade_homework_hint.py -q`
Expected: FAIL（`test_ocr_hint_injected_into_prompt` 失败——hint 未注入；或 TypeError: 意外的 ocr_hint 参数）

- [ ] **Step 3: 改造 grade_homework**

将 `backend/app/services/ai_service.py` 的 `grade_homework` 改为（替换 131-160 行整段函数）：

```python
async def grade_homework(image_base64: str, subject: str, grade: int, ocr_hint: str = "") -> dict:
    system_prompt = HOMEWORK_GRADING_PROMPTS.get(
        subject, HOMEWORK_GRADING_PROMPTS["chinese"]
    ).format(grade=grade)

    text_prompt = system_prompt
    if ocr_hint:
        text_prompt += f"\n\n以下是OCR预识别的文字（可能有误，仅供参考）：\n{ocr_hint}"
    text_prompt += "\n\nGrade this homework now."

    response = await _client.chat.completions.create(
        model="glm-4v-flash",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        },
                    },
                    {
                        "type": "text",
                        "text": text_prompt,
                    },
                ],
            },
        ],
        max_tokens=3000,
        temperature=0.3,
    )

    text = response.choices[0].message.content
    return _parse_grading_json(text)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && PYTHONPATH="venv_local;." python -m pytest tests/test_grade_homework_hint.py -q`
Expected: PASS（2 passed）

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/ai_service.py backend/tests/test_grade_homework_hint.py
git commit -m "feat: grade_homework 支持注入OCR预识别文字提示"
```

---

### Task 3: `process_homework` 接入 OCR

**Files:**
- Modify: `backend/app/services/homework_service.py`（imports 段 + 读图与调用 grade_homework 处）
- Test: `backend/tests/test_homework_ocr_flow.py`

**Interfaces:**
- Consumes: `ocr_service.recognize_text`（Task 1）、`grade_homework(..., ocr_hint=...)`（Task 2）
- Produces: 无（流程内部接线）

- [ ] **Step 1: 写失败测试**

创建 `backend/tests/test_homework_ocr_flow.py`：

```python
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
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && PYTHONPATH="venv_local;." python -m pytest tests/test_homework_ocr_flow.py -q`
Expected: FAIL（`AttributeError: module 'app.services.homework_service' has no attribute 'ocr_service'`）

- [ ] **Step 3: 接线 process_homework**

在 `backend/app/services/homework_service.py` 顶部 import 段（`from app.scope import active_student_id` 一行附近）追加：

```python
from app.services import ocr_service
```

将读图与调用批改处（当前 `with open(...) as f: image_base64 = base64.b64encode(f.read())...` 到 `result = await grade_homework(image_base64, subject, grade)`）改为：

```python
    with open(file_path, "rb") as f:
        raw_bytes = f.read()
    image_base64 = base64.b64encode(raw_bytes).decode("utf-8")

    ocr_text = await ocr_service.recognize_text(raw_bytes)

    sid = await active_student_id(db, user_id)
```

并把后面的批改调用改为：

```python
        result = await grade_homework(image_base64, subject, grade, ocr_hint=ocr_text)
```

> 注意：保持 `sid = await active_student_id(...)` 与 Homework 创建逻辑原样，只在其前插入 `ocr_text` 一行；`grade_homework` 调用追加 `ocr_hint=ocr_text` 参数。

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && PYTHONPATH="venv_local;." python -m pytest tests/test_homework_ocr_flow.py -q`
Expected: PASS（2 passed）

- [ ] **Step 5: 跑全套回归**

Run: `cd backend && PYTHONPATH="venv_local;." python -m pytest -q`
Expected: PASS（全部既有测试 + 新增，全绿）

- [ ] **Step 6: 提交**

```bash
git add backend/app/services/homework_service.py backend/tests/test_homework_ocr_flow.py
git commit -m "feat: 作业批改前先调百度OCR，识别文字注入批改提示"
```

---

### Task 4: 文档同步

**Files:**
- Modify: `backend/.env.example`
- Modify: `backend/README.md`

**Interfaces:** 无

- [ ] **Step 1: 更新 .env.example**

在 `backend/.env.example` 的「微信小程序」段之前（或文件末尾）追加：

```
# 百度OCR（可选；不配则作业批改仅用视觉模型）
BAIDU_OCR_API_KEY=
BAIDU_OCR_SECRET_KEY=
```

- [ ] **Step 2: 更新 README**

在 `backend/README.md` 的「技术栈」表格 OCR 行（若无则在 AI 行下）补一行，并在「关键设计」小节追加一句：

```markdown
- **作业 OCR 增强**：批改前先用百度 OCR 识别文字注入视觉模型提示；未配置
  `BAIDU_OCR_*` 或 OCR 失败时自动降级为纯视觉批改。
```

- [ ] **Step 3: 提交**

```bash
git add backend/.env.example backend/README.md
git commit -m "docs: 补充百度OCR配置说明"
```

---

## Self-Review

**Spec coverage：**
- 新增 `ocr_service.recognize_text` + token 缓存 → Task 1 ✓
- 分层降级（未配置/token失败/请求异常/空结果均返回""）→ Task 1 测试覆盖 ✓
- `grade_homework` 注入 `ocr_hint` → Task 2 ✓
- `process_homework` 批改前 OCR → Task 3 ✓
- 配置项 `BAIDU_OCR_API_KEY/SECRET_KEY` → Task 1 Step 1 + Task 4 ✓
- 测试不发真实请求 → Task 1/2/3 全部 mock ✓
- README/.env.example 同步 → Task 4 ✓

**Placeholder scan：** 无 TBD/TODO，所有代码与命令均完整。

**Type consistency：** `recognize_text(image_bytes: bytes) -> str`、`grade_homework(..., ocr_hint: str="")` 在 Task 1/2 定义，Task 3 按此调用，签名一致。
