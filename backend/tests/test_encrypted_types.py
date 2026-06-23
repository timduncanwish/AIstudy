"""TypeDecorator 单元测试：直接测 bind/result 处理逻辑。"""
from app.security.types import EncryptedText, HashedKey
from app.security import crypto


def test_encrypted_text_bind_then_result_roundtrip():
    t = EncryptedText()
    stored = t.process_bind_param("小明的对话", None)
    assert stored is not None and "小明的对话" not in stored
    assert t.process_result_value(stored, None) == "小明的对话"


def test_encrypted_text_none_passthrough():
    t = EncryptedText()
    assert t.process_bind_param(None, None) is None
    assert t.process_result_value(None, None) is None


def test_encrypted_text_tolerates_legacy_plaintext():
    t = EncryptedText()
    # 老明文（非合法令牌）读出原样返回
    assert t.process_result_value("老明文内容", None) == "老明文内容"


def test_hashed_key_hashes_on_bind():
    k = HashedKey(64)
    stored = k.process_bind_param("wx_openid_abc", None)
    assert stored == crypto.hash_lookup("wx_openid_abc")
    assert k.process_result_value(stored, None) == stored  # 读出即哈希


def test_hashed_key_idempotent_on_existing_hash():
    k = HashedKey(64)
    once = k.process_bind_param("wx_openid_abc", None)
    twice = k.process_bind_param(once, None)  # 已是 64 位 hex，不再哈希
    assert twice == once


def test_hashed_key_none_passthrough():
    k = HashedKey(64)
    assert k.process_bind_param(None, None) is None
