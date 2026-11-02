export type Period = 'day' | 'week' | 'month' | 'year';
export type Section = 'dashboard' | 'readings' | 'invoices' | 'goodwe' | 'settings';

export interface AuthStatus {
  auth_required: boolean;
  authenticated: boolean;
  volatile_storage: boolean;
}

export interface EnergyRecord {
  id: number;
  record_date: string;
  production_kwh: number | null;
  consumption_kwh: number | null;
  injected_kwh: number | null;
  compensated_kwh: number | null;
  source: 'manual' | 'goodwe' | 'import';
  notes: string | null;
  is_demo: boolean;
  created_at: string;
}

export interface Invoice {
  id: number;
  billing_period_start: string | null;
  billing_period_end: string | null;
  issue_date: string | null;
  due_date: string | null;
  paid_date: string | null;
  billed_consumption_kwh: number | null;
  injected_kwh: number | null;
  compensated_kwh: number | null;
  accumulated_credits_kwh: number | null;
  total_amount_brl: number | null;
  paid_amount_brl: number | null;
  payment_status: 'pending' | 'paid' | 'overdue' | 'partial';
  source_filename: string | null;
  notes: string | null;
  is_demo: boolean;
  created_at: string;
}

export interface Tariffs {
  energy_rate_brl_kwh: number | null;
  availability_cost_brl: number | null;
  compensation_factor_percent: number | null;
  updated_at?: string | null;
}

export interface DashboardData {
  period: Period;
  start_date: string;
  end_date: string;
  production_kwh: number | null;
  consumption_kwh: number | null;
  injected_kwh: number | null;
  compensated_kwh: number | null;
  last_invoice_amount_brl: number | null;
  last_invoice_due_date: string | null;
  self_consumed_kwh: number | null;
  solar_utilization_percent: number | null;
  consumption_coverage_percent: number | null;
  accumulated_credits_kwh: number | null;
  estimated_savings_brl: number | null;
  savings_status: string;
  energy_rate_brl_kwh: number | null;
  availability_cost_brl: number | null;
  compensation_factor_percent: number | null;
  daily_series: Array<{ date: string; label: string; production_kwh: number | null; consumption_kwh: number | null; injected_kwh: number | null }>;
  monthly_series: Array<{ month: string; label: string; production_kwh: number | null; consumption_kwh: number | null }>;
  comparison_series: Array<{ month: string; label: string; production_kwh: number | null; consumption_kwh: number | null }>;
  financial_series: Array<{ month: string; label: string; amount_brl: number | null; paid_amount_brl: number | null }>;
  demo_records: number;
  demo_invoices: number;
  record_count: number;
}

export interface GoodWeStatus {
  app_id: string | null;
  plant_id: string | null;
  secret_configured: boolean;
  status: string;
}

export interface DemoStatus {
  enabled: boolean;
  demo_records: number;
  demo_invoices: number;
}

export interface InvoiceDraft {
  billing_period_start: string | null;
  billing_period_end: string | null;
  issue_date: string | null;
  due_date: string | null;
  paid_date: string | null;
  billed_consumption_kwh: number | null;
  injected_kwh: number | null;
  compensated_kwh: number | null;
  accumulated_credits_kwh: number | null;
  total_amount_brl: number | null;
  paid_amount_brl: number | null;
  payment_status: Invoice['payment_status'];
  source_filename: string | null;
  notes: string | null;
}
