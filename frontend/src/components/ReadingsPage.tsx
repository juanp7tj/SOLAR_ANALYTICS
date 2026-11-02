import { useState } from 'react';
import { Activity, Check, Plus, Trash2, UploadCloud } from 'lucide-react';
import { api, formatDate, formatKwh } from '../lib/api';
import type { EnergyRecord } from '../types';
import { Badge, EmptyState, Field, Panel, SectionTitle } from './Primitives';

const today = new Date().toISOString().slice(0, 10);

export function ReadingsPage({ readings, onRefresh, notify }: { readings: EnergyRecord[]; onRefresh: () => Promise<void>; notify: (message: string, tone?: 'success' | 'error') => void }) {
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [recordDate, setRecordDate] = useState(today);
  const [production, setProduction] = useState('');
  const [consumption, setConsumption] = useState('');
  const [injected, setInjected] = useState('');
  const [compensated, setCompensated] = useState('');
  const [notes, setNotes] = useState('');
  const [error, setError] = useState('');

  async function createRecord(event: React.FormEvent) {
    event.preventDefault(); setError('');
    if ([production, consumption, injected, compensated].every((item) => item === '')) { setError('Informe pelo menos uma quantidade de energia.'); return; }
    setSaving(true);
    const toNumber = (value: string) => value === '' ? null : Number(value);
    try {
      await api('/readings', { method: 'POST', body: JSON.stringify({ record_date: recordDate, production_kwh: toNumber(production), consumption_kwh: toNumber(consumption), injected_kwh: toNumber(injected), compensated_kwh: toNumber(compensated), notes: notes || null, source: 'manual' }) });
      setOpen(false); setProduction(''); setConsumption(''); setInjected(''); setCompensated(''); setNotes(''); notify('Medição real adicionada.'); await onRefresh();
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Não foi possível salvar.'); }
    finally { setSaving(false); }
  }

  async function removeRecord(row: EnergyRecord) {
    if (!window.confirm(`Excluir a medição de ${formatDate(row.record_date)}?`)) return;
    try { await api<void>(`/readings/${row.id}`, { method: 'DELETE' }); notify('Medição removida.'); await onRefresh(); }
    catch (reason) { notify(reason instanceof Error ? reason.message : 'Não foi possível remover.', 'error'); }
  }

  const sorted = [...readings].sort((a, b) => b.record_date.localeCompare(a.record_date));
  const latest = sorted[0];
  return <div className="page-content module-page">
    <SectionTitle eyebrow="MEDIÇÕES DA INSTALAÇÃO" title="Leituras de energia" detail="Registre os dados disponíveis por dia. Produção, consumo, injeção e compensação não são intercambiáveis." action={<><button className="button button-quiet" onClick={() => window.location.assign('/api/export.csv?kind=readings')}><UploadCloud size={15} />Exportar CSV</button><button className="button button-primary" onClick={() => setOpen(!open)}><Plus size={16} />Nova medição</button></>} />
    <div className="reading-highlight-grid"><Panel className="reading-highlight"><span className="reading-highlight-symbol"><Activity size={18} /></span><div><span>Última leitura</span><strong>{latest ? formatDate(latest.record_date) : '—'}</strong><small>{latest?.is_demo ? 'Registro fictício de demonstração' : 'Data do último registro'}</small></div></Panel><Panel className="reading-definition"><span className="eyebrow">GRANDEZAS REGISTRADAS</span><div className="definition-tags"><Badge tone="green">Produzida</Badge><Badge tone="blue">Consumida</Badge><Badge tone="lime">Injetada</Badge><Badge tone="amber">Compensada</Badge></div><p>Deixe em branco o que não foi medido. O sistema mantém valores desconhecidos como “—”.</p></Panel></div>
    {open && <Panel className="reading-form-panel"><div className="table-head"><div><h3>Adicionar leitura manual</h3><p>Unidade dos campos de energia: kWh.</p></div><button className="icon-button" aria-label="Fechar formulário" onClick={() => setOpen(false)}>×</button></div><form onSubmit={createRecord}>
      <div className="reading-fields"><Field label="Data da leitura"><input type="date" value={recordDate} onChange={(event) => setRecordDate(event.target.value)} required /></Field>
        <Field label="Energia produzida"><div className="input-suffix-wrap"><input type="number" min="0" step="0.01" value={production} onChange={(event) => setProduction(event.target.value)} placeholder="Opcional" /><span>kWh</span></div></Field>
        <Field label="Energia consumida"><div className="input-suffix-wrap"><input type="number" min="0" step="0.01" value={consumption} onChange={(event) => setConsumption(event.target.value)} placeholder="Opcional" /><span>kWh</span></div></Field>
        <Field label="Energia injetada na rede"><div className="input-suffix-wrap"><input type="number" min="0" step="0.01" value={injected} onChange={(event) => setInjected(event.target.value)} placeholder="Opcional" /><span>kWh</span></div></Field>
        <Field label="Energia compensada"><div className="input-suffix-wrap"><input type="number" min="0" step="0.01" value={compensated} onChange={(event) => setCompensated(event.target.value)} placeholder="Opcional" /><span>kWh</span></div></Field>
        <Field label="Observações"><input value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Fonte da leitura, observação..." /></Field>
      </div>
      {error && <div className="inline-error">{error}</div>}<div className="form-bottom"><span className="muted-note">Registros manuais são marcados como dados reais.</span><button type="button" className="button button-quiet" onClick={() => setOpen(false)}>Cancelar</button><button className="button button-primary" disabled={saving}>{saving ? 'Salvando…' : <><Check size={15} />Salvar leitura</>}</button></div>
    </form></Panel>}
    <Panel className="invoice-table-panel"><div className="table-head"><div><h3>Histórico de medições</h3><p>{sorted.length} registros · mais recentes primeiro</p></div></div>
      {sorted.length ? <div className="table-scroll"><table className="data-table"><thead><tr><th>Data</th><th>Energia produzida</th><th>Energia consumida</th><th>Injetada na rede</th><th>Compensada</th><th>Origem</th><th>Observações</th><th></th></tr></thead><tbody>{sorted.map((row) => <tr key={row.id}><td><strong>{formatDate(row.record_date)}</strong></td><td>{formatKwh(row.production_kwh)}</td><td>{formatKwh(row.consumption_kwh)}</td><td>{formatKwh(row.injected_kwh)}</td><td>{formatKwh(row.compensated_kwh)}</td><td><Badge tone={row.is_demo ? 'amber' : 'green'}>{row.is_demo ? 'Demo' : row.source === 'manual' ? 'Manual' : row.source}</Badge></td><td className="notes-cell" title={row.notes || ''}>{row.notes || '—'}</td><td><button className="icon-button icon-button-danger" aria-label="Excluir medição" title="Excluir medição" onClick={() => removeRecord(row)}><Trash2 size={15} /></button></td></tr>)}</tbody></table></div> : <EmptyState icon={<Activity size={20} />} title="Ainda não há medições" detail="Registre as grandezas disponíveis para começar a comparar a instalação." />}
    </Panel>
  </div>;
}
