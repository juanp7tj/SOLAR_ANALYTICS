import { BatteryCharging, CircleDollarSign, Gauge, SunMedium, Zap } from 'lucide-react';
import type { DashboardData, Period } from '../types';
import { formatBrl, formatDate, formatKwh, shortNumber } from '../lib/api';
import { Badge, Panel, SectionTitle } from './Primitives';
import { DailyChart, FinanceChart, MonthlyChart } from './Charts';

const periods: Array<{ id: Period; label: string }> = [
  { id: 'day', label: 'Dia' }, { id: 'week', label: 'Semana' }, { id: 'month', label: 'Mês' }, { id: 'year', label: 'Ano' },
];

function MetricCard({ icon, label, value, unit, hint, accent, className = '' }: { icon: React.ReactNode; label: string; value: string; unit?: string; hint: string; accent: 'green' | 'blue' | 'lime' | 'amber'; className?: string }) {
  return <Panel className={`metric-card metric-${accent} ${className}`}>
    <div className="metric-top"><span className="metric-icon">{icon}</span><span className="metric-orbit" /></div>
    <div className="metric-label">{label}</div>
    <div className="metric-number">{value}{unit && <small>{unit}</small>}</div>
    <div className="metric-hint">{hint}</div>
  </Panel>;
}

export function Dashboard({ data, period, onPeriodChange, onNavigate }: { data: DashboardData; period: Period; onPeriodChange: (value: Period) => void; onNavigate: (page: 'invoices' | 'readings') => void }) {
  const periodRange = `${formatDate(data.start_date, { day: '2-digit', month: 'short' })} — ${formatDate(data.end_date, { day: '2-digit', month: 'short', year: 'numeric' })}`;
  return <div className="page-content">
    <div className="dashboard-heading">
      <SectionTitle eyebrow="CENTRAL DE ENERGIA · RESIDENCIAL" title="Visão geral" detail="Sua energia, em perspectiva. Acompanhe a geração e o impacto na sua conta." />
      <div className="period-control" role="group" aria-label="Filtrar por período">
        {periods.map((option) => <button key={option.id} className={period === option.id ? 'period-active' : ''} onClick={() => onPeriodChange(option.id)}>{option.label}</button>)}
        <span className="period-range">{periodRange}</span>
      </div>
    </div>

    <div className="metrics-grid">
      <MetricCard icon={<SunMedium size={19} />} label="Energia produzida" value={shortNumber(data.production_kwh, 1)} unit="kWh" hint="Geração solar no período" accent="green" />
      <MetricCard icon={<Zap size={18} />} label="Energia consumida" value={shortNumber(data.consumption_kwh, 1)} unit="kWh" hint="Consumo residencial medido" accent="blue" />
      <MetricCard icon={<BatteryCharging size={18} />} label="Injetada na rede" value={shortNumber(data.injected_kwh, 1)} unit="kWh" hint="Energia enviada à distribuidora" accent="lime" />
      <MetricCard icon={<CircleDollarSign size={18} />} label="Última fatura" value={formatBrl(data.last_invoice_amount_brl)} hint={data.last_invoice_due_date ? `Vencimento · ${formatDate(data.last_invoice_due_date)}` : 'Cadastre uma fatura para acompanhar'} accent="amber" className="metric-money" />
    </div>

    <div className="charts-grid">
      <DailyChart data={data} />
      <MonthlyChart data={data} />
    </div>

    <div className="lower-grid">
      <Panel className="analysis-panel">
        <div className="panel-heading"><div><span className="eyebrow">LEITURA INTELIGENTE</span><h3>Aproveitamento solar</h3></div><span className="panel-heading-icon"><Gauge size={17} /></span></div>
        <div className="analysis-main"><div className="ring" style={{ '--ring-progress': `${Math.min(data.solar_utilization_percent ?? 0, 100)}%` } as React.CSSProperties}><div><strong>{data.solar_utilization_percent === null ? '—' : `${shortNumber(data.solar_utilization_percent, 0)}%`}</strong><span>uso local</span></div></div><div className="analysis-kpis"><div><span>Autoconsumida</span><strong>{formatKwh(data.self_consumed_kwh)}</strong></div><div><span>Compensada</span><strong>{formatKwh(data.compensated_kwh)}</strong></div><div><span>Cobertura do consumo</span><strong>{data.consumption_coverage_percent === null ? '—' : `${shortNumber(data.consumption_coverage_percent, 1)}%`}</strong></div></div></div>
        <div className="savings-line"><span>Economia estimada</span><strong>{formatBrl(data.estimated_savings_brl)}</strong></div>
        <p className="calculation-note">{data.savings_status}</p>
        <div className="tariff-foot"><span>Disponibilidade configurada</span><strong>{data.availability_cost_brl === null ? 'Não informado' : formatBrl(data.availability_cost_brl)}</strong></div>
      </Panel>
      <FinanceChart data={data} />
    </div>

    <Panel className="credit-strip">
      <div className="credit-symbol"><BatteryCharging size={20} /></div>
      <div className="credit-copy"><span className="eyebrow">SALDO DA DISTRIBUIDORA</span><strong>{formatKwh(data.accumulated_credits_kwh)}</strong><small>Créditos acumulados da última fatura cadastrada</small></div>
      <div className="credit-explainer"><Badge tone={data.accumulated_credits_kwh === null ? 'amber' : 'green'} dot>{data.accumulated_credits_kwh === null ? 'Sem saldo informado' : 'Dado da fatura'}</Badge><p>Energia produzida, injetada e compensada são indicadores distintos. O saldo só aparece quando informado em uma fatura.</p></div>
      <div className="credit-actions"><button className="button button-quiet" onClick={() => onNavigate('readings')}>Adicionar medição</button><button className="button button-primary" onClick={() => onNavigate('invoices')}>Registrar fatura</button></div>
    </Panel>
    <div className="page-footnote"><span><span className="footnote-dot" />Dados locais sincronizados com SQLite</span><span>{data.record_count} medições no período · {periodRange}</span></div>
  </div>;
}
