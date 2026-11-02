import { useEffect, useState } from 'react';
import { Archive, Check, Database, FileDown, RotateCcw, Save, ShieldCheck, Upload } from 'lucide-react';
import { api, downloadFile, formatBrl } from '../lib/api';
import type { Tariffs } from '../types';
import { Field, Panel, SectionTitle } from './Primitives';

export function SettingsPage({ tariffs, onRefresh, notify }: { tariffs: Tariffs; onRefresh: () => Promise<void>; notify: (message: string, tone?: 'success' | 'error') => void }) {
  const [rate, setRate] = useState('');
  const [availability, setAvailability] = useState('');
  const [compensation, setCompensation] = useState('');
  const [saving, setSaving] = useState(false);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    setRate(tariffs.energy_rate_brl_kwh == null ? '' : String(tariffs.energy_rate_brl_kwh));
    setAvailability(tariffs.availability_cost_brl == null ? '' : String(tariffs.availability_cost_brl));
    setCompensation(tariffs.compensation_factor_percent == null ? '' : String(tariffs.compensation_factor_percent));
  }, [tariffs]);

  async function saveTariffs(event: React.FormEvent) {
    event.preventDefault(); setSaving(true);
    const numeric = (value: string) => value === '' ? null : Number(value);
    try {
      await api<Tariffs>('/settings/tariffs', { method: 'PUT', body: JSON.stringify({ energy_rate_brl_kwh: numeric(rate), availability_cost_brl: numeric(availability), compensation_factor_percent: numeric(compensation) }) });
      notify('Parâmetros tarifários salvos.'); await onRefresh();
    } catch (error) { notify(error instanceof Error ? error.message : 'Falha ao salvar tarifas.', 'error'); }
    finally { setSaving(false); }
  }

  async function createBackup() {
    setBusy(true);
    try {
      const response = await fetch('/api/backup', { method: 'POST', cache: 'no-store' });
      if (!response.ok) throw new Error('Não foi possível gerar o backup SQLite.');
      const blob = await response.blob(); const url = URL.createObjectURL(blob); const link = document.createElement('a');
      link.href = url; link.download = `solar_analytics_backup_${new Date().toISOString().slice(0, 10)}.zip`; link.click(); URL.revokeObjectURL(url);
      notify('Backup SQLite gerado e baixado.');
    } catch (error) { notify(error instanceof Error ? error.message : 'Falha no backup.', 'error'); }
    finally { setBusy(false); }
  }

  async function restoreBackup(file?: File) {
    if (!file) return;
    if (!window.confirm('Restaurar este backup substituirá os dados atuais do banco local. Deseja continuar?')) return;
    setBusy(true);
    try {
      const form = new FormData(); form.append('file', file);
      const result = await api<{ message: string }>('/backup/restore', { method: 'POST', body: form });
      notify(result.message); await onRefresh();
    } catch (error) { notify(error instanceof Error ? error.message : 'Falha ao restaurar backup.', 'error'); }
    finally { setBusy(false); }
  }

  async function exportCsv(kind: 'readings' | 'invoices') {
    try { await downloadFile(`/api/export.csv?kind=${kind}`, `solar_analytics_${kind}.csv`); notify(`CSV de ${kind === 'readings' ? 'medições' : 'faturas'} baixado.`); }
    catch (error) { notify(error instanceof Error ? error.message : 'Falha na exportação.', 'error'); }
  }

  return <div className="page-content module-page">
    <SectionTitle eyebrow="CONTROLE LOCAL" title="Configurações & dados" detail="Ajuste os parâmetros usados nas estimativas. Nenhuma tarifa é preenchida automaticamente." />
    <div className="settings-grid">
      <Panel className="settings-panel"><div className="panel-heading"><div><span className="eyebrow">BASE DA ESTIMATIVA</span><h3>Parâmetros tarifários</h3></div><span className="panel-heading-icon"><Database size={17} /></span></div><p className="settings-intro">Os campos vazios permanecem desconhecidos. Informe os valores da sua conta e revise a regra de compensação aplicável ao seu sistema.</p>
        <form onSubmit={saveTariffs} className="settings-form">
          <Field label="Tarifa de energia"><div className="input-suffix-wrap"><input type="number" min="0" step="0.00001" value={rate} onChange={(event) => setRate(event.target.value)} placeholder="Não informado" /><span>R$/kWh</span></div></Field>
          <Field label="Custo de disponibilidade"><div className="input-suffix-wrap"><input type="number" min="0" step="0.01" value={availability} onChange={(event) => setAvailability(event.target.value)} placeholder="Não informado" /><span>R$</span></div><small>Parcela mínima informada na fatura; permanece separada da economia estimada.</small></Field>
          <Field label="Fator de compensação"><div className="input-suffix-wrap"><input type="number" min="0" max="100" step="0.01" value={compensation} onChange={(event) => setCompensation(event.target.value)} placeholder="Não informado" /><span>%</span></div><small>Informe o fator que se aplica aos créditos compensados. Não é presumido.</small></Field>
          <div className="settings-form-bottom"><span className="muted-note">Usados apenas para estimativas de energia evitada.</span><button className="button button-primary" disabled={saving}>{saving ? 'Salvando…' : <><Save size={15} />Salvar parâmetros</>}</button></div>
        </form>
        <div className="settings-preview"><div><span>Disponibilidade informada</span><strong>{availability === '' ? '—' : formatBrl(Number(availability))}</strong></div><div><span>Fator informado</span><strong>{compensation === '' ? '—' : `${compensation}%`}</strong></div></div>
      </Panel>

      <Panel className="settings-panel local-data-panel"><div className="panel-heading"><div><span className="eyebrow">ARMAZENAMENTO</span><h3>Dados & privacidade</h3></div><span className="panel-heading-icon"><ShieldCheck size={17} /></span></div><div className="local-data-card"><div className="local-data-icon"><Database size={17} /></div><div><strong>SQLite local</strong><span>O banco fica neste computador. O SOLAR ANALYTICS não envia seus dados para hospedagem externa.</span></div></div>
        <div className="tool-row"><div><strong>Exportar dados em CSV</strong><span>Baixe medições ou faturas em formato tabular.</span></div><div className="tool-actions"><button className="button button-quiet button-small" onClick={() => exportCsv('readings')}><FileDown size={14} />Medições</button><button className="button button-quiet button-small" onClick={() => exportCsv('invoices')}><FileDown size={14} />Faturas</button></div></div>
        <div className="tool-row"><div><strong>Backup completo do banco</strong><span>Cria um ZIP com uma cópia consistente do banco SQLite.</span></div><button className="button button-primary button-small" disabled={busy} onClick={createBackup}>{busy ? 'Aguarde…' : <><Archive size={14} />Baixar backup</>}</button></div>
        <div className="tool-row restore-row"><div><strong>Restaurar backup</strong><span>A restauração substitui o conteúdo atual. O ZIP/SQLite é validado primeiro.</span></div><label className={`button button-quiet button-small ${busy ? 'button-disabled' : ''}`}><Upload size={14} />Selecionar arquivo<input type="file" accept=".zip,.sqlite3,.db" disabled={busy} onChange={(event) => { void restoreBackup(event.target.files?.[0]); event.target.value = ''; }} /></label></div>
      </Panel>
    </div>
    <Panel className="rules-panel"><span className="rules-icon"><RotateCcw size={17} /></span><div><span className="eyebrow">LEITURA DAS ESTIMATIVAS</span><h3>Como o sistema interpreta os dados</h3><p>Produção é a energia gerada pelo sistema; consumo é a energia utilizada na residência; injeção é o excedente entregue à rede; compensação é o crédito aplicado à fatura. A tarifa, o fator de compensação e o custo de disponibilidade devem ser informados pelo usuário. A estimativa de energia evitada não representa o valor final da fatura nem presume impostos, componentes tarifários ou regras individuais não cadastradas.</p><div className="rule-pills"><span><Check size={13} />Sem tarifa presumida</span><span><Check size={13} />Valores desconhecidos preservados</span><span><Check size={13} />Disponibilidade separada</span></div></div></Panel>
  </div>;
}
