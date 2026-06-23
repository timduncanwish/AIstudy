import os

from dotenv import load_dotenv

load_dotenv()

ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY", "")
ZHIPU_BASE_URL = os.getenv("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/")
ZHIPU_MODEL = os.getenv("ZHIPU_MODEL", "glm-4-flash")
ZHIPU_EMBEDDING_MODEL = os.getenv("ZHIPU_EMBEDDING_MODEL", "embedding-3")
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_data")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./ai_tutor.db")

APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8000"))
DEBUG = os.getenv("DEBUG", "True").lower() == "true"

WX_APPID = os.getenv("WX_APPID", "")
WX_SECRET = os.getenv("WX_SECRET", "")

# 百度OCR（可选；不配则作业批改仅用视觉模型）
BAIDU_OCR_API_KEY = os.getenv("BAIDU_OCR_API_KEY", "")
BAIDU_OCR_SECRET_KEY = os.getenv("BAIDU_OCR_SECRET_KEY", "")

DEFAULT_JWT_SECRET = "ai_tutor_secret_key_change_in_prod"
JWT_SECRET = os.getenv("JWT_SECRET", DEFAULT_JWT_SECRET)

# CORS 允许来源，逗号分隔；默认 * 便于开发，生产应在 .env 设具体域名
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()]

# 微信订阅消息模板 ID（在 MP 后台申请后填入）
WX_TMPL_PRACTICE = os.getenv("WX_TMPL_PRACTICE", "")   # 即时：练习完成简报
WX_TMPL_DAILY    = os.getenv("WX_TMPL_DAILY", "")       # 定时：每日学习汇总
