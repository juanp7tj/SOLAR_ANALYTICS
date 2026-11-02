import asyncio
from datetime import date

import fitz
import httpx
import pytest

from app.routers.dashboard import _period_range, _sum_known
from app.routers.data_tools import _safe_spreadsheet_text
from app.services.pdf_parser import extract_invoice_fields


def test_pdf_extracts_only_explicit_labels_and_preserves_absence():
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Consumo faturado 123,4 kWh\nEnergia injetada 45,6 kWh\nEnergia compensada 40,0 kWh\nCréditos acumulados 215,0 kWh\nTotal da fatura R$ 199,90\nVencimento: 12/12/2026")
    payload = document.tobytes()
    document.close()

    extracted = extract_invoice_fields(payload)
    assert extracted["billed_consumption_kwh"] == 123.4
    assert extracted["injected_kwh"] == 45.6
    assert extracted["compensated_kwh"] == 40.0
    assert extracted["accumulated_credits_kwh"] == 215.0
    assert str(extracted["total_amount_brl"]) == "199.90"
    assert extracted["due_date"] == date(2026, 12, 12)
    assert extracted["paid_amount_brl"] is None


def test_pdf_rejects_documents_with_too_many_pages(monkeypatch):
    from app.services import pdf_parser

    class LargeDocument:
        page_count = pdf_parser.MAX_PDF_PAGES + 1

        def close(self):
            pass

    monkeypatch.setattr(pdf_parser.fitz, "open", lambda **kwargs: LargeDocument())
    with pytest.raises(ValueError, match="páginas"):
        pdf_parser.extract_invoice_fields(b"pdf")


def test_pdf_rejects_text_above_extraction_limit(monkeypatch):
    from app.services import pdf_parser

    class LargePage:
        def get_text(self, *_args):
            return "x" * (pdf_parser.MAX_EXTRACTED_TEXT_CHARS + 1)

    class LargeDocument:
        page_count = 1

        def __iter__(self):
            return iter([LargePage()])

        def close(self):
            pass

    monkeypatch.setattr(pdf_parser.fitz, "open", lambda **kwargs: LargeDocument())
    with pytest.raises(ValueError, match="limite de segurança"):
        pdf_parser.extract_invoice_fields(b"pdf")


def test_unknown_values_are_not_summed_as_zero():
    class Row:
        def __init__(self, value):
            self.energy = value

    assert _sum_known([Row(None), Row(None)], "energy") is None
    assert _sum_known([Row(None), Row(0.0), Row(3.2)], "energy") is None
    assert _sum_known([Row(0.0), Row(3.2)], "energy") == 3.2


def test_period_filters_use_calendar_boundaries():
    assert _period_range("day", date(2026, 11, 4)) == (date(2026, 11, 4), date(2026, 11, 4))
    assert _period_range("week", date(2026, 11, 4)) == (date(2026, 11, 2), date(2026, 11, 8))
    assert _period_range("month", date(2026, 2, 14)) == (date(2026, 2, 1), date(2026, 2, 28))
    assert _period_range("year", date(2026, 7, 1)) == (date(2026, 1, 1), date(2026, 12, 31))


def test_spreadsheet_csv_text_neutralizes_formula_prefixes():
    assert _safe_spreadsheet_text("=1+1") == "'=1+1"
    assert _safe_spreadsheet_text("  @SUM(A1:A2)") == "'  @SUM(A1:A2)"
    assert _safe_spreadsheet_text("\t-1+1") == "'\t-1+1"
    assert _safe_spreadsheet_text("\ufeff=1+1") == "'\ufeff=1+1"
    assert _safe_spreadsheet_text("\u200b@SUM(A1:A2)") == "'\u200b@SUM(A1:A2)"
    assert _safe_spreadsheet_text("Conta solar") == "Conta solar"
    assert _safe_spreadsheet_text(None) == ""


def test_goodwe_secret_storage_rejects_unapproved_keyring(monkeypatch):
    from app.services import goodwe

    class FallbackBackend:
        pass

    FallbackBackend.__module__ = "keyring.backends.fail"
    monkeypatch.setattr(goodwe, "sys", type("Platform", (), {"platform": "win32"})())
    monkeypatch.setattr(goodwe.keyring, "get_keyring", lambda: FallbackBackend())

    assert not goodwe._secure_keyring_available()
    with pytest.raises(RuntimeError, match="cofre de credenciais aprovado"):
        goodwe.save_app_secret("x")


def test_goodwe_accepts_windows_credential_vault_backend(monkeypatch):
    from app.services import goodwe

    class WindowsVaultBackend:
        pass

    WindowsVaultBackend.__module__ = "keyring.backends.Windows"
    monkeypatch.setattr(goodwe, "sys", type("Platform", (), {"platform": "win32"})())
    monkeypatch.setattr(goodwe.keyring, "get_keyring", lambda: WindowsVaultBackend())
    assert goodwe._secure_keyring_available()


