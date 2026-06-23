from datetime import datetime, timedelta, timezone

import jwt
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import WX_APPID, WX_SECRET, JWT_SECRET
from app.models.user import User


async def wx_login(db: AsyncSession, code: str, nickname: str = "家长", avatar: str = "") -> dict:
    openid = await _code2session(code)

    result = await db.execute(select(User).where(User.openid_hash == openid))
    user = result.scalar_one_or_none()

    is_new = False
    if not user:
        device_id = f"wx_{openid[:16]}"
        user = User(
            device_id=device_id,
            openid=openid,
            openid_hash=openid,
            nickname=nickname,
            avatar_url=avatar or "",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        is_new = True
    else:
        if nickname != "家长":
            user.nickname = nickname
        if avatar:
            user.avatar_url = avatar
        await db.commit()

    token = _generate_token(user.id)
    return {
        "token": token,
        "user_id": user.id,
        "is_new_user": is_new,
        "nickname": user.nickname,
    }


async def _code2session(code: str) -> str:
    if not WX_APPID or not WX_SECRET:
        return f"mock_openid_{code}"

    url = "https://api.weixin.qq.com/sns/jscode2session"
    params = {
        "appid": WX_APPID,
        "secret": WX_SECRET,
        "js_code": code,
        "grant_type": "authorization_code",
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params)
        data = resp.json()

    if "openid" not in data:
        raise ValueError(f"微信登录失败: {data.get('errmsg', 'unknown error')}")

    return data["openid"]


def _generate_token(user_id: int) -> str:
    payload = {
        "user_id": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=30),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def verify_token(token: str) -> int | None:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload.get("user_id")
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None
