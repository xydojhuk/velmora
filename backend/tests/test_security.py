import os

os.environ.setdefault("JWT_SECRET", 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_!@#$%^&*()')
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///./test_security.db")

from app.security import decode_token, hash_password, verify_password


def test_password_hash_roundtrip():
    raw = "Strong-Test-Password-2026!"
    hashed = hash_password(raw)
    assert raw not in hashed
    valid, _ = verify_password(raw, hashed)
    assert valid is True
    invalid, _ = verify_password("wrong-password", hashed)
    assert invalid is False