def test_mutating_requests_reject_untrusted_origin_and_add_security_headers():
    from app.main import app

    async def exercise():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8000") as client:
            blocked = await client.post("/api/goodwe/sync", headers={"Origin": "https://evil.example"})
            assert blocked.status_code == 403
            allowed = await client.post("/api/goodwe/sync", headers={"Origin": "http://127.0.0.1:3000"})
            assert allowed.status_code == 501
            assert allowed.headers["cache-control"] == "no-store"
            assert allowed.headers["x-content-type-options"] == "nosniff"
            assert allowed.headers["referrer-policy"] == "no-referrer"
            untrusted_host = await client.get("/api/health", headers={"Host": "evil.example"})
            assert untrusted_host.status_code == 400

    asyncio.run(exercise())


def test_admin_login_protects_data_routes_and_logout(monkeypatch):
    from app import config
    from app.main import app, initialize_application

    initialize_application()
    monkeypatch.setattr(config, "AUTH_REQUIRED", True)
    monkeypatch.setattr(config, "ADMIN_USERNAME", "solar-admin")
    monkeypatch.setattr(config, "ADMIN_PASSWORD", "senha-de-teste-muito-forte-123")

    async def exercise():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8000") as client:
            unauthenticated = await client.get("/api/readings")
            assert unauthenticated.status_code == 401

            bad_login = await client.post(
                "/api/auth/login",
                json={"username": "solar-admin", "password": "senha-incorreta"},
                headers={"Origin": "http://127.0.0.1:3000"},
            )
            assert bad_login.status_code == 401
            assert "solar_analytics_session" not in bad_login.headers.get("set-cookie", "")

            login = await client.post(
                "/api/auth/login",
                json={"username": "solar-admin", "password": "senha-de-teste-muito-forte-123"},
                headers={"Origin": "http://127.0.0.1:3000"},
            )
            assert login.status_code == 200
            assert login.json()["authenticated"] is True
            assert "httponly" in login.headers["set-cookie"].lower()
            assert "solar_analytics_session" in login.headers["set-cookie"]
            local_cookie = login.headers["set-cookie"].lower()
            assert "samesite=lax" in local_cookie
            assert "max-age=43200" in local_cookie
            assert "secure" not in local_cookie

            protected = await client.get("/api/readings")
            assert protected.status_code == 200
            status = await client.get("/api/auth/status")
            assert status.json()["auth_required"] is True
            assert status.json()["authenticated"] is True

            logout = await client.post("/api/auth/logout", headers={"Origin": "http://127.0.0.1:3000"})
            assert logout.status_code == 200
            protected_after_logout = await client.get("/api/readings")
            assert protected_after_logout.status_code == 401

    asyncio.run(exercise())


def test_public_authenticated_writes_require_a_trusted_origin(monkeypatch):
    from app import config
    from app.main import app

    monkeypatch.setattr(config, "AUTH_REQUIRED", True)

    async def exercise():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8000") as client:
            missing_origin = await client.post("/api/auth/login", json={"username": "x", "password": "x"})
            assert missing_origin.status_code == 403
            bad_origin = await client.post(
                "/api/auth/login",
                json={"username": "x", "password": "x"},
                headers={"Origin": "https://attacker.example"},
            )
            assert bad_origin.status_code == 403

    asyncio.run(exercise())



def _http_scope(path, *, method="POST", headers=None, session=None):
    header_items = [(b"host", b"127.0.0.1")]
    if headers:
        header_items.extend(headers)
    return {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.4"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": header_items,
        "server": ("127.0.0.1", 8000),
        "client": ("127.0.0.1", 4321),
        "session": session or {},
    }


def test_unauthenticated_multipart_is_rejected_before_body_read(monkeypatch):
    from app import config
    from app.middleware import RequestSecurityMiddleware

    monkeypatch.setattr(config, "AUTH_REQUIRED", True)
    scope = _http_scope(
        "/api/invoices/extract",
        headers=[
            (b"origin", b"http://127.0.0.1:3000"),
            (b"content-type", b"multipart/form-data; boundary=test"),
            (b"content-length", b"12"),
        ],
    )
    state = {"read": False, "downstream": False}
    messages = []

    async def receive():
        state["read"] = True
        return {"type": "http.request", "body": b"upload-body", "more_body": False}

    async def downstream(_scope, _receive, _send):
        state["downstream"] = True

    async def send(message):
        messages.append(message)

    asyncio.run(RequestSecurityMiddleware(downstream)(scope, receive, send))
    response_start = next(message for message in messages if message["type"] == "http.response.start")
    assert response_start["status"] == 401
    assert state == {"read": False, "downstream": False}


