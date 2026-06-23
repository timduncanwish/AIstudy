import time
import logging

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import WX_APPID, WX_SECRET, WX_TMPL_PRACTICE, WX_TMPL_DAILY
from app.models.user import User

logger = logging.getLogger(__name__)

_token_cache: dict = {"token": "", "expires_at": 0}


async def _get_access_token() -> str:
    if _token_cache["token"] and time.time() < _token_cache["expires_at"]:
        return _token_cache["token"]

    if not WX_APPID or not WX_SECRET:
        return ""

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.weixin.qq.com/cgi-bin/token",
            params={"grant_type": "client_credential", "appid": WX_APPID, "secret": WX_SECRET},
        )
        data = resp.json()

    token = data.get("access_token", "")
    expires_in = data.get("expires_in", 7200)
    _token_cache["token"] = token
    _token_cache["expires_at"] = time.time() + expires_in - 300  # 提前 5 分钟刷新
    return token


async def send_subscribe_msg(openid: str, template_id: str, data: dict) -> bool:
    if not openid or not template_id:
        logger.debug("notify skip: openid=%s tmpl=%s", openid, template_id)
        return False

    token = await _get_access_token()
    if not token:
        logger.warning("notify skip: no access_token (WX_APPID/WX_SECRET not configured)")
        return False

    payload = {"touser": openid, "template_id": template_id, "data": data}
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://api.weixin.qq.com/cgi-bin/message/subscribe/send?access_token={token}",
            json=payload,
        )
        result = resp.json()

    if result.get("errcode", 0) != 0:
        logger.warning("notify failed: %s", result)
        return False
    return True


async def notify_practice_done(
    openid: str, subject: str, topic: str, score: int, total: int
) -> None:
    subject_label = "语文" if subject == "chinese" else "英语"
    data = {
        "thing1": {"value": f"{subject_label} · {topic}"},
        "number2": {"value": f"{score}/{total}"},
        "thing3": {"value": "太棒了！继续保持！" if score >= total * 0.8 else "再练练，会越来越好的！"},
    }
    await send_subscribe_msg(openid, WX_TMPL_PRACTICE, data)


async def notify_daily_summary(
    openid: str, nickname: str, homework_count: int, mistakes_count: int, weak_topic: str
) -> None:
    data = {
        "name1": {"value": nickname},
        "number2": {"value": str(homework_count)},
        "number3": {"value": str(mistakes_count)},
        "thing4": {"value": weak_topic or "综合练习"},
    }
    await send_subscribe_msg(openid, WX_TMPL_DAILY, data)


async def get_subscribed_users_for_time(db: AsyncSession, hhmm: str) -> list[User]:
    result = await db.execute(
        select(User).where(
            User.notify_subscribed == 1,
            User.notify_time == hhmm,
            User.openid.isnot(None),
        )
    )
    return list(result.scalars().all())
