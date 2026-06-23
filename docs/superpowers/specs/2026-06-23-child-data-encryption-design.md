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

**加密（Fernet 可逆，需展示或需回传的数据）**
| 模型.字段 | 理由 |
|---|---|
| `User.openid` | 微信身份标识；**需回传微信推送订阅消息（touser=openid），必须可恢复** |
| `Student.name` | 孩子真实姓名 |
| `ChatHistory.content` | 孩子对话内容 |
| `Mistake.question_text / student_answer / correct_answer / explanation` | 学习内容 |

**哈希（HMAC-SHA256 不可逆，仅用于匹配、从不回传/展示）**
| 模型.字段 | 理由 |
|---|---|
| `User.openid_hash` | **新增列**：openid 的盲索引（blind index），供 `wx_login` 按 openid 查找 |
| `User.device_id` | 设备标识，仅内部匹配、从不回传 |

> **盲索引模式（修正）**：openid 既要按值查找（`wx_login`）又要回传给微信推送。哈希
> 不可恢复，无法回传；故 openid 本身用 `EncryptedText`（可恢复），另加 `openid_hash`
> （`HashedKey`）专供查找。device_id 仅内部匹配、从不回传，直接 `HashedKey` 即可。

**不处理（非 PII / YAGNI）**：`User.nickname`（通用"家长"）、`Mistake.topic`（类别）、
每日一练题目（AI 生成）、`avatar_url`、作业图片路径。

## 非目标（YAGNI / 后续项）

- 作业图片 `uploads/` 仍明文落盘——属"全面加密"，本次不做
- 不改前端

## 显式决策：chromadb 明文残留（接受残留风险）

知识库 chromadb 在 `chroma_data/` 中以明文存储错题文档。本设计**显式决定本次接受此
残留风险**，理由：

1. **活跃 AI 上下文检索走加密后的 SQL 路径**（`mistake_service.get_relevant_mistakes`），
   不读 chroma 文档；chroma 的 `search_relevant_mistakes` 当前是**未被调用的死代码**。
2. `chroma_data/` 是 gitignored 的**本地运行时数据**，不入库、不分发。
3. 全面保护 chroma/图片属用户已推迟的"全面加密"档。

**配套要求（写入 README）**：生产部署须对 `chroma_data/` 与 `uploads/` 目录做操作系统级
访问控制（限定服务账户、磁盘加密）。

**后续任务（记入待办，不在本次范围）**：知识库改为只存向量 + 加密的 mistake_id 引用，
检索时回查加密 DB，彻底消除 chroma 明文。

## 架构

### 新增 `app/security/` 包

**`crypto.py`** —— 底层原语：
- `encrypt(text: str) -> str`：用**主密钥** Fernet 加密，返回令牌字符串
- `decrypt(token: str) -> str`：用 `MultiFernet` 解密（依次尝试所有密钥）；非法令牌抛 `cryptography.fernet.InvalidToken`
- `hash_lookup(text: str) -> str`：HMAC-SHA256 十六进制（64 位小写 hex）
- **密钥轮换支持（建议2）**：`DATA_ENCRYPTION_KEY` 支持逗号分隔多个密钥——
  **第一个为主密钥（加密用）**，全部组成 `MultiFernet`（解密用，老密文用旧密钥仍可解）。
  轮换流程：把新密钥放第一位、旧密钥保留在后，逐步用 `--encrypt-content` 重写即完成。
- 密钥构建：模块加载时从 `DATA_ENCRYPTION_KEY`（逗号分隔列表）构建 `MultiFernet`；
  未设则从 `JWT_SECRET` 派生单个 Fernet key。HMAC key 始终从 `DATA_ENCRYPTION_KEY`
  首段（或 `JWT_SECRET`）派生，**注意：HMAC 哈希字段不支持轮换**（HMAC 本性，换 key 即全部失配）。
  - 派生：`fernet_key = base64.urlsafe_b64encode(hashlib.sha256(("fernet:"+SECRET).encode()).digest())`、
    `hmac_key = hashlib.sha256(("hmac:"+SECRET).encode()).digest()`，
    其中 `SECRET = DATA_ENCRYPTION_KEY 首段 or JWT_SECRET`

