import hashlib
import ipaddress
import re
import secrets
import uuid
from datetime import UTC, datetime

from fastapi import Request

from app.config import settings


_control_chars = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def utcnow() -> datetime:
    return datetime.now(UTC)


def clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    return _control_chars.sub("", value).strip()


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def random_token(bytes_count: int = 32) -> str:
    return secrets.token_urlsafe(bytes_count)


def new_order_number() -> str:
    stamp = utcnow().strftime("%y%m%d")
    return f"VD-{stamp}-{secrets.token_hex(6).upper()}"


def request_id() -> str:
    return uuid.uuid4().hex


def normalize_ip(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return str(ipaddress.ip_address(value.strip()))
    except ValueError:
        return None


def get_client_ip(request: Request) -> str | None:
    if settings.trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            candidate = normalize_ip(forwarded.split(",")[0])
            if candidate:
                return candidate
        real_ip = normalize_ip(request.headers.get("x-real-ip"))
        if real_ip:
            return real_ip
    if request.client:
        return normalize_ip(request.client.host)
    return None


def get_user_agent(request: Request) -> str | None:
    value = request.headers.get("user-agent")
    if not value:
        return None
    return clean_text(value)[:512]
