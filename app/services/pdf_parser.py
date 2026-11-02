from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation

import fitz

MAX_PDF_PAGES = 100
MAX_EXTRACTED_TEXT_CHARS = 1_000_000


FIELD_PATTERNS: dict[str, list[str]] = {
    "billed_consumption_kwh": [r"consumo\s+(?:faturado|ativo|de\s+energia)[^\d]{0,60}([\d.,]+)\s*kwh"],
    "injected_kwh": [r"energia\s+(?:injetada|injetado)[^\d]{0,60}([\d.,]+)\s*kwh", r"injetada\s+na\s+rede[^\d]{0,60}([\d.,]+)\s*kwh"],
    "compensated_kwh": [r"energia\s+(?:compensada|compensado)[^\d]{0,60}([\d.,]+)\s*kwh", r"energia\s+compensada\s+gd[^\d]{0,60}([\d.,]+)\s*kwh"],
    "accumulated_credits_kwh": [r"(?:saldo|cr[eé]ditos?)\s+(?:acumulado|acumulados|de\s+energia)[^\d]{0,60}([\d.,]+)\s*kwh", r"cr[eé]dito\s+dispon[ií]vel[^\d]{0,60}([\d.,]+)\s*kwh"],
}


def _number(raw: str) -> float | None:
    value = raw.strip().replace(" ", "")
    if not value:
        return None
    if "," in value:
        value = value.replace(".", "").replace(",", ".")
    elif value.count(".") > 1:
        value = value.replace(".", "")
    try:
        number = float(value)
        return number if number >= 0 else None
    except ValueError:
        return None


def _money(raw: str) -> Decimal | None:
    value = raw.strip().replace("R$", "").replace(" ", "")
    if "," in value:
        value = value.replace(".", "").replace(",", ".")
    try:
        number = Decimal(value)
        return number.quantize(Decimal("0.01")) if number >= 0 else None
    except (InvalidOperation, ValueError):
        return None


def _find(patterns: list[str], text: str, parser):
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            value = parser(match.group(1))
            if value is not None:
                return value
    return None


def _date_near(label: str, text: str) -> date | None:
    match = re.search(label + r"[^\d]{0,30}(\d{2})[/-](\d{2})[/-](\d{4})", text, re.IGNORECASE)
    if not match:
        return None
    try:
        return date(int(match.group(3)), int(match.group(2)), int(match.group(1)))
    except ValueError:
        return None


def extract_invoice_fields(pdf_bytes: bytes) -> dict:
    try:
        document = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:
        raise ValueError("Não foi possível abrir este PDF. Confira se o arquivo é válido e não está protegido por senha.") from exc

    try:
        if document.page_count == 0:
            raise ValueError("O PDF não contém páginas.")
        if document.page_count > MAX_PDF_PAGES:
            raise ValueError(f"O PDF ultrapassa o limite de {MAX_PDF_PAGES} páginas.")
        pages: list[str] = []
        total_chars = 0
        for page in document:
            page_text = page.get_text("text")
            if total_chars + len(page_text) > MAX_EXTRACTED_TEXT_CHARS:
                raise ValueError("O texto extraído do PDF ultrapassa o limite de segurança de 1 milhão de caracteres.")
            pages.append(page_text)
            total_chars += len(page_text)
        text = "\n".join(pages)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("Não foi possível ler o conteúdo deste PDF.") from exc
    finally:
        document.close()

    flattened = re.sub(r"[\t\r]+", " ", text)
    result: dict = {key: _find(patterns, flattened, _number) for key, patterns in FIELD_PATTERNS.items()}

    money_value = r"(?:R\$\s*)?([\d.]+,\d{2})"
    total_patterns = [
        r"(?:valor\s+total\s+da\s+fatura|total\s+da\s+fatura|total\s+a\s+pagar|valor\s+a\s+pagar)[^\d]{0,40}" + money_value,
    ]
    paid_patterns = [r"(?:valor\s+pago|pagamento\s+efetuado)[^\d]{0,40}" + money_value]
    result["total_amount_brl"] = _find(total_patterns, flattened, _money)
    result["paid_amount_brl"] = _find(paid_patterns, flattened, _money)
    result["due_date"] = _date_near(r"(?:vencimento|data\s+de\s+vencimento)", flattened)

    field_labels = {
        "billed_consumption_kwh": "Consumo faturado",
        "injected_kwh": "Energia injetada",
        "compensated_kwh": "Energia compensada",
        "accumulated_credits_kwh": "Créditos acumulados",
        "total_amount_brl": "Valor total",
        "paid_amount_brl": "Valor pago",
        "due_date": "Vencimento",
    }
    result["extracted_fields"] = [label for key, label in field_labels.items() if result.get(key) is not None]
    return result
