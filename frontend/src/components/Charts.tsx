import { Area, AreaChart, Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { ReactNode } from 'react';
import type { DashboardData } from '../types';
import { formatBrl, shortNumber } from '../lib/api';
import { EmptyState, Panel } from './Primitives';
import { Activity, BarChart3, CircleDollarSign } from 'lucide-react';

const axisStyle = { fill: '#70808b', fontSize: 10, fontFamily: 'DM Mono, monospace' };
const tooltipStyle = { background: '#10191f', border: '1px solid rgba(143, 166, 174, .16)', borderRadius: 12, color: '#e7f1ef', boxShadow: '0 15px 45px rgba(0,0,0,.4)' };

function ChartHead({ icon, title, note, legend }: { icon: ReactNode; title: string; note: string; legend: Array<{ color: string; label: string }> }) {
  return <div className="chart-head"><div className="chart-title"><span className="chart-icon">{icon}</span><div><h3>{title}</h3><p>{note}</p></div></div><div className="chart-legend">{legend.map((item) => <span key={item.label}><i style={{ background: item.color }} />{item.label}</span>)}</div></div>;
}

function ChartPlaceholder({ detail }: { detail: string }) {
  return <EmptyState title="Sem leituras neste intervalo" detail={detail} />;
}

export function DailyChart({ data }: { data: DashboardData }) {
  const visible = data.daily_series.some((point) => point.production_kwh !== null || point.consumption_kwh !== null);
  return <Panel className="chart-panel chart-wide">
    <ChartHead icon={<Activity size={16} />} title="Geração & consumo diário" note="Acompanhamento dos últimos 14 dias" legend={[{ color: '#17d39c', label: 'Produção' }, { color: '#8ea1af', label: 'Consumo' }, { color: '#c8f278', label: 'Injetada' }]} />
    <div className="chart-canvas">{visible ? <ResponsiveContainer width="100%" height="100%"><AreaChart data={data.daily_series} margin={{ top: 10, right: 8, left: -20, bottom: 0 }}>
      <defs><linearGradient id="solarFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#16d39a" stopOpacity={0.28} /><stop offset="96%" stopColor="#16d39a" stopOpacity={0.01} /></linearGradient></defs>
      <CartesianGrid stroke="#26323a" strokeDasharray="3 6" vertical={false} />
      <XAxis dataKey="label" axisLine={false} tickLine={false} tick={axisStyle} dy={8} />
      <YAxis axisLine={false} tickLine={false} tick={axisStyle} width={42} tickFormatter={(value) => shortNumber(Number(value))} />
      <Tooltip contentStyle={tooltipStyle} formatter={(value, name) => [value == null ? 'Sem dado' : `${shortNumber(Number(value), 1)} kWh`, name === 'production_kwh' ? 'Produção' : name === 'consumption_kwh' ? 'Consumo' : 'Injetada']} />
      <Area type="monotone" dataKey="production_kwh" name="production_kwh" stroke="#16d39a" strokeWidth={2.5} fill="url(#solarFill)" connectNulls={false} activeDot={{ r: 4, stroke: '#09120f', strokeWidth: 2 }} />
      <Area type="monotone" dataKey="consumption_kwh" name="consumption_kwh" stroke="#93a7b7" strokeWidth={1.8} fill="transparent" connectNulls={false} activeDot={{ r: 3 }} />
      <Area type="monotone" dataKey="injected_kwh" name="injected_kwh" stroke="#c8f278" strokeWidth={1.5} strokeDasharray="4 5" fill="transparent" connectNulls={false} activeDot={{ r: 3 }} />
    </AreaChart></ResponsiveContainer> : <ChartPlaceholder detail="Cadastre medições manuais ou importe dados reais para visualizar as séries." />}</div>
  </Panel>;
}

export function MonthlyChart({ data }: { data: DashboardData }) {
  const visible = data.monthly_series.some((point) => point.production_kwh !== null || point.consumption_kwh !== null);
  return <Panel className="chart-panel">
    <ChartHead icon={<BarChart3 size={16} />} title="Produção x consumo" note="Comparativo mensal · kWh" legend={[{ color: '#17d39c', label: 'Produção' }, { color: '#647888', label: 'Consumo' }]} />
    <div className="chart-canvas chart-short">{visible ? <ResponsiveContainer width="100%" height="100%"><BarChart data={data.monthly_series} margin={{ top: 8, right: 4, left: -22, bottom: 0 }} barGap={5}>
      <CartesianGrid stroke="#26323a" strokeDasharray="3 6" vertical={false} />
      <XAxis dataKey="label" axisLine={false} tickLine={false} tick={axisStyle} dy={8} />
      <YAxis axisLine={false} tickLine={false} tick={axisStyle} width={40} tickFormatter={(value) => shortNumber(Number(value))} />
      <Tooltip contentStyle={tooltipStyle} formatter={(value, name) => [value == null ? 'Sem dado' : `${shortNumber(Number(value), 1)} kWh`, name === 'production_kwh' ? 'Produção' : 'Consumo']} />
      <Bar dataKey="production_kwh" name="production_kwh" fill="#17d39c" radius={[5, 5, 0, 0]} maxBarSize={16} />
      <Bar dataKey="consumption_kwh" name="consumption_kwh" fill="#516473" radius={[5, 5, 0, 0]} maxBarSize={16} />
    </BarChart></ResponsiveContainer> : <ChartPlaceholder detail="Os dados aparecem por mês conforme suas medições." />}</div>
  </Panel>;
}

export function FinanceChart({ data }: { data: DashboardData }) {
  const visible = data.financial_series.length > 0 && data.financial_series.some((point) => point.amount_brl !== null);
  return <Panel className="chart-panel">
    <ChartHead icon={<CircleDollarSign size={16} />} title="Evolução das contas" note="Faturas cadastradas · R$" legend={[{ color: '#c8f278', label: 'Valor total' }, { color: '#17d39c', label: 'Valor pago' }]} />
    <div className="chart-canvas chart-short">{visible ? <ResponsiveContainer width="100%" height="100%"><BarChart data={data.financial_series} margin={{ top: 8, right: 4, left: -20, bottom: 0 }} barGap={4}>
      <CartesianGrid stroke="#26323a" strokeDasharray="3 6" vertical={false} />
      <XAxis dataKey="label" axisLine={false} tickLine={false} tick={axisStyle} dy={8} />
      <YAxis axisLine={false} tickLine={false} tick={axisStyle} width={42} tickFormatter={(value) => `R$${shortNumber(Number(value))}`} />
      <Tooltip contentStyle={tooltipStyle} formatter={(value, name) => [value == null ? 'Sem dado' : formatBrl(Number(value)), name === 'amount_brl' ? 'Valor da fatura' : 'Valor pago']} />
      <Bar dataKey="amount_brl" name="amount_brl" fill="#c8f278" radius={[5, 5, 0, 0]} maxBarSize={17} />
      <Bar dataKey="paid_amount_brl" name="paid_amount_brl" fill="#17d39c" radius={[5, 5, 0, 0]} maxBarSize={17} />
    </BarChart></ResponsiveContainer> : <ChartPlaceholder detail="Cadastre faturas para acompanhar a evolução financeira." />}</div>
  </Panel>;
}
