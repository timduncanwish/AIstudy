"""百度OCR手写文字识别。可选增强，任何失败返回 ""，由调用方退回纯视觉批改。"""
import base64
import time
import logging

import httpx

from app.config import BAIDU_OCR_API_KEY, BAIDU_OCR_SECRET_KEY

logger = logging.getLogger(__name__)

_TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"
_OCR_URL = "https://aip.baidubce.com/rest/2.0/ocr/v1/handwriting"

_token_cache: dict = {"token": "", "expires_at": 0}


async def _get_access_token() -> str:
    if _token_cache["token"] and time.time() < _token_cache["expires_at"]:
        return _token_cache["token"]
    if not BAIDU_OCR_API_KEY or not BAIDU_OCR_SECRET_KEY:
        return ""
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(_TOKEN_URL, params={
                "grant_type": "client_credentials",
                "client_id": BAIDU_OCR_API_KEY,
                "client_secret": BAIDU_OCR_SECRET_KEY,
            })
            data = resp.json()
    except Exception:
        logger.warning("baidu ocr token request failed", exc_info=True)
        return ""
    token = data.get("access_token", "")
    expires_in = data.get("expires_in", 2592000)
    if token:
        _token_cache["token"] = token
        _token_cache["expires_at"] = time.time() + expires_in - 86400  # 提前1天刷新
    return token


async def recognize_text(image_bytes: bytes) -> str:
    if not BAIDU_OCR_API_KEY or not BAIDU_OCR_SECRET_KEY:
        return ""
    token = await _get_access_token()
    if not token:
        return ""
    try:
        img_b64 = base64.b64encode(image_bytes).decode("utf-8")
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.post(
                _OCR_URL,
                params={"access_token": token},
                data={"image": img_b64},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            data = resp.json()
    except Exception:
        logger.warning("baidu ocr request failed", exc_info=True)
        return ""
    words = data.get("words_result") or []
    lines = [w.get("words", "") for w in words if w.get("words")]
    return "\n".join(lines)
