from __future__ import annotations

import asyncio
import hashlib
import hmac
import ipaddress
import json
import logging
import os
import re
import secrets
import socket
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

import psycopg
from fastapi import Cookie, FastAPI, Header, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from psycopg import sql

APP_VERSION = "0.1.0-alpha.1"
CONFIG_DIR = Path(os.getenv("VELMORA_RUNTIME_CONFIG_DIR", "/runtime/config"))
SECRETS_DIR = Path(os.getenv("VELMORA_RUNTIME_SECRETS_DIR", "/runtime/secrets"))
BOOTSTRAP_DIR = Path(os.getenv("VELMORA_BOOTSTRAP_DIR", "/bootstrap"))
SETUP_TOKEN_FILE = BOOTSTRAP_DIR / "setup_token"
BOOTSTRAP_PG_PASSWORD_FILE = BOOTSTRAP_DIR / "postgres_bootstrap_password"
INSTALLED_FILE = CONFIG_DIR / "installed.json"
RUNTIME_ENV_FILE = CONFIG_DIR / "runtime.env"
INSTALL_SESSION_FILE = CONFIG_DIR / ".install_session"
INSTALL_CSRF_FILE = CONFIG_DIR / ".install_csrf"
INSTALL_LOCK_FILE = CONFIG_DIR / ".installing"
MODE = os.getenv("VELMORA_BOOTSTRAP_MODE", "server").strip().lower()
SITE_URL = os.getenv("VELMORA_SITE_URL", "").strip().rstrip("/")
INTERNAL_PG_HOST = os.getenv("VELMORA_INTERNAL_PG_HOST", "postgres")
INTERNAL_PG_PORT = int(os.getenv("VELMORA_INTERNAL_PG_PORT", "5432"))
INTERNAL_PG_USER = os.getenv("VELMORA_INTERNAL_PG_USER", "velmora_bootstrap")
LOCAL_SETUP_TOKEN = os.getenv("VELMORA_LOCAL_SETUP_TOKEN", "").strip()
LOCAL_BOOTSTRAP_PG_PASSWORD = os.getenv("VELMORA_LOCAL_PG_BOOTSTRAP_PASSWORD", "").strip()

SESSION_COOKIE = "velmora_install_session"
CSRF_COOKIE = "velmora_install_csrf"
SESSION_TTL_SECONDS = 60 * 60
MAX_UNLOCK_ATTEMPTS = 8
UNLOCK_WINDOW_SECONDS = 15 * 60

logger = logging.getLogger(__name__)

app = FastAPI(title="Velmora Installer", version=APP_VERSION, docs_url=None, redoc_url=None, openapi_url=None)


@app.middleware("http")
async def installer_security_headers(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > 131072:
        return Response(content="Installer request is too large", status_code=413, media_type="text/plain")
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response

_unlock_attempts: dict[str, list[float]] = {}
_install_guard = asyncio.Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _setup_token() -> str:
    # Local/rootless Docker must not depend on host bind-mount permissions.
    # Production keeps using the protected bootstrap file under /etc/velmora.
    if MODE == "local" and LOCAL_SETUP_TOKEN:
        return LOCAL_SETUP_TOKEN
    return _read_text(SETUP_TOKEN_FILE)


def _bootstrap_pg_password() -> str:
    if MODE == "local" and LOCAL_BOOTSTRAP_PG_PASSWORD:
        return LOCAL_BOOTSTRAP_PG_PASSWORD
    return _read_text(BOOTSTRAP_PG_PASSWORD_FILE)


def _atomic_write(path: Path, value: str, mode: int = 0o444) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())
        temp = Path(handle.name)
    os.chmod(temp, mode)
    os.replace(temp, path)


