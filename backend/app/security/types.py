"""SQLAlchemy 透明加密列类型。"""
import re
import logging

from sqlalchemy import String, Text
from sqlalchemy.types import TypeDecorator
from cryptography.fernet import InvalidToken

from app.security import crypto

logger = logging.getLogger(__name__)
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
            # 看起来像 Fernet 令牌（gAAAAA 开头）却解不开 → 多半是密钥误配/误换，告警；
            # 否则视为存量明文，静默容错（迁移期不刷屏）
            if isinstance(value, str) and value.startswith("gAAAAA"):
                logger.warning("EncryptedText 解密失败（疑似 DATA_ENCRYPTION_KEY 配置错误），按原值返回")
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
