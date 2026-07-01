"""此前完全没有测试的一块：登录换 token、token 校验。

微信 code2session 走真实 HTTP 请求，测试环境没配 WX_APPID/WX_SECRET，
_code2session 会走 mock 分支（见 auth_service.py:49-50），所以这里能测完整
的 wx_login 流程而不用真的打微信的接口。
"""
import jwt
import pytest

from app.services.auth_service import wx_login, verify_token, _generate_token
from app.config import JWT_SECRET


async def test_wx_login_creates_new_user_with_mock_openid(db):
    result = await wx_login(db, code="code123", nickname="张爸爸", avatar="http://a.png")

    assert result["is_new_user"] is True
    assert result["nickname"] == "张爸爸"
    assert isinstance(result["user_id"], int)
    assert verify_token(result["token"]) == result["user_id"]


async def test_wx_login_same_code_returns_same_user_not_new(db):
    first = await wx_login(db, code="code123", nickname="张爸爸")
    second = await wx_login(db, code="code123", nickname="张爸爸")

    assert second["is_new_user"] is False
    assert second["user_id"] == first["user_id"]


async def test_wx_login_updates_nickname_and_avatar_on_relogin(db):
    first = await wx_login(db, code="codeXYZ", nickname="家长")
    second = await wx_login(db, code="codeXYZ", nickname="李妈妈", avatar="http://b.png")

    assert second["user_id"] == first["user_id"]
    assert second["nickname"] == "李妈妈"


async def test_verify_token_returns_none_for_garbage():
    assert verify_token("not-a-real-token") is None


async def test_verify_token_returns_none_for_wrong_secret():
    token = jwt.encode({"user_id": 1}, "some-other-secret", algorithm="HS256")
    assert verify_token(token) is None


async def test_verify_token_returns_none_for_expired_token():
    from datetime import datetime, timedelta, timezone

    expired = jwt.encode(
        {"user_id": 42, "exp": datetime.now(timezone.utc) - timedelta(days=1)},
        JWT_SECRET,
        algorithm="HS256",
    )
    assert verify_token(expired) is None


async def test_generate_and_verify_token_roundtrip():
    token = _generate_token(99)
    assert verify_token(token) == 99