def _json_write(path: Path, payload: dict) -> None:
    _atomic_write(path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def _installed() -> bool:
    return INSTALLED_FILE.is_file()


def _site_host() -> str:
    if not SITE_URL:
        return ""
    try:
        return (urlparse(SITE_URL).hostname or "").lower()
    except ValueError:
        return ""


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()[:64]
    return (request.client.host if request.client else "unknown")[:64]


def _expected_origin() -> str:
    return SITE_URL


def _check_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if origin and _expected_origin() and origin.rstrip("/") != _expected_origin():
        raise HTTPException(status_code=403, detail="This request origin is not allowed")


def _session_valid(raw: str | None) -> bool:
    if not raw:
        return False
    saved = _read_text(INSTALL_SESSION_FILE)
    if not saved:
        return False
    try:
        payload = json.loads(saved)
        if time.time() - float(payload["created_at"]) > SESSION_TTL_SECONDS:
            return False
        return hmac.compare_digest(hashlib.sha256(raw.encode()).hexdigest(), payload["hash"])
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        return False


def _require_session(session: str | None) -> None:
    if _installed():
        raise HTTPException(status_code=410, detail="Velmora is already installed")
    if not _session_valid(session):
        raise HTTPException(status_code=401, detail="Installer session is missing or expired")


def _require_csrf(request: Request, csrf_cookie: str | None, csrf_header: str | None) -> None:
    _check_origin(request)
    saved = _read_text(INSTALL_CSRF_FILE)
    if not csrf_cookie or not csrf_header or not saved:
        raise HTTPException(status_code=403, detail="Installer CSRF validation failed")
    digest = hashlib.sha256(csrf_cookie.encode()).hexdigest()
    if not hmac.compare_digest(csrf_cookie, csrf_header) or not hmac.compare_digest(digest, saved):
        raise HTTPException(status_code=403, detail="Installer CSRF validation failed")


def _rate_limit_unlock(request: Request) -> None:
    now = time.time()
    key = _client_ip(request)
    values = [stamp for stamp in _unlock_attempts.get(key, []) if now - stamp < UNLOCK_WINDOW_SECONDS]
    if len(values) >= MAX_UNLOCK_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Too many setup-code attempts. Try again later.")
    values.append(now)
    _unlock_attempts[key] = values


def _runtime_check() -> list[dict]:
    checks: list[dict] = []
    for directory, name in ((CONFIG_DIR, "Runtime configuration"), (SECRETS_DIR, "Secret storage")):
        try:
            directory.mkdir(parents=True, exist_ok=True)
            probe = directory / ".write_test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            checks.append({"key": name, "ok": True, "message": "Writable"})
        except OSError:
            checks.append({"key": name, "ok": False, "message": "Storage is not writable"})
    token_ok = bool(_setup_token()) or _installed()
    checks.append({"key": "Setup code", "ok": token_ok, "message": "Ready" if token_ok else "Missing bootstrap setup code"})
    host = _site_host()
    checks.append({"key": "Site URL", "ok": bool(host), "message": SITE_URL or "Not configured"})
    if MODE == "server" and host:
        try:
            addresses = sorted({item[4][0] for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)})
            checks.append({"key": "DNS", "ok": bool(addresses), "message": ", ".join(addresses[:4]) or "No addresses"})
        except OSError:
            checks.append({"key": "DNS", "ok": False, "message": "Domain does not resolve yet"})
    try:
        with _bootstrap_connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        checks.append({"key": "Bundled PostgreSQL", "ok": True, "message": "Reachable"})
    except Exception:
        checks.append({"key": "Bundled PostgreSQL", "ok": False, "message": "Database is not reachable"})
    return checks


class UnlockPayload(BaseModel):
    setup_code: str = Field(min_length=12, max_length=256)


class DatabasePayload(BaseModel):
    kind: Literal["bundled", "external"] = "bundled"
    host: str = Field(default="postgres", min_length=1, max_length=255)
    port: int = Field(default=5432, ge=1, le=65535)
    name: str = Field(default="velmora", min_length=1, max_length=63)
    user: str = Field(default="velmora", min_length=1, max_length=63)
    password: str = Field(min_length=12, max_length=256)
    sslmode: Literal["disable", "allow", "prefer", "require", "verify-ca", "verify-full"] = "prefer"

    @model_validator(mode="before")
    @classmethod
    def normalize_for_mode(cls, raw):
        # Hidden External PostgreSQL fields must never make bundled setup fail.
        # Normalize bundled connection details before Pydantic applies field-level
        # constraints such as host min_length=1.
        if isinstance(raw, dict):
            data = dict(raw)
            if data.get("kind", "bundled") == "bundled":
                data["host"] = INTERNAL_PG_HOST
                data["port"] = INTERNAL_PG_PORT
                data["sslmode"] = "disable"
            return data
        return raw

    @field_validator("name", "user")
    @classmethod
    def pg_identifier(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,62}", value):
            raise ValueError("Use letters, digits and underscores; the first character must be a letter or underscore")
        return value

    @field_validator("host")
    @classmethod
    def host_valid(cls, value: str) -> str:
        value = value.strip()
        if not value or any(char in value for char in " /\\@#?"):
            raise ValueError("Database host is required for External PostgreSQL")
        return value