def test_authenticated_oversized_content_length_is_rejected_without_read(monkeypatch):
    from app import config, middleware
    from app.middleware import RequestSecurityMiddleware

    monkeypatch.setattr(config, "AUTH_REQUIRED", True)
    monkeypatch.setitem(middleware.UPLOAD_BODY_LIMITS, "/api/invoices/extract", 8)
    scope = _http_scope(
        "/api/invoices/extract",
        headers=[
            (b"origin", b"http://127.0.0.1:3000"),
            (b"content-length", b"9"),
        ],
        session={"solar_admin_authenticated": True},
    )
    read = False
    messages = []

    async def receive():
        nonlocal read
        read = True
        return {"type": "http.request", "body": b"123456789", "more_body": False}

    async def downstream(_scope, _receive, _send):
        raise AssertionError("A requisição excessiva não deve chegar ao parser.")

    async def send(message):
        messages.append(message)

    asyncio.run(RequestSecurityMiddleware(downstream)(scope, receive, send))
    response_start = next(message for message in messages if message["type"] == "http.response.start")
    assert response_start["status"] == 413
    assert read is False


def test_streaming_body_limit_handles_missing_content_length(monkeypatch):
    from app import config, middleware
    from app.middleware import RequestSecurityMiddleware

    monkeypatch.setattr(config, "AUTH_REQUIRED", True)
    monkeypatch.setitem(middleware.UPLOAD_BODY_LIMITS, "/api/invoices/extract", 8)
    scope = _http_scope(
        "/api/invoices/extract",
        headers=[(b"origin", b"http://127.0.0.1:3000")],
        session={"solar_admin_authenticated": True},
    )
    messages = []

    async def receive():
        return {"type": "http.request", "body": b"123456789", "more_body": False}

    async def downstream(_scope, downstream_receive, _send):
        await downstream_receive()

    async def send(message):
        messages.append(message)

    asyncio.run(RequestSecurityMiddleware(downstream)(scope, receive, send))
    response_start = next(message for message in messages if message["type"] == "http.response.start")
    assert response_start["status"] == 413


def test_login_rate_limit_state_is_bounded_and_expires(monkeypatch):
    from starlette.requests import Request

    from app.services import auth

    monkeypatch.setattr(auth, "_MAX_TRACKED_CLIENTS", 2)
    with auth._attempts_lock:
        auth._attempts.clear()
        auth._last_global_cleanup = 0.0

    def request_from(host):
        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/api/auth/login",
            "headers": [],
            "client": (host, 4321),
            "server": ("127.0.0.1", 8000),
        }
        return Request(scope)

    clients = [request_from(f"198.51.100.{index}") for index in range(1, 11)]
    for index, client in enumerate(clients):
        auth.record_login_failure(client, now=1000.0 + index)
    assert len(auth._attempts) <= 2
    assert not auth.login_is_rate_limited(clients[-1], now=1009.0)
    assert not auth.login_is_rate_limited(clients[-1], now=1009.0 + auth._ATTEMPT_WINDOW_SECONDS)
    assert len(auth._attempts) == 0


def test_render_https_session_cookie_flags_in_isolated_process(tmp_path):
    import os
    import subprocess
    import sys

    env = os.environ.copy()
    env.update(
        {
            "RENDER": "true",
            "RENDER_EXTERNAL_URL": "https://solar-auth-test.onrender.com",
            "RENDER_EXTERNAL_HOSTNAME": "solar-auth-test.onrender.com",
            "SOLAR_AUTH_REQUIRED": "true",
            "SOLAR_ADMIN_USERNAME": "solar-test-admin",
            "SOLAR_ADMIN_PASSWORD": "unit-test-only-password-123456",
            "SOLAR_SESSION_SECRET": "unit-test-session-secret-0123456789abcdef0123456789",
            "SOLAR_DATA_DIR": str(tmp_path / "data"),
            "SOLAR_BACKUP_DIR": str(tmp_path / "backups"),
            "SOLAR_DEMO_AUTOLOAD": "false",
            "SOLAR_VOLATILE_STORAGE": "true",
            "SOLAR_DISABLE_API_DOCS": "true",
        }
    )
    script = """
import asyncio
import httpx
from app.main import app

async def exercise():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url='https://solar-auth-test.onrender.com') as client:
        response = await client.post(
            '/api/auth/login',
            json={'username': 'solar-test-admin', 'password': 'unit-test-only-password-123456'},
            headers={'Origin': 'https://solar-auth-test.onrender.com'},
        )
        assert response.status_code == 200
        cookie = response.headers['set-cookie'].lower()
        assert 'httponly' in cookie
        assert 'secure' in cookie
        assert 'samesite=none' in cookie
        assert 'max-age=43200' in cookie

asyncio.run(exercise())
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=os.path.dirname(os.path.dirname(__file__)),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, "A verificação de cookie HTTPS falhou; consulte a saída do subprocesso."



def test_session_and_host_middleware_wrap_preparser_gate():
    from app.main import app

    order = [item.cls.__name__ for item in app.user_middleware]
    assert order.index("SessionMiddleware") < order.index("TrustedHostMiddleware")
    assert order.index("TrustedHostMiddleware") < order.index("RequestSecurityMiddleware")
