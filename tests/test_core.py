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