class StorePayload(BaseModel):
    store_name: str = Field(default="Velmora", min_length=1, max_length=160)
    brand_tagline: str = Field(default="Signal Detection", max_length=120)
    phone: str = Field(default="", max_length=40)
    email: EmailStr | Literal[""] = ""
    service_region: str = Field(default="Worldwide", max_length=120)
    timezone: str = Field(default="UTC", min_length=1, max_length=64)
    footer_description: str = Field(default="Professional field electronics and signal-detection equipment.", max_length=800)


class AdminPayload(BaseModel):
    name: str = Field(default="Administrator", min_length=2, max_length=120)
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=12, max_length=128)

    @field_validator("email")
    @classmethod
    def basic_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+", value):
            raise ValueError("Enter a valid email address")
        return value

    @field_validator("password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        categories = sum(bool(re.search(pattern, value)) for pattern in (r"[a-z]", r"[A-Z]", r"\d", r"[^A-Za-z0-9]"))
        if categories < 3:
            raise ValueError("Password must use at least three character categories")
        return value


class InstallOptions(BaseModel):
    demo_catalog: bool = True


class InstallPayload(BaseModel):
    database: DatabasePayload
    store: StorePayload
    admin: AdminPayload
    options: InstallOptions = Field(default_factory=InstallOptions)


def _external_connect(db: DatabasePayload, dbname: str | None = None):
    return psycopg.connect(
        host=db.host,
        port=db.port,
        dbname=dbname or db.name,
        user=db.user,
        password=db.password,
        sslmode=db.sslmode,
        connect_timeout=6,
    )


def _bootstrap_connect():
    password = _bootstrap_pg_password()
    if not password:
        raise RuntimeError("Bundled PostgreSQL bootstrap password is missing")
    return psycopg.connect(
        host=INTERNAL_PG_HOST,
        port=INTERNAL_PG_PORT,
        dbname="postgres",
        user=INTERNAL_PG_USER,
        password=password,
        sslmode="disable",
        connect_timeout=6,
        autocommit=True,
    )


def _database_probe(db: DatabasePayload) -> dict:
    if db.kind == "bundled":
        with _bootstrap_connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version()")
                version = cur.fetchone()[0]
                cur.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (db.user,))
                role_exists = bool(cur.fetchone())
                cur.execute("SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname=%s", (db.name,))
                row = cur.fetchone()
                owner = row[0] if row else None
        return {
            "ok": True,
            "server": str(version).split(",", 1)[0],
            "message": "Bundled PostgreSQL is reachable",
            "role_exists": role_exists,
            "database_exists": owner is not None,
            "database_owner": owner,
        }

    with _external_connect(db) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT version(), current_database(), current_user")
            version, current_database, current_user = cur.fetchone()
            cur.execute("SELECT to_regclass('public.users'), to_regclass('public.alembic_version')")
            users_table, alembic_table = cur.fetchone()
            cur.execute("CREATE TEMP TABLE velmora_install_probe(id integer)")
    return {
        "ok": True,
        "server": str(version).split(",", 1)[0],
        "message": f"Connected to {current_database} as {current_user}",
        "existing_velmora_schema": bool(users_table or alembic_table),
    }


def _prepare_bundled_database(db: DatabasePayload) -> None:
    with _bootstrap_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (db.user,))
            if cur.fetchone():
                cur.execute(sql.SQL("ALTER ROLE {} WITH LOGIN PASSWORD {}").format(sql.Identifier(db.user), sql.Literal(db.password)))
            else:
                cur.execute(sql.SQL("CREATE ROLE {} WITH LOGIN PASSWORD {}").format(sql.Identifier(db.user), sql.Literal(db.password)))

            cur.execute("SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname=%s", (db.name,))
            row = cur.fetchone()
            if row:
                if row[0] != db.user:
                    raise RuntimeError(f"Database {db.name!r} already exists and is owned by another role")
            else:
                cur.execute(sql.SQL("CREATE DATABASE {} OWNER {}").format(sql.Identifier(db.name), sql.Identifier(db.user)))


def _ensure_external_database_is_safe(db: DatabasePayload) -> None:
    with _external_connect(db) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.users'), to_regclass('public.alembic_version')")
            users_table, alembic_table = cur.fetchone()
            if users_table or alembic_table:
                raise RuntimeError("The selected database already contains a Velmora schema. Use an empty database for a new installation.")


