from __future__ import annotations

import random
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AppSetting, EnergyRecord, Invoice


DEMO_FLAG = "demo_seeded_once"


def demo_counts(db: Session) -> tuple[int, int]:
    return (
        len(db.scalars(select(EnergyRecord.id).where(EnergyRecord.is_demo.is_(True))).all()),
        len(db.scalars(select(Invoice.id).where(Invoice.is_demo.is_(True))).all()),
    )


def seed_demo_if_first_run(db: Session, auto_load: bool) -> None:
    marker = db.get(AppSetting, DEMO_FLAG)
    if marker:
        return
    if auto_load and not db.scalar(select(EnergyRecord.id).limit(1)) and not db.scalar(select(Invoice.id).limit(1)):
        rng = random.Random(2026)
        today = date.today()
        for offset in range(89, -1, -1):
            day = today - timedelta(days=offset)
            production = round(max(3.5, rng.gauss(19.2, 4.2)), 2)
            consumption = round(max(5.0, rng.gauss(17.0, 3.3)), 2)
            self_use_ratio = rng.uniform(0.38, 0.64)
            injected = round(production * (1 - self_use_ratio), 2)
            compensated = round(min(injected, rng.uniform(4, 13)), 2)
            db.add(EnergyRecord(
                record_date=day,
                production_kwh=production,
                consumption_kwh=consumption,
                injected_kwh=injected,
                compensated_kwh=compensated,
                source="manual",
                notes="Amostra fictícia para demonstração; substitua por dados reais.",
                is_demo=True,
            ))

        for month_offset in range(5, -1, -1):
            month_index = today.year * 12 + today.month - 1 - month_offset
            year, month_zero = divmod(month_index, 12)
            month = month_zero + 1
            end_day = min(25, (date(year + (month == 12), 1 if month == 12 else month + 1, 1) - timedelta(days=1)).day)
            bill_date = date(year, month, end_day)
            total = round(rng.uniform(164, 245), 2)
            bill_due = bill_date + timedelta(days=10)
            db.add(Invoice(
                billing_period_start=date(year, month, 1),
                billing_period_end=bill_date,
                issue_date=bill_date,
                due_date=bill_due,
                paid_date=bill_due - timedelta(days=2) if month_offset > 0 else None,
                billed_consumption_kwh=round(rng.uniform(280, 370), 2),
                injected_kwh=round(rng.uniform(145, 245), 2),
                compensated_kwh=round(rng.uniform(120, 210), 2),
                accumulated_credits_kwh=round(rng.uniform(180, 520), 2),
                total_amount_brl=Decimal(str(total)),
                paid_amount_brl=Decimal(str(total)) if month_offset > 0 else None,
                payment_status="paid" if month_offset > 0 else "pending",
                source_filename="Demonstração fictícia — não é fatura real",
                notes="Dados fictícios para demonstração; não representam uma conta ou instalação real.",
                is_demo=True,
            ))
    db.add(AppSetting(key=DEMO_FLAG, value="true"))
    db.commit()


def remove_demo(db: Session) -> tuple[int, int]:
    records, invoices = demo_counts(db)
    db.query(EnergyRecord).filter(EnergyRecord.is_demo.is_(True)).delete(synchronize_session=False)
    db.query(Invoice).filter(Invoice.is_demo.is_(True)).delete(synchronize_session=False)
    if not db.get(AppSetting, DEMO_FLAG):
        db.add(AppSetting(key=DEMO_FLAG, value="true"))
    db.commit()
    return records, invoices