**`types.py`** —— 两个 SQLAlchemy `TypeDecorator`（透明列加解密）：
- `EncryptedText(TypeDecorator)`，`impl = Text`，`cache_ok = True`
  - `process_bind_param`：`None` 透传；否则返回 `crypto.encrypt(value)`
  - `process_result_value`：`None` 透传；否则 `try: crypto.decrypt(value) except InvalidToken: return value`（容错老明文）
- `HashedKey(TypeDecorator)`，`impl = String`，`cache_ok = True`
  - `process_bind_param`：`None` 透传；**值已是 64 位小写 hex（`re.fullmatch(r'[0-9a-f]{64}', value)`）则原样返回（建议1：幂等守卫）**；否则返回 `crypto.hash_lookup(value)`（INSERT 与 WHERE 比较都触发 → 查询透明匹配）
  - `process_result_value`：原样返回（哈希值，从不解密）
  - **幂等守卫的两个作用**：① 消除"读出哈希→回写被二次哈希"的往返陷阱（openid/device_id 原值不可能是 64 位 hex，安全）；② 天然成为迁移脚本的幂等判据

### 字段类型替换

把内容字段列类型改为 `EncryptedText`（impl=Text，无长度限制——密文比原文长，
`Student.name` 原 `String(50)` 必须换成 `EncryptedText`）：
- `User.openid`（原 `String(100)` → `EncryptedText`）
- `Student.name`、`ChatHistory.content`、`Mistake` 四个文本字段

把查找字段改为 `HashedKey`（impl=String，存 64 位 hex）：
- `User.device_id`（`HashedKey(64)`）
- **新增** `User.openid_hash = mapped_column(HashedKey(64), unique=True, nullable=True, index=True)`

### wx_login 与 init_db 改动

- `wx_login` 查找由 `where(User.openid == openid)` 改为 `where(User.openid_hash == openid)`
  （`HashedKey` 自动哈希 `openid` 后比对盲索引）。建用户时同时设
  `openid=openid`（加密存）与 `openid_hash=openid`（哈希存）。
- `device_id` 查找（`get_or_create_user` 的 `where(User.device_id == device_id)`）无需改动：
  `HashedKey` 自动哈希比对，匹配照常。
- `database.init_db` 增加幂等 `ALTER TABLE users ADD COLUMN openid_hash VARCHAR(64)`
  （沿用现有 try/except 幂等迁移块）。
- 唯一约束因 HMAC 确定性而保持（device_id、openid_hash）。

其余内容字段的业务读写无需改动：`EncryptedText` 透明加解密。

## 密钥管理

- `config.py` 新增 `DATA_ENCRYPTION_KEY = os.getenv("DATA_ENCRYPTION_KEY", "")`
- `main.py` 启动检查：非 DEBUG 且未设 `DATA_ENCRYPTION_KEY`（即在用 JWT 派生）时
  `logger.warning` 告警（沿用 JWT 默认密钥告警模式）
- ⚠️ **关键约束（写进 README 与告警）**：密钥一旦变更，所有密文不可解、所有哈希不再
  匹配。生产须设**固定**的 `DATA_ENCRYPTION_KEY` 并永不更换
- `.env.example` 新增：
  ```
  # 数据加密密钥（强烈建议生产设置；不设则从 JWT_SECRET 派生）
  # 支持逗号分隔多个密钥做轮换：第一个加密、全部用于解密（旧密文仍可解）
  # 注意：HMAC 哈希字段（openid/device_id）不支持轮换，更换会导致这些字段全部失配
  DATA_ENCRYPTION_KEY=
  ```

## 渐进迁移

存量数据通过两条路径覆盖：
1. **内容字段**：`EncryptedText` 读时容错（老明文照读），新写入即加密 → 自然渐进
2. **查找字段（必跑迁移）**：`device_id` 必须哈希、`openid_hash` 必须从存量 openid 回填，
   否则部署后老用户查不到（查询哈希/盲索引匹配不上）