def _runtime_env(db: DatabasePayload) -> str:
    host = _site_host()
    environment = "development" if MODE == "local" else "production"
    cookie_secure = "false" if MODE == "local" else "true"
    docs_enabled = "true" if MODE == "local" else "false"
    cors = json.dumps([SITE_URL], separators=(",", ":"))
    allowed = json.dumps([host, "backend", "localhost", "127.0.0.1"], separators=(",", ":"))
    values = {
        "ENVIRONMENT": environment,
        "DATABASE_HOST": db.host,
        "DATABASE_PORT": str(db.port),
        "DATABASE_USER": db.user,
        "DATABASE_NAME": db.name,
        "DATABASE_PASSWORD_FILE": "/run/velmora/secrets/database_password",
        "DATABASE_SSLMODE": db.sslmode,
        "JWT_SECRET_FILE": "/run/velmora/secrets/jwt_secret",
        "JWT_ISSUER": "velmora-api",
        "JWT_AUDIENCE": "velmora-admin",
        "ACCESS_TOKEN_MINUTES": "15",
        "REFRESH_TOKEN_DAYS": "14",
        "COOKIE_SECURE": cookie_secure,
        "COOKIE_SAMESITE": "lax",
        "CORS_ORIGINS": cors,
        "ALLOWED_HOSTS": allowed,
        "TRUST_PROXY_HEADERS": "true",
        "HTTPS_ONLY": "false",
        "DOCS_ENABLED": docs_enabled,
        "SMTP_HOST": "",
        "SMTP_PORT": "587",
        "SMTP_USERNAME": "",
        "SMTP_FROM_EMAIL": "",
        "SMTP_STARTTLS": "true",
    }
    return "\n".join(f"{key}={value}" for key, value in values.items()) + "\n"


def _subprocess_env(db: DatabasePayload, jwt_secret: str) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "ENVIRONMENT": "development",
            "DATABASE_HOST": db.host,
            "DATABASE_PORT": str(db.port),
            "DATABASE_USER": db.user,
            "DATABASE_NAME": db.name,
            "DATABASE_PASSWORD": db.password,
            "DATABASE_PASSWORD_FILE": "",
            "DATABASE_SSLMODE": db.sslmode,
            "JWT_SECRET": jwt_secret,
            "JWT_SECRET_FILE": "",
            "COOKIE_SECURE": "false",
            "DOCS_ENABLED": "true",
            "CORS_ORIGINS": json.dumps([SITE_URL]),
            "ALLOWED_HOSTS": json.dumps([_site_host() or "localhost", "localhost", "127.0.0.1"]),
        }
    )
    return env


def _run(command: list[str], env: dict[str, str], *, stdin: str | None = None, timeout: int = 180) -> str:
    result = subprocess.run(
        command,
        cwd="/app",
        input=stdin,
        text=True,
        capture_output=True,
        env=env,
        timeout=timeout,
        check=False,
    )
    if result.returncode != 0:
        message = (result.stderr or result.stdout or "Command failed").strip()
        raise RuntimeError(message[-4000:])
    return (result.stdout or "").strip()


def _install_tasks(payload: InstallPayload, env: dict[str, str]) -> None:
    task_payload = {
        "store": payload.store.model_dump(mode="json"),
        "admin": payload.admin.model_dump(mode="json"),
        "demo_catalog": payload.options.demo_catalog,
    }
    _run([sys.executable, "-m", "app.install_tasks"], env, stdin=json.dumps(task_payload), timeout=180)


@app.get("/healthz")
def healthz():
    return {"status": "ok", "installed": _installed()}


@app.get("/api/v1/install/status")
def install_status(session: str | None = Cookie(default=None, alias=SESSION_COOKIE)):
    installed = _installed()
    return {
        "version": APP_VERSION,
        "installed": installed,
        "locked": installed,
        "mode": MODE,
        "site_url": SITE_URL,
        "session": False if installed else _session_valid(session),
        "checks": _runtime_check(),
    }


@app.post("/api/v1/install/unlock")
def unlock(payload: UnlockPayload, request: Request, response: Response):
    if _installed():
        raise HTTPException(status_code=410, detail="Velmora is already installed")
    _check_origin(request)
    _rate_limit_unlock(request)
    expected = _setup_token()
    if not expected or not hmac.compare_digest(payload.setup_code.strip(), expected):
        raise HTTPException(status_code=401, detail="Invalid setup code")
    session = secrets.token_urlsafe(48)
    csrf = secrets.token_urlsafe(32)
    _json_write(INSTALL_SESSION_FILE, {"hash": hashlib.sha256(session.encode()).hexdigest(), "created_at": time.time()})
    _atomic_write(INSTALL_CSRF_FILE, hashlib.sha256(csrf.encode()).hexdigest() + "\n")
    secure = MODE != "local"
    response.set_cookie(SESSION_COOKIE, session, httponly=True, secure=secure, samesite="strict", max_age=SESSION_TTL_SECONDS, path="/")
    response.set_cookie(CSRF_COOKIE, csrf, httponly=False, secure=secure, samesite="strict", max_age=SESSION_TTL_SECONDS, path="/")
    return {"ok": True, "expires_in": SESSION_TTL_SECONDS}


