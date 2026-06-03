# SPEC.md — AI助学技术开发规范

## 一、后端规范

### 技术栈
- Python 3.14 + FastAPI
- 智谱AI API (GLM-4-flash)，通过 OpenAI SDK 兼容调用
- SQLite (开发) / MySQL (生产)

### 目录约定

```
backend/
├── app/
│   ├── main.py          # FastAPI入口，注册中间件和路由
│   ├── config.py        # 环境变量读取（不使用pydantic-settings）
│   ├── routers/         # 按功能分文件：chat.py, homework.py, auth.py ...
│   ├── services/        # 业务逻辑：ai_service.py, ocr_service.py ...
│   ├── models/          # SQLAlchemy数据模型
│   └── schemas/         # Pydantic请求/响应模型
├── requirements.txt     # 不锁定小版本，保持兼容
└── .env                 # 本地配置，不入版本控制
```

### API设计规范

- RESTful风格，路由前缀按模块划分（`/chat`, `/homework`, `/auth`）
- 请求/响应统一使用 Pydantic model 校验
- 错误响应使用 HTTPException，附带中文 detail
- 所有接口支持 CORS（小程序需要）

```python
# 请求示例
POST /chat
{
    "messages": [{"role": "user", "content": "..."}],
    "subject": "chinese",   # chinese | english
    "grade": 3              # 3 | 4 | 5 | 6
}

# 响应示例
{
    "reply": "AI回复内容",
    "subject": "chinese"
}
```

### 智谱AI调用规范

- 使用 `openai` SDK，base_url 指向 `https://open.bigmodel.cn/api/paas/v4/`
- 默认模型：`glm-4-flash`（快速、低成本）
- system prompt 按科目+年级动态生成
- max_tokens: 1024, temperature: 0.7
- API Key 存放在 `.env`，代码中不硬编码

### 配置管理

```python
# config.py 使用 python-dotenv，不使用 pydantic-settings（Python 3.14兼容性问题）
from dotenv import load_dotenv
load_dotenv()
API_KEY = os.getenv("ZHIPU_API_KEY", "")
```

---

## 二、前端规范

### 技术栈
- uni-app + Vue 3 Composition API (`<script setup lang="ts">`)
- TypeScript
- 微信小程序目标平台

### 页面开发约定

- 每个页面一个文件夹：`pages/[name]/index.vue`
- 使用 `<script setup lang="ts">` + `<style scoped>`
- 样式单位用 `rpx`（响应式像素）
- 颜色主题：主色 `#4A90D9`，辅色 `#FF8E53`

### API调用

```typescript
// 使用 uni.request，封装在 api/ 目录下
const res = await uni.request({
    url: 'http://localhost:8000/chat',
    method: 'POST',
    data: { messages, subject, grade },
})
```

- 开发环境后端地址：`http://localhost:8000`
- 生产环境需替换为备案域名

### 路由配置

```json
// pages.json 管理所有页面路由和 tabBar
{
    "pages": [...],
    "globalStyle": { ... },
    "tabBar": { ... }
}
```

---

## 三、数据模型设计（二期+）

### users 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 用户ID |
| openid | TEXT UNIQUE | 微信openid |
| nickname | TEXT | 昵称 |
| avatar_url | TEXT | 头像 |
| created_at | DATETIME | 创建时间 |

### students 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 学生ID |
| user_id | INTEGER FK | 关联家长 |
| name | TEXT | 学生姓名 |
| grade | INTEGER | 年级(3-6) |
| avatar | TEXT | 头像标识 |

### chat_history 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 记录ID |
| student_id | INTEGER FK | 关联学生 |
| subject | TEXT | 科目 |
| role | TEXT | user/assistant |
| content | TEXT | 对话内容 |
| created_at | DATETIME | 时间 |

### mistakes 表（错题本）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 错题ID |
| student_id | INTEGER FK | 关联学生 |
| subject | TEXT | 科目 |
| question | TEXT | 题目 |
| wrong_answer | TEXT | 错误答案 |
| correct_answer | TEXT | 正确答案 |
| explanation | TEXT | 讲解 |
| mastery_level | INTEGER | 掌握度(0-5) |
| next_review | DATETIME | 下次复习时间 |

### word_progress 表（闯关进度）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | |
| student_id | INTEGER FK | |
| word | TEXT | 生字/单词 |
| subject | TEXT | 科目 |
| level | INTEGER | 掌握等级(0-4) |
| review_count | INTEGER | 复习次数 |
| next_review | DATETIME | |

---

## 四、部署方案

### 开发环境
- 后端：`python -m uvicorn app.main:app --reload`
- 前端：`npm run dev:mp-weixin` → 微信开发者工具打开 `dist/dev/mp-weixin`

### 生产环境
- 服务器：腾讯云轻量应用服务器
- 域名：需备案（微信小程序要求 https + 备案域名）
- 后端部署：uvicorn + nginx反向代理
- 数据库：MySQL 8.0
- 图片存储：腾讯云COS

---

## 五、关键依赖版本

### 后端 requirements.txt
```
fastapi==0.115.0
uvicorn==0.30.0
httpx==0.27.0
python-dotenv==1.0.1
openai==1.47.0
```

### 前端核心依赖
```
vue: ^3.4.21
@dcloudio/uni-app: 3.0.0-4080420251103001
typescript: ^4.9.4
vite: 5.2.8
```

> 注意：不使用 pydantic-settings，因为 Python 3.14 的 pydantic-core wheel 编译存在问题。
