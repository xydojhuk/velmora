from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.staticfiles import StaticFiles

from app.api.router import api_router
from app.config import settings
from app.version import get_version
from app.database import engine
from app.middleware import BodySizeLimitMiddleware, CrossSiteMutationGuardMiddleware, DeniedRequestAuditMiddleware, RequestContextMiddleware


app = FastAPI(
    title=settings.app_name,
    version=get_version(),
    docs_url="/docs" if settings.docs_enabled and not settings.is_production else None,
    redoc_url=None,
    openapi_url="/openapi.json" if settings.docs_enabled and not settings.is_production else None,
)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token", "Idempotency-Key", "X-Requested-With"],
)
if settings.https_only:
    app.add_middleware(HTTPSRedirectMiddleware)
app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.max_request_body_bytes)
app.add_middleware(CrossSiteMutationGuardMiddleware)
app.add_middleware(DeniedRequestAuditMiddleware)
app.add_middleware(RequestContextMiddleware)

app.include_router(api_router, prefix=settings.api_prefix)

media_directory = Path(settings.media_root).expanduser().resolve()
media_directory.mkdir(parents=True, exist_ok=True)
app.mount(settings.media_url_prefix, StaticFiles(directory=media_directory, check_dir=False), name="media")


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok"}


@app.get("/ready", tags=["system"])
def ready():
    with Session(engine) as db:
        db.execute(text("SELECT 1"))
    return {"status": "ready"}
