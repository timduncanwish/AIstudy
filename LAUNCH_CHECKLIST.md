# 上线前检查清单（AI助学）

> 本清单基于对当前代码/配置的实际审查生成，标注证据位置与具体动作。
> 严重度：🔴 必须（阻断上线） / 🟡 强烈建议 / 🟢 注意。

## 🔴 必须（上线前务必处理）

### 1. JWT_SECRET 用强随机值
- 证据：`backend/app/config.py:26-27` 默认 `ai_tutor_secret_key_change_in_prod`；`.env.example` 为占位符。
- 风险：默认密钥可被任何人伪造登录令牌。
- 动作：在生产 `.env` 设 `JWT_SECRET=<强随机串>`。`main.py:79` 在非 DEBUG 且仍用默认值时会告警。

### 2. 生产关闭 DEBUG
- 证据：`config.py:17` 默认 `DEBUG=True`；`.env.example` 也是 `true`。
- 风险：DEBUG=True 会让 JWT/加密密钥告警失效、并开启自动 reload。
- 动作：生产 `.env` 设 `DEBUG=false`。

### 3. 固定 DATA_ENCRYPTION_KEY（且永不更换）
- 证据：`config.py:30` 默认空 → 从 JWT_SECRET 派生；`main.py:84` 有告警。
- 风险：不设则与 JWT_SECRET 绑定；一旦更换，已有密文（手机号等）不可解、`openid_hash` 失配导致登录错乱。
- 动作：生产设固定强随机 `DATA_ENCRYPTION_KEY`，写入运维密钥库，**永不更换**（轮换见 docs 轮换说明）。

### 4. 确认智谱 API 额度与计费
- 证据：AI 调用点 —
  - `ai_service.py` chat / homework(glm-4v) / preview-explain；限流：chat `30/min`(chat.py:31)、homework `5/min`(homework.py:18)、explain `20/min`(preview.py:110)。
  - `practice_service.py:115` 生成练习调智谱，但 `routers/practice.py` 的 `/generate` **无限流**。
  - `knowledge_service.py:43` 嵌入 `embedding-3`，由**作业批改**(`homework_service.py:85`)与**错题入库**(`mistakes.py:151`)触发。
- 风险：`embedding-3` 曾触发 **429 资源欠费**（见记忆 zhipu-api-quota-risk）。
- 动作：上线前确认账户余额/限额；接入用量监控；给 `/practice/generate` 补限流（见 🟡8）。

### 5. 教材字表数据人工复核
- 证据：`backend/app/data/textbooks/` 共 36 册，`source_status` 全部 `待人工复核`（已复核文件数=0）；5-6 年级语文为「高置信核心字」非整册全量（见 `INDEX.md`）。
- 风险：字表准确性/完整性未经人工核对，给小学生用属硬伤。
- 动作：对照官方教材逐册核对补全，改 `source_status=已复核` 后方可作为权威数据发布。

## 🟡 强烈建议

### 6. CORS 限定来源
- 证据：`config.py:33` 与 `.env.example` 默认 `ALLOWED_ORIGINS=*`。
- 动作：生产设具体域名（如 `https://servicewechat.com,https://<你的H5域名>`）。注：`main.py:34` 已在 `*` 时自动关闭 credentials。

### 7. 数据库换 MySQL
- 证据：`config.py:13` 默认 `sqlite`；PRD 生产用 MySQL。
- 动作：生产设 `DATABASE_URL` 指向 MySQL；sqlite 不适合并发生产。

### 8. 给 /practice/generate 补限流
- 证据：`routers/practice.py` `POST /generate` 调智谱却无 `@limiter.limit`（对比 chat/homework/explain 均有）。
- 动作：加 `@limiter.limit("10/minute")` 之类，防滥用与成本失控。
- 说明：`/preview/unit-challenge`、`/parent-summary`、`/challenge-result` 不调 AI，无需限流。

### 9. 微信配置齐全
- 证据：`.env.example` 中 `WX_APPID`/`WX_SECRET`（登录）、`WX_TMPL_PRACTICE`/`WX_TMPL_DAILY`（订阅消息模板）为空。
- 动作：在微信 MP 后台申请并填入，否则登录与学习通知不可用。

## 🟢 注意

### 10. ~~家长端档案接口鉴权~~（已修复）
- 原风险：`routers/students.py` 用 `X-User-Id` 头 + `anonymous` 兜底定位用户，客户端自报的字符串没有签名校验，知道/猜到对方 X-User-Id 即可读写他人孩子档案（含删除）。
- 修复：`/students` 全部接口改为强制 `require_user_id`（有效 JWT），不再接受 `X-User-Id` 头兜底；未登录一律 401。前端个人中心加了登录态检查，未登录点「添加/编辑」会提示先登录而不是直接报错。见 `backend/tests/test_students_router_authz.py`。
- 说明：preview/homework/chat 等匿名可用接口的 `X-User-Id` 兜底逻辑本身没变——那类接口设计上就允许免登录使用，风险敞口与本条不同，未在本次修复范围内。

### 11. 上传文件存储
- 证据：作业图片存本地磁盘 `uploads/`（`homework.py`）。
- 动作：生产建议对象存储 + 大小限制 + 定期清理。

### 12. OCR 为可选
- 证据：`config.py:22` 未配百度 OCR 则作业批改仅用视觉模型，可接受。

---

## 快速核对（生产 .env 最小项）
```
DEBUG=false
JWT_SECRET=<强随机>
DATA_ENCRYPTION_KEY=<固定强随机，永不换>
ALLOWED_ORIGINS=https://servicewechat.com,https://<H5域名>
DATABASE_URL=mysql+aiomysql://...
ZHIPU_API_KEY=<有额度的key>
WX_APPID=...  WX_SECRET=...
WX_TMPL_PRACTICE=...  WX_TMPL_DAILY=...
```
