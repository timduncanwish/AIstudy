"""加密原语测试。"""
import re

import pytest
from cryptography.fernet import InvalidToken

from app.security import crypto


def test_encrypt_decrypt_roundtrip():
    for s in ["小明的作业", "hello", ""]:
        assert crypto.decrypt(crypto.encrypt(s)) == s


def test_encrypt_is_not_plaintext():
    token = crypto.encrypt("小明")
    assert "小明" not in token


def test_decrypt_invalid_raises():
    with pytest.raises(InvalidToken):
        crypto.decrypt("not-a-valid-token")


def test_hash_lookup_deterministic_and_hex():
    h = crypto.hash_lookup("wx_openid_abc")
    assert h == crypto.hash_lookup("wx_openid_abc")
    assert re.fullmatch(r"[0-9a-f]{64}", h)
    assert crypto.hash_lookup("a") != crypto.hash_lookup("b")


def test_rotation_old_key_still_decrypts(monkeypatch):
    # 用旧密钥加密的令牌，在「新,旧」多密钥下仍可解
    from cryptography.fernet import Fernet
    old_key = Fernet.generate_key()
    new_key = Fernet.generate_key()
    old_token = Fernet(old_key).encrypt("历史数据".encode()).decode()

    monkeypatch.setattr(crypto, "_multi", crypto._build_multifernet(
        [new_key.decode(), old_key.decode()]
    ))
    assert crypto.decrypt(old_token) == "历史数据"
