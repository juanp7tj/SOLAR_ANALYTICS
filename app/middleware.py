from __future__ import annotations

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app import config
from app.limits import MAX_BACKUP_REQUEST_BYTES, MAX_PDF_REQUEST_BYTES, MAX_STANDARD_API_BODY_BYTES

PUBLIC_API_PATHS = frozenset({
    "/api/health",
    "/api/auth/status",
    "/api/auth/login",
    "/api/auth/logout",
})
UPLOAD_BODY_LIMITS = {
    "/api/invoices/extract": MAX_PDF_REQUEST_BYTES,
    "/api/backup/restore": MAX_BACKUP_REQUEST_BYTES,
}


class _RequestBodyTooLarge(Exception):
    pass


class RequestSecurityMiddleware:
    """Enforce auth and bounded request bodies before FastAPI parses multipart/form data."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def _send_json(self, scope: Scope, receive: Receive, send: Send, status: int, detail: str) -> None:
        response = JSONResponse(status_code=status, content={"detail": detail})
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        if scope.get("path", "").startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        await response(scope, receive, send)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        method = scope.get("method", "GET").upper()
        is_api = path.startswith("/api/")
        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        origin = headers.get(b"origin", b"").decode("latin-1").rstrip("/")
        mutating_api = is_api and method in {"POST", "PUT", "PATCH", "DELETE"}

        if mutating_api:
            if origin and origin not in config.TRUSTED_WRITE_ORIGINS:
                await self._send_json(scope, receive, send, 403, "Origem não autorizada para esta operação.")
                return
            if config.AUTH_REQUIRED and not origin:
                await self._send_json(scope, receive, send, 403, "Origem não autorizada para esta operação.")
                return

        if is_api and method != "OPTIONS" and config.AUTH_REQUIRED and path not in PUBLIC_API_PATHS:
            session = scope.get("session")
            if not isinstance(session, dict) or session.get("solar_admin_authenticated") is not True:
                await self._send_json(scope, receive, send, 401, "Autenticação necessária.")
                return

        if not is_api:
            await self._call_with_security_headers(scope, receive, send)
            return

        limit = UPLOAD_BODY_LIMITS.get(path, MAX_STANDARD_API_BODY_BYTES)
        content_length = headers.get(b"content-length")
        if content_length is not None:
            try:
                declared_size = int(content_length)
            except (ValueError, TypeError):
                await self._send_json(scope, receive, send, 400, "Cabeçalho Content-Length inválido.")
                return
            if declared_size < 0:
                await self._send_json(scope, receive, send, 400, "Cabeçalho Content-Length inválido.")
                return
            if declared_size > limit:
                await self._send_json(scope, receive, send, 413, "O corpo da requisição excede o limite permitido.")
                return

        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message.get("type") == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    raise _RequestBodyTooLarge()
            return message

        async def secure_send(message: Message) -> None:
            if message.get("type") == "http.response.start":
                response_headers = dict(message.get("headers", []))
                response_headers.setdefault(b"x-content-type-options", b"nosniff")
                response_headers.setdefault(b"referrer-policy", b"no-referrer")
                response_headers[b"cache-control"] = b"no-store"
                message = {**message, "headers": list(response_headers.items())}
            await send(message)

        try:
            await self.app(scope, limited_receive, secure_send)
        except _RequestBodyTooLarge:
            await self._send_json(scope, receive, send, 413, "O corpo da requisição excede o limite permitido.")

    async def _call_with_security_headers(self, scope: Scope, receive: Receive, send: Send) -> None:
        async def secure_send(message: Message) -> None:
            if message.get("type") == "http.response.start":
                response_headers = dict(message.get("headers", []))
                response_headers.setdefault(b"x-content-type-options", b"nosniff")
                response_headers.setdefault(b"referrer-policy", b"no-referrer")
                message = {**message, "headers": list(response_headers.items())}
            await send(message)

        await self.app(scope, receive, secure_send)
