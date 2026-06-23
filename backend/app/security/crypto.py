"""数据加密原语：Fernet 可逆加密（支持密钥轮换）+ HMAC 不可逆哈希。"""
import base64
import hashlib
import hmac

from cryptography.fernet import Fernet, MultiFernet

from app.config import DATA_ENCRYPTION_KEY, JWT_SECRET


def _derive_fernet_key(secret: str) -> bytes:
    return base64.urlsafe_b64encode(hashlib.sha256(("fernet:" + secret).encode()).digest())


def _build_multifernet(keys: list[str]) -> MultiFernet:
    return MultiFernet([Fernet(k.encode() if isinstance(k, str) else k) for k in keys])


# 密钥来源：DATA_ENCRYPTION_KEY（逗号分隔）首段为主密钥；未设则从 JWT_SECRET 派生
if DATA_ENCRYPTION_KEY.strip():
    _keys = [k.strip() for k in DATA_ENCRYPTION_KEY.split(",") if k.strip()]
    _primary_secret = _keys[0]
else:
    _keys = [_derive_fernet_key(JWT_SECRET).decode()]
    _primary_secret = JWT_SECRET

_multi = _build_multifernet(_keys)
_hmac_key = hashlib.sha256(("hmac:" + _primary_secret).encode()).digest()


def encrypt(text: str) -> str:
    return _multi.encrypt(text.encode("utf-8")).decode("ascii")


def decrypt(token: str) -> str:
    return _multi.decrypt(token.encode("ascii")).decode("utf-8")


def hash_lookup(text: str) -> str:
    return hmac.new(_hmac_key, text.encode("utf-8"), hashlib.sha256).hexdigest()
