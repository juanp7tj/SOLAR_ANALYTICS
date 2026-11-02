from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, Float, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class EnergyRecord(Base):
    __tablename__ = "energy_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    record_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    production_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    consumption_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    injected_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    compensated_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(40), default="manual", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    billing_period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    billing_period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, index=True, nullable=True)
    paid_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    billed_consumption_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    injected_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    compensated_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    accumulated_credits_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_amount_brl: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    paid_amount_brl: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    payment_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    source_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class TariffConfig(Base):
    __tablename__ = "tariff_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    energy_rate_brl_kwh: Mapped[Decimal | None] = mapped_column(Numeric(10, 5), nullable=True)
    availability_cost_brl: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    compensation_factor_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class GoodWeConfig(Base):
    __tablename__ = "goodwe_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    app_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    plant_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[str] = mapped_column(String(255), nullable=False)
