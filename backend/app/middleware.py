import time

from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.config import settings
from app.utils import request_id


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        rid = request_id()
        scope.setdefault("state", {})["request_id"] = rid
        started = time.perf_counter()

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", rid.encode()))
                headers.append((b"x-content-type-options", b"nosniff"))
                headers.append((b"x-frame-options", b"DENY"))
                headers.append((b"referrer-policy", b"no-referrer"))
                headers.append((b"permissions-policy", b"camera=(), microphone=(), geolocation=()"))
                if settings.https_only:
                    headers.append((b"strict-transport-security", b"max-age=63072000; includeSubDomains; preload"))
                path = scope.get("path", "")
                if path.startswith(settings.api_prefix + "/admin") or path.startswith(settings.api_prefix + "/auth"):
                    headers.append((b"cache-control", b"no-store"))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)
        scope["state"]["duration_ms"] = round((time.perf_counter() - started) * 1000, 2)




class CrossSiteMutationGuardMiddleware:
    _unsafe_methods = {"POST", "PUT", "PATCH", "DELETE"}

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        method = str(scope.get("method", "GET")).upper()
        path = str(scope.get("path", ""))
        if method in self._unsafe_methods and path.startswith(settings.api_prefix):
            headers = Headers(scope=scope)
            fetch_site = (headers.get("sec-fetch-site") or "").lower()
            origin = headers.get("origin")
            if fetch_site == "cross-site" or (origin and origin not in settings.cors_origins):
                response = JSONResponse({"detail": "Cross-site request rejected"}, status_code=403)
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


class BodySizeLimitMiddleware:
    def __init__(self, app: ASGIApp, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = Headers(scope=scope)
        content_length = headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > self.max_bytes:
                    response = JSONResponse({"detail": "Request body exceeds the allowed size"}, status_code=413)
                    await response(scope, receive, send)
                    return
            except ValueError:
                response = JSONResponse({"detail": "Invalid Content-Length header"}, status_code=400)
                await response(scope, receive, send)
                return

        messages = []
        received = 0
        while True:
            message = await receive()
            messages.append(message)
            if message["type"] == "http.disconnect":
                return
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    response = JSONResponse({"detail": "Request body exceeds the allowed size"}, status_code=413)
                    await response(scope, receive, send)
                    return
                if not message.get("more_body", False):
                    break

        index = 0

        async def replay_receive() -> Message:
            nonlocal index
            if index < len(messages):
                message = messages[index]
                index += 1
                return message
            return {"type": "http.request", "body": b"", "more_body": False}

        await self.app(scope, replay_receive, send)


from starlette.middleware.base import BaseHTTPMiddleware

from app.database import SessionLocal
from app.models import AuditLog
from app.utils import get_client_ip, get_user_agent


class DeniedRequestAuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        if response.status_code in {401, 403, 429} and request.url.path.startswith(settings.api_prefix):
            db = SessionLocal()
            try:
                db.add(
                    AuditLog(
                        actor_user_id=getattr(request.state, "actor_id", None),
                        actor_email=getattr(request.state, "actor_email", None),
                        action="security.request_denied",
                        success=False,
                        message=f"HTTP {response.status_code}",
                        details={"status_code": response.status_code},
                        client_ip=get_client_ip(request),
                        user_agent=get_user_agent(request),
                        request_id=getattr(request.state, "request_id", None),
                        method=request.method,
                        path=str(request.url.path)[:500],
                    )
                )
                db.commit()
            except Exception:
                db.rollback()
            finally:
                db.close()
        return response
