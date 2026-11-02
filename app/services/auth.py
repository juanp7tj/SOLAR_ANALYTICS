from __future__ import annotations

import hmac
import threading
from collections import deque
from time import monotonic

from fastapi import HTTPException, Request

from app import config

_ATTEMPT_WINDOW_SECONDS = 15 * 60
_MAX_FAILED_ATTEMPTS = 8
_MAX_TRACKED_CLIENTS = 4096
_GLOBAL_CLEANUP_INTERVAL_SECONDS = 60
_attempts: dict[str, deque[float]] = {}
_attempts_lock = threading.Lock()
_last_global_cleanup = 0.0


def require_authenticated_admin(request: Request) -> None:
    if not config.AUTH_REQUIRED:
        return
    if request.session.get("solar_admin_authenticated") is not True:
        raise HTTPException(status_code=401, detail="Autenticação necessária.")


def _client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _expire(queue: deque[float], now: float) -> None:
    while queue and now - queue[0] >= _ATTEMPT_WINDOW_SECONDS:
        queue.popleft()


def _cleanup_expired(now: float) -> None:
    global _last_global_cleanup
    if now - _last_global_cleanup < _GLOBAL_CLEANUP_INTERVAL_SECONDS:
        return
    for key, queue in list(_attempts.items()):
        _expire(queue, now)
        if not queue:
            _attempts.pop(key, None)
    _last_global_cleanup = now


def login_is_rate_limited(request: Request, *, now: float | None = None) -> bool:
    current = monotonic() if now is None else now
    key = _client_key(request)
    with _attempts_lock:
        _cleanup_expired(current)
        attempts = _attempts.get(key)
        if attempts is None:
            return False
        _expire(attempts, current)
        if not attempts:
            _attempts.pop(key, None)
            return False
        return len(attempts) >= _MAX_FAILED_ATTEMPTS


def record_login_failure(request: Request, *, now: float | None = None) -> None:
    current = monotonic() if now is None else now
    key = _client_key(request)
    with _attempts_lock:
        _cleanup_expired(current)
        attempts = _attempts.get(key)
        if attempts is None:
            if len(_attempts) >= _MAX_TRACKED_CLIENTS:
                # Ordered dictionaries preserve insertion order; evict one oldest key to cap memory.
                oldest_key = next(iter(_attempts), None)
                if oldest_key is not None:
                    _attempts.pop(oldest_key, None)
            attempts = deque()
            _attempts[key] = attempts
        _expire(attempts, current)
        attempts.append(current)


def clear_login_failures(request: Request) -> None:
    with _attempts_lock:
        _attempts.pop(_client_key(request), None)


def credentials_match(username: str, password: str) -> bool:
    configured_user = config.ADMIN_USERNAME.encode("utf-8")
    configured_password = config.ADMIN_PASSWORD.encode("utf-8")
    candidate_user = username.strip().encode("utf-8")
    candidate_password = password.encode("utf-8")
    return hmac.compare_digest(candidate_user, configured_user) and hmac.compare_digest(
        candidate_password, configured_password
    )
