# 设计文档：儿童数据加密与合规

- 日期：2026-06-23
- 状态：已与用户确认设计，待写实现计划
- 范围：后端字段级透明加密 + 渐进迁移；前端无改动

## 背景与目标

PRD §五非功能需求要求「儿童数据加密存储」「符合《儿童个人信息网络保护规定》」，
CLAUDE.md 价值观 #5 亦明确隐私保护。当前敏感数据在 SQLite/MySQL 中以明文存储。

本设计为最敏感的字段加上**字段级透明加密**：身份标识做不可逆哈希、可识别内容做
可逆加密，业务代码几乎不改。采用**渐进迁移**，不停机、不大爆炸。

不采用全库加密（SQLCipher）的原因：需更换数据库引擎并重新加密整库，对现有
SQLite/MySQL 双轨与渐进迁移不友好；字段级加密改动局部、按字段精准可控。

## 范围

**加密（Fernet 可逆，需展示的内容）**
| 模型.字段 | 理由 |
|---|---|
| `Student.name` | 孩子真实姓名 |
| `ChatHistory.content` | 孩子对话内容 |
| `Mistake.question_text / student_answer / correct_answer / explanation` | 学习内容 |

**哈希（HMAC-SHA256 不可逆，仅用于匹配、从不展示）**
| 模型.字段 | 理由 |
|---|---|
| `User.openid` | 微信身份标识，查找键 |
| `User.device_id` | 设备标识，查找键 |

**不处理（非 PII / YAGNI）**：`User.nickname`（通用"家长"）、`Mistake.topic`（类别）、
每日一练题目（AI 生成）、`avatar_url`、作业图片路径。

## 非目标（YAGNI / 后续项）

- 知识库 chromadb 文档仍明文（独立于加密 DB）——属"全面加密"，本次不做
- 作业图片 `uploads/` 仍明文落盘——同上
- 不改前端

## 架构

### 新增 `app/security/` 包

**`crypto.py`** —— 底层原语：
- `encrypt(text: str) -> str`：Fernet 加密，返回令牌字符串
- `decrypt(token: str) -> str`：Fernet 解密；非法令牌抛 `cryptography.fernet.InvalidToken`
- `hash_lookup(text: str) -> str`：HMAC-SHA256 十六进制（64 位小写 hex）
- 密钥：`_fernet`（Fernet 实例）与 `_hmac_key`（bytes）在模块加载时从 `DATA_ENCRYPTION_KEY`
  构建；未设则从 `JWT_SECRET` 派生：
  - Fernet key：`base64.urlsafe_b64encode(hashlib.sha256(("fernet:"+SECRET).encode()).digest())`
  - HMAC key：`hashlib.sha256(("hmac:"+SECRET).encode()).digest()`
  其中 `SECRET = DATA_ENCRYPTION_KEY or JWT_SECRET`

**`types.py`** —— 两个 SQLAlchemy `TypeDecorator`（透明列加解密）：
- `EncryptedText(TypeDecorator)`，`impl = Text`，`cache_ok = True`
  - `process_bind_param`：`None` 透传；否则返回 `crypto.encrypt(value)`
  - `process_result_value`：`None` 透传；否则 `try: crypto.decrypt(value) except InvalidToken: return value`（容错老明文）
- `HashedKey(TypeDecorator)`，`impl = String`，`cache_ok = True`
  - `process_bind_param`：`None` 透传；否则返回 `crypto.hash_lookup(value)`（INSERT 与 WHERE 比较都触发 → 查询透明匹配）
  - `process_result_value`：原样返回（哈希值，从不解密）

### 字段类型替换

把上表字段的列类型从 `Text/String` 改为 `EncryptedText` / `HashedKey`。
例：`openid = mapped_column(HashedKey(100), ...)`、`content = mapped_column(EncryptedText, ...)`。

业务查询无需改动：`select(User).where(User.openid == raw_openid)` 中 `raw_openid` 经
`HashedKey.process_bind_param` 自动哈希后与库中哈希比对，匹配照常。唯一约束因 HMAC
确定性而保持。

## 密钥管理

- `config.py` 新增 `DATA_ENCRYPTION_KEY = os.getenv("DATA_ENCRYPTION_KEY", "")`
- `main.py` 启动检查：非 DEBUG 且未设 `DATA_ENCRYPTION_KEY`（即在用 JWT 派生）时
  `logger.warning` 告警（沿用 JWT 默认密钥告警模式）
- ⚠️ **关键约束（写进 README 与告警）**：密钥一旦变更，所有密文不可解、所有哈希不再
  匹配。生产须设**固定**的 `DATA_ENCRYPTION_KEY` 并永不更换
- `.env.example` 新增：
  ```
  # 数据加密密钥（强烈建议生产设置且永不更换；不设则从 JWT_SECRET 派生）
  DATA_ENCRYPTION_KEY=
  ```

## 渐进迁移

存量数据通过两条路径覆盖：
1. **内容字段**：`EncryptedText` 读时容错（老明文照读），新写入即加密 → 自然渐进
2. **身份字段**：必须一次性哈希迁移，否则部署后老用户查不到（查询哈希值匹配不上明文）

**脚本 `scripts/migrate_encrypt.py`**（手动运行，走原生 SQL 绕开 ORM 类型，精确可控）：
- 默认：哈希存量 `users.openid` / `users.device_id`
  - 幂等：值已是 64 位小写 hex（`re.fullmatch(r'[0-9a-f]{64}', v)`）则跳过
- `--encrypt-content`：额外加密存量 `students.name`、`chat_history.content`、
  `mistakes.{question_text,student_answer,correct_answer,explanation}`
  - 幂等：值已以 `gAAAAA`（Fernet 令牌前缀）开头则跳过
- 通过 `app.database` 的同步/异步连接执行；逐行 SELECT 原文 → 计算 → UPDATE
- 运行前提示备份；打印每表处理行数

## 错误处理

- `decrypt` 遇非法令牌：`EncryptedText.process_result_value` 捕获 `InvalidToken` 返回原值（容错）
- `crypto` 模块加载时密钥构建失败：直接抛错（配置错误应尽早暴露）
- 迁移脚本逐行 try/except，单行失败记录并继续，最后汇总失败计数

## 测试（扩展 pytest）

`tests/test_crypto.py`：
- `encrypt` → `decrypt` 还原原文；中文与空串均可
- `decrypt` 非法令牌抛 `InvalidToken`
- `hash_lookup` 确定性（同输入同输出）、不同输入不同输出、输出为 64 位 hex

`tests/test_encrypted_types.py`（用 conftest 的临时库 + 真实模型）：
- `EncryptedText`：写入 `ChatHistory.content` 后读出还原；库内原始值非明文
- `EncryptedText` 容错：手工写入明文（绕 ORM）后经 ORM 读出得原明文
- `HashedKey`：建用户后用明文 `openid` 查询命中；库内 `openid` 为 64 位 hex
- 既有全套测试保持通过（透明加密不破坏现有读写）

迁移脚本以小型临时库做一次端到端测：插入明文行 → 跑迁移 → 身份哈希且明文查询命中；
二次跑幂等无变化。

## 验收标准

1. 选定字段在库中以密文/哈希存储，应用读写透明无感
2. 老明文内容仍可读（容错）；存量用户经身份迁移后登录/匹配正常
3. 未配 `DATA_ENCRYPTION_KEY` 时从 JWT 派生可用；生产用派生默认值时启动告警
4. 新增测试全部通过且既有测试不回归
5. README 与 `.env.example` 说明新配置与"密钥不可更换"约束；chromadb/图片明文边界已记录
