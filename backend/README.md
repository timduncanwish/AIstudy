# AI助学 · 后端

小学3-6年级语文/英语 AI 辅导后端，FastAPI（异步）+ SQLAlchemy + 智谱AI。

> 项目价值观与产品定位见根目录 [CLAUDE.md](../CLAUDE.md)；技术规范见 [SPEC.md](../SPEC.md)。

## 技术栈

| 组件 | 说明 |
|------|------|
| Web | FastAPI + uvicorn（异步） |
| ORM | SQLAlchemy 2.0 + aiosqlite（开发）|
| AI | 智谱AI GLM-4-flash（OpenAI 兼容接口）|
| OCR | 百度OCR 手写识别（可选，增强作业批改）|
| 向量库 | chromadb（错题知识库，语义检索）|
| 鉴权 | JWT（Bearer）|
| 限流 | slowapi |
| 定时 | APScheduler（每日学习汇总推送）|

## 快速开始

```bash
cd backend

# 1. 创建虚拟环境并安装依赖
python -m venv venv
venv\Scripts\activate        # Windows；macOS/Linux 用 source venv/bin/activate
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env          # 然后填入 ZHIPU_API_KEY 等
                              # Windows: copy .env.example .env

# 3. 启动（开发，热重载）
python -m uvicorn app.main:app --reload

# 健康检查
curl http://localhost:8000/health   # -> {"status":"ok"}
```

## 测试

```bash
cd backend
python -m pytest
```

测试用独立的临时 SQLite，不触碰真实库，并屏蔽知识库以免触发 AI 调用。
覆盖：间隔重复算法、多孩子数据隔离、每日一练计分、作业通知、报告聚合。

## 主要接口

| 前缀 | 功能 |
|------|------|
| `/auth` | 微信登录、JWT 签发 |
| `/chat` | AI 对话（`/chat/stream` 为 SSE 流式）、历史会话 |
| `/homework` | 作业图片上传批改，自动生成错题 |
| `/mistakes` | 错题本、间隔重复复习、知识图谱、知识库 |
| `/practice` | 每日一练（AI 按薄弱知识点出题）|
| `/challenge` | 字词闯关 |
| `/students` | 多孩子档案管理 |
| `/reports` | 每日/每周学习报告 |
| `/notify` | 微信订阅消息（即时简报 + 每日汇总）|

## 关键设计

- **多孩子数据隔离**：学习数据（错题/作业/对话/每日一练）按「当前活跃孩子」隔离，
  见 `app/scope.py`。启动时对存量表做幂等迁移并回填 `student_id`。
- **AI 失败韧性**：出题失败抛 503、批改失败标记 failed、通知失败静默不影响主流程。
- **作业 OCR 增强**：批改前先用百度 OCR 识别文字注入视觉模型提示；未配置
  `BAIDU_OCR_*` 或 OCR 失败时自动降级为纯视觉批改。
- **儿童数据加密**：身份字段（device_id、openid_hash）HMAC 哈希、内容字段（openid、
  孩子姓名、对话、错题文本）Fernet 可逆加密，经 SQLAlchemy 透明列类型自动加解密。
  openid 用盲索引（加密存储 + openid_hash 查找），仍可解密回传微信推送。

## 生产部署须知

- **`JWT_SECRET`** 必须在 `.env` 设为强随机值，否则用公开默认值、令牌可被伪造
  （非 DEBUG 时启动会告警）。
- **`ALLOWED_ORIGINS`** 设为具体域名，不要在生产用 `*`。
- **`DEBUG=false`**。
- **智谱账户额度**：AI 对话/批改/出题/知识库嵌入全依赖智谱，确保额度充足。
- 数据库可通过 `DATABASE_URL` 切换为 MySQL。
- **`DATA_ENCRYPTION_KEY`**：生产须设固定强随机值并**永不更换**（更换将使所有密文不可解、
  哈希失配）。用 `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` 生成合法密钥。部署后跑一次 `python -m scripts.migrate_encrypt` 回填存量查找字段
  （加 `--encrypt-content` 可一并加密存量内容；先 `--dry-run` 预览，务必先备份）。
- `chroma_data/` 与 `uploads/` 仍为明文（属"全面加密"后续项），生产须对这两个目录
  做操作系统级访问控制。
