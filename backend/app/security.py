import hmac
import re
import uuid
from datetime import timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from fastapi import HTTPException, Request, Response, status
from jwt import InvalidTokenError

from app.config import settings
from app.utils import random_token, sha256_hex, utcnow


password_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4, hash_len=32, salt_len=16)


def validate_password_policy(password: str, email: str | None = None) -> None:
    if len(password) < 12 or len(password) > 128:
        raise ValueError("Password must contain 12 to 128 characters")
    categories = sum(
        bool(pattern.search(password))
        for pattern in (
            re.compile(r"[a-z]"),
            re.compile(r"[A-Z]"),
            re.compile(r"\d"),
            re.compile(r"[^A-Za-z0-9]"),
        )
    )
    if categories < 3:
        raise ValueError("Password must contain at least three character categories")
    if email:
        local = email.split("@", 1)[0].lower()
        if len(local) >= 4 and local in password.lower():
            raise ValueError("Password must not contain part of the email address")


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> tuple[bool, bool]:
    try:
        valid = password_hasher.verify(password_hash, password)
        return valid, valid and password_hasher.check_needs_rehash(password_hash)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False, False


def _encode(payload: dict[str, Any]) -> str:
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def create_access_token(user_id: uuid.UUID, session_id: uuid.UUID, role: str) -> str:
    now = utcnow()
    return _encode(
        {
            "sub": str(user_id),
            "sid": str(session_id),
            "role": role,
            "typ": "access",
            "jti": str(uuid.uuid4()),
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "iat": now,
            "nbf": now,
            "exp": now + timedelta(minutes=settings.access_token_minutes),
        }
    )


def create_refresh_token(user_id: uuid.UUID, session_id: uuid.UUID, jti: str, expires_at=None) -> str:
    now = utcnow()
    expiry = expires_at or (now + timedelta(days=settings.refresh_token_days))
    return _encode(
        {
            "sub": str(user_id),
            "sid": str(session_id),
            "typ": "refresh",
            "jti": jti,
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "iat": now,
            "nbf": now,
            "exp": expiry,
        }
    )


def decode_token(token: str, expected_type: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "iat", "nbf", "iss", "aud", "sub", "sid", "jti", "typ"]},
        )
    except InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="The session is invalid or has expired") from exc
    if payload.get("typ") != expected_type:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    return payload


def new_csrf_token() -> str:
    return random_token(32)


def verify_csrf(raw_token: str | None, stored_hash: str) -> bool:
    if not raw_token:
        return False
    return hmac.compare_digest(sha256_hex(raw_token), stored_hash)


def set_auth_cookies(response: Response, access_token: str, refresh_token: str, csrf_token: str) -> None:
    secure = settings.cookie_secure
    common = {"secure": secure, "samesite": settings.cookie_samesite, "path": "/"}
    response.set_cookie(
        key=settings.cookie_access_name,
        value=access_token,
        httponly=True,
        max_age=settings.access_token_minutes * 60,
        **common,
    )
    response.set_cookie(
        key=settings.cookie_refresh_name,
        value=refresh_token,
        httponly=True,
        max_age=settings.refresh_token_days * 86400,
        **common,
    )
    response.set_cookie(
        key=settings.cookie_csrf_name,
        value=csrf_token,
        httponly=False,
        max_age=settings.refresh_token_days * 86400,
        **common,
    )


def clear_auth_cookies(response: Response) -> None:
    for key in (settings.cookie_access_name, settings.cookie_refresh_name, settings.cookie_csrf_name):
        response.delete_cookie(key=key, path="/", secure=settings.cookie_secure, samesite=settings.cookie_samesite)


def enforce_allowed_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if origin and origin not in settings.cors_origins:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This request origin is not allowed")
