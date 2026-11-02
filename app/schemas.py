from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EnergyRecordBase(BaseModel):
    record_date: date
    production_kwh: float | None = Field(default=None, ge=0)
    consumption_kwh: float | None = Field(default=None, ge=0)
    injected_kwh: float | None = Field(default=None, ge=0)
    compensated_kwh: float | None = Field(default=None, ge=0)
    source: Literal["manual", "goodwe", "import"] = "manual"
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def require_measurement(self):
        if all(value is None for value in (self.production_kwh, self.consumption_kwh, self.injected_kwh, self.compensated_kwh)):
            raise ValueError("Informe ao menos uma medição de energia.")
        return self


class EnergyRecordCreate(EnergyRecordBase):
    pass


class EnergyRecordOut(EnergyRecordBase):
    id: int
    is_demo: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class InvoiceBase(BaseModel):
    billing_period_start: date | None = None
    billing_period_end: date | None = None
    issue_date: date | None = None
    due_date: date | None = None
    paid_date: date | None = None
    billed_consumption_kwh: float | None = Field(default=None, ge=0)
    injected_kwh: float | None = Field(default=None, ge=0)
    compensated_kwh: float | None = Field(default=None, ge=0)
    accumulated_credits_kwh: float | None = Field(default=None, ge=0)
    total_amount_brl: Decimal | None = Field(default=None, ge=0)
    paid_amount_brl: Decimal | None = Field(default=None, ge=0)
    payment_status: Literal["pending", "paid", "overdue", "partial"] = "pending"
    source_filename: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=2000)


class InvoiceCreate(InvoiceBase):
    @model_validator(mode="after")
    def require_invoice_data(self):
        values = [self.billing_period_start, self.billing_period_end, self.issue_date, self.due_date, self.paid_date, self.billed_consumption_kwh, self.injected_kwh, self.compensated_kwh, self.accumulated_credits_kwh, self.total_amount_brl, self.paid_amount_brl]
        if all(value is None for value in values):
            raise ValueError("Informe ao menos um campo da fatura antes de salvar.")
        return self


class InvoiceOut(InvoiceBase):
    id: int
    is_demo: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class TariffUpdate(BaseModel):
    energy_rate_brl_kwh: Decimal | None = Field(default=None, ge=0, le=100)
    availability_cost_brl: Decimal | None = Field(default=None, ge=0, le=100000)
    compensation_factor_percent: float | None = Field(default=None, ge=0, le=100)


class TariffOut(TariffUpdate):
    updated_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


class GoodWeCredentialsUpdate(BaseModel):
    app_id: str = Field(min_length=1, max_length=255)
    app_secret: str | None = Field(default=None, max_length=4096)
    plant_id: str = Field(min_length=1, max_length=255)


class GoodWeConfigOut(BaseModel):
    app_id: str | None = None
    plant_id: str | None = None
    secret_configured: bool = False
    status: str = "Aguardando credenciais da API GoodWe"


class DashboardOut(BaseModel):
    period: str
    start_date: date
    end_date: date
    production_kwh: float | None
    consumption_kwh: float | None
    injected_kwh: float | None
    compensated_kwh: float | None
    last_invoice_amount_brl: float | None
    last_invoice_due_date: date | None
    self_consumed_kwh: float | None
    solar_utilization_percent: float | None
    consumption_coverage_percent: float | None
    accumulated_credits_kwh: float | None
    estimated_savings_brl: float | None
    savings_status: str
    energy_rate_brl_kwh: float | None
    availability_cost_brl: float | None
    compensation_factor_percent: float | None
    daily_series: list[dict]
    monthly_series: list[dict]
    comparison_series: list[dict]
    financial_series: list[dict]
    demo_records: int
    demo_invoices: int
    record_count: int


class DemoStatus(BaseModel):
    enabled: bool
    demo_records: int
    demo_invoices: int


class PdfExtractOut(InvoiceBase):
    extracted_fields: list[str] = []
    file_name: str
    warning: str = "Revise os campos extraídos. Campos não encontrados permanecem vazios."