**脚本 `scripts/migrate_encrypt.py`**（手动运行，走原生 SQL 绕开 ORM 类型，精确可控）：
- 默认（查找字段，必跑）：
  - 哈希存量 `users.device_id`（幂等：值已是 64 位 hex 则跳过）
  - 从存量 `users.openid` 明文回填 `users.openid_hash = hmac(openid)`
    （幂等：该行 openid_hash 已非空则跳过；openid 为 NULL 的匿名用户跳过）
- `--encrypt-content`：额外加密存量 `users.openid`、`students.name`、`chat_history.content`、
  `mistakes.{question_text,student_answer,correct_answer,explanation}`
  - **幂等（建议3）**：尝试 `crypto.decrypt(v)`，成功即说明已是密文 → 跳过（比前缀启发式可靠）
  - 注意：openid 回填 openid_hash 用的是**明文** openid，故必须**先回填 openid_hash 再加密 openid**
    （脚本内保证顺序：默认段先跑，`--encrypt-content` 段后跑）
- **安全措施（建议3）**：
  - `--dry-run`：只扫描并打印每表将处理的行数，不写库
  - 每表操作用一个事务包裹，整表成功才提交，失败回滚
  - 逐行 try/except，单行失败记录并继续，结束汇总成功/跳过/失败计数
- 通过 `app.database` 的连接执行；逐行 SELECT 原文 → 计算 → UPDATE
- 运行前提示**先备份数据库**

## 错误处理

- `decrypt` 遇非法令牌：`EncryptedText.process_result_value` 捕获 `InvalidToken` 返回原值（容错）
- `crypto` 模块加载时密钥构建失败：直接抛错（配置错误应尽早暴露）
- 迁移脚本逐行 try/except，单行失败记录并继续，最后汇总失败计数

## 测试（扩展 pytest）

`tests/test_crypto.py`：
- `encrypt` → `decrypt` 还原原文；中文与空串均可
- `decrypt` 非法令牌抛 `InvalidToken`
- `hash_lookup` 确定性（同输入同输出）、不同输入不同输出、输出为 64 位 hex
- **轮换（建议2）**：用「新,旧」两个密钥构建后，旧密钥加密的密文仍能 `decrypt`；新加密用首个密钥

`tests/test_encrypted_types.py`（用 conftest 的临时库 + 真实模型）：
- `EncryptedText`：写入 `ChatHistory.content` 后读出还原；库内原始值非明文
- `EncryptedText` 容错：手工写入明文（绕 ORM）后经 ORM 读出得原明文
- **openid 盲索引**：建用户（设 `openid` 与 `openid_hash` 同为明文）后，用明文
  `where(User.openid_hash == raw_openid)` 查询命中；读出的 `user.openid` 还原为明文
  （可回传微信）；库内 `openid` 为密文、`openid_hash` 为 64 位 hex
- `HashedKey`：用明文 `device_id` 查询命中；库内 `device_id` 为 64 位 hex
- **HashedKey 幂等（建议1）**：对已是 64 位 hex 的值再次 `process_bind_param` 不变（不二次哈希）
- 既有全套测试保持通过（透明加密不破坏现有读写）

迁移脚本测试（小型临时库端到端）：
- 插入明文行 → 跑迁移 → 身份哈希且明文查询命中；二次跑幂等无变化
- **`--dry-run`（建议3）**：只统计不改库（跑后原始明文不变）

## 验收标准

1. 选定字段在库中以密文/哈希存储，应用读写透明无感
2. 老明文内容仍可读（容错）；存量用户经查找字段迁移后登录/匹配正常
2b. `openid` 可解密回传微信推送（`user.openid` 读出为明文）；`wx_login` 按 `openid_hash` 查找命中
3. 未配 `DATA_ENCRYPTION_KEY` 时从 JWT 派生可用；生产用派生默认值时启动告警
4. 新增测试全部通过且既有测试不回归
5. README 与 `.env.example` 说明新配置与"密钥不可更换"约束；chromadb/图片明文边界已记录
