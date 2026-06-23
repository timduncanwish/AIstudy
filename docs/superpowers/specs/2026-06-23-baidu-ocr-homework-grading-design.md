# 设计文档：百度 OCR 增强作业批改

- 日期：2026-06-23
- 状态：已与用户确认设计，待写实现计划
- 范围：纯后端增强，前端无改动

## 背景与目标

PRD 二期「作业批改+错题本」主体已实现：拍照上传、AI 批改、错题讲解、错题本、
遗忘曲线复习均在代码中。唯一明确缺口是 PRD/CLAUDE.md 提到的「独立 OCR 识别」。

当前作业批改直接把图片喂给视觉模型 `glm-4-flash`，由其同时完成识别+批改。
本次接入**百度 OCR 手写文字识别**作为**增强**：先 OCR 提取文字，连同图片一起
交给视觉模型，提升手写/模糊题目的识别准确率。

**核心约束**：OCR 是可选增强，任何失败都必须无声降级为现有纯视觉批改，
家长/孩子无感知（沿用项目「AI 失败韧性」原则）。

## 非目标（YAGNI）

- 不做多服务商插件框架，只实现百度；保留 `recognize_text` 单一接口便于日后替换
- 不做 OCR 结果展示页（本次只增强批改，不改前端）
- 不改变 `process_homework` 的对外返回结构

## 架构与数据流

```
图片字节 ──→ ocr_service.recognize_text(image_bytes) ──→ ocr_text(str，失败为 "")
                                                              │
图片 base64 ──────────────────────────────────────────────┐  │
                                                           ▼  ▼
                          ai_service.grade_homework(image_base64, ocr_hint=ocr_text)
                                       └─→ 视觉模型(图片 + OCR文字提示) → 逐题批改
```

### 新增 `app/services/ocr_service.py`

参照 `notify_service.py` 的 access_token 缓存模式：

- `async recognize_text(image_bytes: bytes) -> str`
  - 未配置 `BAIDU_OCR_API_KEY`/`BAIDU_OCR_SECRET_KEY` → 直接返回 `""`，不发请求
  - 取 access_token（带模块级缓存）
  - 调百度手写识别端点，解析 `words_result[].words` 按行拼接为纯文本
  - 全程 `try/except`，任何异常记 warning 并返回 `""`
- access_token 缓存：模块级 `{"token": "", "expires_at": 0}`，百度 token 有效期约 30 天，提前 1 天刷新
- HTTP 用 `httpx.AsyncClient`，OCR 请求设 8s 超时，避免拖慢批改

**百度端点**
- token：`https://aip.baidubce.com/oauth/2.0/token`（grant_type=client_credentials）
- OCR：`https://aip.baidubce.com/rest/2.0/ocr/v1/handwriting`（手写，印刷体亦可识别）

### 改造 `ai_service.grade_homework`

- 签名增加可选参：`grade_homework(image_base64, subject, grade, ocr_hint: str = "")`
- 当 `ocr_hint` 非空时，在用户 prompt 前追加：
  `"以下是OCR预识别的文字（可能有误，仅供参考）：\n{ocr_hint}\n"`
- `ocr_hint` 为空时 prompt 完全等同现状 → 零行为变化

### 改造 `homework_service.process_homework`

- 读取图片字节后，先 `ocr_text = await ocr_service.recognize_text(image_bytes)`
- 调用 `grade_homework(image_base64, subject, grade, ocr_hint=ocr_text)`
- 其余逻辑（错题生成、知识库、家长通知）不变

### 配置

`config.py` 新增（默认空字符串）：
```python
BAIDU_OCR_API_KEY = os.getenv("BAIDU_OCR_API_KEY", "")
BAIDU_OCR_SECRET_KEY = os.getenv("BAIDU_OCR_SECRET_KEY", "")
```
`.env.example` 新增段：
```
# 百度OCR（可选；不配则作业批改仅用视觉模型）
BAIDU_OCR_API_KEY=
BAIDU_OCR_SECRET_KEY=
```

## 错误处理（分层降级）

| 情况 | 行为 |
|------|------|
| 未配 API Key/Secret | 直接返回 `""`，不发请求 |
| token 获取失败 | 记 warning，返回 `""` |
| OCR 请求超时/报错 | `try/except` 记 warning，返回 `""` |
| OCR 返回空/无文字 | 返回 `""` |

任一情况 → 批改照常走纯视觉，对外行为不变。

## 测试（扩展现有 pytest 套件）

- `tests/test_ocr_service.py`（mock `httpx`，不发真实请求）：
  - 未配置 → 返回 `""` 且不发请求
  - 正常响应 → `words_result` 正确拼接为多行文本
  - token 获取失败 → 返回 `""`
  - OCR 请求抛异常 → 返回 `""`
  - access_token 命中缓存不重复请求
- 流程测试（参照 `test_homework_notify.py` 的 spy 风格）：
  - spy `recognize_text` 返回非空 → 断言 `grade_homework` 收到对应 `ocr_hint`
  - `recognize_text` 返回 `""` → 断言 `grade_homework` 收到空 `ocr_hint`（降级路径）
- 所有测试不依赖真实百度凭证，无凭证也全绿

## 验收标准

1. 配置百度凭证后，作业批改会先调用 OCR 并将文字注入批改 prompt
2. 未配置或 OCR 失败时，批改行为与现状完全一致（纯视觉），无异常冒泡
3. 新增单测全部通过，且不发真实外部请求
4. `.env.example` 与后端 README 同步说明新配置项