@app.post("/api/v1/install/database/test")
def test_database(
    payload: DatabasePayload,
    request: Request,
    session: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    csrf_cookie: str | None = Cookie(default=None, alias=CSRF_COOKIE),
    csrf_header: str | None = Header(default=None, alias="X-Install-CSRF"),
):
    _require_session(session)
    _require_csrf(request, csrf_cookie, csrf_header)
    try:
        return _database_probe(payload)
    except Exception as exc:
        logger.warning("Database connection test failed (%s)", type(exc).__name__)
        raise HTTPException(status_code=422, detail="Database connection failed. Verify the connection settings.") from None


@app.post("/api/v1/install/run")
async def run_install(
    payload: InstallPayload,
    request: Request,
    session: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    csrf_cookie: str | None = Cookie(default=None, alias=CSRF_COOKIE),
    csrf_header: str | None = Header(default=None, alias="X-Install-CSRF"),
):
    _require_session(session)
    _require_csrf(request, csrf_cookie, csrf_header)
    if _install_guard.locked():
        raise HTTPException(status_code=409, detail="Installation is already running")

    async with _install_guard:
        if _installed():
            raise HTTPException(status_code=410, detail="Velmora is already installed")
        _atomic_write(INSTALL_LOCK_FILE, _now_iso() + "\n")
        jwt_secret = secrets.token_urlsafe(64)
        try:
            await asyncio.to_thread(_database_probe, payload.database)
            if payload.database.kind == "bundled":
                await asyncio.to_thread(_prepare_bundled_database, payload.database)
            else:
                await asyncio.to_thread(_ensure_external_database_is_safe, payload.database)

            env = _subprocess_env(payload.database, jwt_secret)
            await asyncio.to_thread(_run, ["alembic", "upgrade", "head"], env)
            await asyncio.to_thread(_install_tasks, payload, env)

            _atomic_write(SECRETS_DIR / "database_password", payload.database.password + "\n")
            _atomic_write(SECRETS_DIR / "jwt_secret", jwt_secret + "\n")
            _atomic_write(SECRETS_DIR / "smtp_password", "")
            _atomic_write(SECRETS_DIR / "telegram_bot_token", "")
            _atomic_write(RUNTIME_ENV_FILE, _runtime_env(payload.database))
            _json_write(
                INSTALLED_FILE,
                {
                    "installed_at": _now_iso(),
                    "version": APP_VERSION,
                    "mode": MODE,
                    "site_url": SITE_URL,
                    "database_kind": payload.database.kind,
                    "database_host": payload.database.host,
                    "database_name": payload.database.name,
                    "database_user": payload.database.user,
                },
            )
            for transient in (INSTALL_SESSION_FILE, INSTALL_CSRF_FILE, INSTALL_LOCK_FILE):
                transient.unlink(missing_ok=True)
            # One-time setup code becomes useless after installation.
            try:
                SETUP_TOKEN_FILE.unlink()
            except OSError:
                pass
            try:
                _atomic_write(BOOTSTRAP_DIR / "installed.lock", "installed\n")
            except OSError:
                # installed.json is the authoritative installation lock. This
                # local marker only prevents helper scripts from recreating the
                # one-time setup code after it has been consumed.
                pass
            return {"ok": True, "message": "Velmora installation completed", "site_url": SITE_URL}
        except HTTPException:
            raise
        except Exception as exc:
            INSTALL_LOCK_FILE.unlink(missing_ok=True)
            logger.error("Installation failed (%s)", type(exc).__name__)
            raise HTTPException(status_code=500, detail="Installation failed. Check the server logs.") from None


@app.get("/api/v1/install/ready")
def ready_after_install():
    if not _installed():
        return {"installed": False, "backend": False}
    backend_ready = False
    try:
        with socket.create_connection(("backend", 8000), timeout=1.0):
            backend_ready = True
    except OSError:
        backend_ready = False
    return {"installed": True, "backend": backend_ready, "site_url": SITE_URL}
