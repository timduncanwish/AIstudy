import os
import logging
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.limiter import limiter

from app.config import APP_HOST, APP_PORT, DEBUG, ALLOWED_ORIGINS, JWT_SECRET, DEFAULT_JWT_SECRET
from app.routers import auth, chat, homework, mistakes, challenge, students, reports, practice, notify
from app.database import init_db, get_db_context

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()

os.makedirs("uploads", exist_ok=True)
os.makedirs("chroma_data", exist_ok=True)

app = FastAPI(title="AI助学", description="小学3-6年级AI辅导助手")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    # 通配来源时凭证必须关闭（CORS 规范不允许 * + credentials）；
    # 本应用用 Bearer 头鉴权而非 cookie，关闭无影响。
    allow_credentials=ALLOWED_ORIGINS != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(homework.router)
app.include_router(mistakes.router)
app.include_router(challenge.router)
app.include_router(students.router)
app.include_router(reports.router)
app.include_router(practice.router)
app.include_router(notify.router)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


async def _daily_push_job():
    hhmm = datetime.now().strftime("%H:%M")
    try:
        async with get_db_context() as db:
            from app.services.notify_service import get_subscribed_users_for_time, notify_daily_summary
            from app.services.report_service import get_daily_report
            users = await get_subscribed_users_for_time(db, hhmm)
            today = datetime.now().strftime("%Y-%m-%d")
            for user in users:
                try:
                    report = await get_daily_report(db, user.id, today)
                    weak = report["weak_topics"][0]["topic"] if report["weak_topics"] else ""
                    await notify_daily_summary(
                        openid=user.openid,
                        nickname=user.nickname,
                        homework_count=report["homework_count"],
                        mistakes_count=report["mistakes_count"],
                        weak_topic=weak,
                    )
                except Exception:
                    logger.exception("daily push failed for user %s", user.id)
    except Exception:
        logger.exception("daily push job error")


@app.on_event("startup")
async def startup():
    if not DEBUG and JWT_SECRET == DEFAULT_JWT_SECRET:
        logger.warning(
            "⚠️ 生产环境仍在使用默认 JWT_SECRET！任何人可伪造登录令牌，"
            "请在 .env 设置强随机的 JWT_SECRET。"
        )
    await init_db()
    scheduler.add_job(_daily_push_job, "cron", minute="*")  # 每分钟检查一次
    scheduler.start()


@app.on_event("shutdown")
async def shutdown():
    scheduler.shutdown(wait=False)


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=APP_HOST,
        port=APP_PORT,
        reload=DEBUG,
    )
