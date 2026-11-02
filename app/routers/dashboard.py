from __future__ import annotations

import calendar
from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import EnergyRecord, Invoice, TariffConfig
from app.schemas import DashboardOut
from app.services.demo import demo_counts

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


def _period_range(period: str, anchor: date) -> tuple[date, date]:
    if period == "day":
        return anchor, anchor
    if period == "week":
        start = anchor - timedelta(days=anchor.weekday())
        return start, start + timedelta(days=6)
    if period == "year":
        return date(anchor.year, 1, 1), date(anchor.year, 12, 31)
    return date(anchor.year, anchor.month, 1), date(anchor.year, anchor.month, calendar.monthrange(anchor.year, anchor.month)[1])


def _sum_known(rows: list, attribute: str) -> float | None:
    values = [getattr(row, attribute) for row in rows]
    if not values or any(value is None for value in values):
        return None
    return round(sum(values), 2)


def _date_bucket(rows: list[EnergyRecord], day: date) -> dict:
    match = [row for row in rows if row.record_date == day]
    return {
        "date": day.isoformat(),
        "label": day.strftime("%d %b"),
        "production_kwh": _sum_known(match, "production_kwh"),
        "consumption_kwh": _sum_known(match, "consumption_kwh"),
        "injected_kwh": _sum_known(match, "injected_kwh"),
    }


def _month_bucket(rows: list[EnergyRecord], year: int, month: int) -> dict:
    match = [row for row in rows if row.record_date.year == year and row.record_date.month == month]
    return {
        "month": f"{year:04d}-{month:02d}",
        "label": calendar.month_abbr[month].upper(),
        "production_kwh": _sum_known(match, "production_kwh"),
        "consumption_kwh": _sum_known(match, "consumption_kwh"),
    }


@router.get("", response_model=DashboardOut)
def get_dashboard(
    period: str = Query(default="month", pattern="^(day|week|month|year)$"),
    anchor: date | None = Query(default=None),
    db: Session = Depends(get_db),
):
    today = anchor or date.today()
    start, end = _period_range(period, today)
    rows = db.scalars(select(EnergyRecord).where(EnergyRecord.record_date >= start, EnergyRecord.record_date <= end)).all()
    all_rows = db.scalars(select(EnergyRecord).order_by(EnergyRecord.record_date.asc())).all()
    invoices = db.scalars(select(Invoice).order_by(Invoice.billing_period_end.desc().nullslast(), Invoice.created_at.desc())).all()
    tariff = db.get(TariffConfig, 1)

    production = _sum_known(rows, "production_kwh")
    consumption = _sum_known(rows, "consumption_kwh")
    injected = _sum_known(rows, "injected_kwh")
    compensated = _sum_known(rows, "compensated_kwh")

    complete_pair = bool(rows) and all(row.production_kwh is not None and row.injected_kwh is not None and row.consumption_kwh is not None for row in rows)
    complete_consumption = bool(rows) and all(row.consumption_kwh is not None for row in rows)
    self_consumed = None
    utilization = coverage = None
    if complete_pair:
        self_consumed = round(sum(max(0, min(row.production_kwh - row.injected_kwh, row.consumption_kwh)) for row in rows), 2)
        if production and production > 0:
            utilization = round(self_consumed / production * 100, 1)
        if consumption is not None and consumption > 0 and complete_consumption:
            coverage = round(min(self_consumed, consumption) / consumption * 100, 1)

    rate = float(tariff.energy_rate_brl_kwh) if tariff and tariff.energy_rate_brl_kwh is not None else None
    availability = float(tariff.availability_cost_brl) if tariff and tariff.availability_cost_brl is not None else None
    compensation_factor = tariff.compensation_factor_percent if tariff else None
    savings = None
    if not rows:
        savings_status = "Cadastre medições no período para estimar a economia."
    elif rate is None or availability is None or compensation_factor is None:
        missing = []
        if rate is None:
            missing.append("tarifa de energia")
        if availability is None:
            missing.append("custo de disponibilidade")
        if compensation_factor is None:
            missing.append("fator de compensação")
        savings_status = "Informe " + ", ".join(missing) + "; a economia total não será presumida."
    elif not complete_pair or any(row.compensated_kwh is None for row in rows):
        savings_status = "Há medições incompletas; a economia total não pode ser determinada com segurança."
    else:
        direct_kwh = sum(max(0, min(row.production_kwh - row.injected_kwh, row.consumption_kwh or 0)) for row in rows)
        credited_kwh = sum(row.compensated_kwh or 0 for row in rows)
        savings = round(direct_kwh * rate + credited_kwh * rate * compensation_factor / 100, 2)
        savings_status = "Estimativa bruta de energia evitada/compensada. O custo de disponibilidade informado permanece como parcela não compensável e é exibido separadamente; tributos e itens tarifários não configurados ficam fora do cálculo."

    last_invoice = invoices[0] if invoices else None
    latest_credit = float(last_invoice.accumulated_credits_kwh) if last_invoice and last_invoice.accumulated_credits_kwh is not None else None
    recent_days = [today - timedelta(days=13 - i) for i in range(14)]
    monthly_dates = []
    month_index = today.year * 12 + today.month - 1
    for offset in range(11, -1, -1):
        year, month_zero = divmod(month_index - offset, 12)
        monthly_dates.append((year, month_zero + 1))

    financial = []
    for invoice in reversed(invoices[:6]):
        bill_date = invoice.billing_period_end or invoice.issue_date or invoice.due_date
        if bill_date:
            financial.append({"month": bill_date.strftime("%Y-%m"), "label": bill_date.strftime("%b").upper(), "amount_brl": float(invoice.total_amount_brl) if invoice.total_amount_brl is not None else None, "paid_amount_brl": float(invoice.paid_amount_brl) if invoice.paid_amount_brl is not None else None})

    demo_record_count, demo_invoice_count = demo_counts(db)
    return DashboardOut(
        period=period,
        start_date=start,
        end_date=end,
        production_kwh=production,
        consumption_kwh=consumption,
        injected_kwh=injected,
        compensated_kwh=compensated,
        last_invoice_amount_brl=float(last_invoice.total_amount_brl) if last_invoice and last_invoice.total_amount_brl is not None else None,
        last_invoice_due_date=last_invoice.due_date if last_invoice else None,
        self_consumed_kwh=self_consumed,
        solar_utilization_percent=utilization,
        consumption_coverage_percent=coverage,
        accumulated_credits_kwh=latest_credit,
        estimated_savings_brl=savings,
        savings_status=savings_status,
        energy_rate_brl_kwh=rate,
        availability_cost_brl=availability,
        compensation_factor_percent=compensation_factor,
        daily_series=[_date_bucket(all_rows, day) for day in recent_days],
        monthly_series=[_month_bucket(all_rows, year, month) for year, month in monthly_dates],
        comparison_series=[_month_bucket(all_rows, year, month) for year, month in monthly_dates],
        financial_series=financial,
        demo_records=demo_record_count,
        demo_invoices=demo_invoice_count,
        record_count=len(rows),
    )
