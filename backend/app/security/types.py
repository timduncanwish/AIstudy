"""SQLAlchemy 透明加密列类型。"""
import re

from sqlalchemy import String, Text
from sqlalchemy.types import TypeDecorator
from cryptography.fernet import InvalidToken

from app.security import crypto

_HEX64 = re.compile(r"[0-9a-f]{64}")


class EncryptedText(TypeDecorator):
    """写时 Fernet 加密、读时解密；解密失败返回原值（容错老明文）。"""
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return crypto.encrypt(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        try:
            return crypto.decrypt(value)
        except (InvalidToken, UnicodeEncodeError, UnicodeDecodeError):
            return value


class HashedKey(TypeDecorator):
    """写入与查询比较都做 HMAC 哈希（透明匹配）；幂等：已是 64 位 hex 则不再哈希。"""
    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if _HEX64.fullmatch(value):
            return value
        return crypto.hash_lookup(value)

    def process_result_value(self, value, dialect):
        return value
