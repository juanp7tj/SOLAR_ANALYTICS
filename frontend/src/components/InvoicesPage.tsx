import { useRef, useState } from 'react';
import { ArrowDownToLine, CalendarClock, Check, FileDown, FileSearch2, FileText, LoaderCircle, Plus, Upload, X } from 'lucide-react';
import { api, formatBrl, formatDate, formatKwh } from '../lib/api';
import type { Invoice, InvoiceDraft } from '../types';
import { Badge, EmptyState, Field, Panel, SectionTitle } from './Primitives';

const blankDraft: InvoiceDraft = {
  billing_period_start: null, billing_period_end: null, issue_date: null, due_date: null, paid_date: null,
  billed_consumption_kwh: null, injected_kwh: null, compensated_kwh: null, accumulated_credits_kwh: null,
  total_amount_brl: null, paid_amount_brl: null, payment_status: 'pending', source_filename: null, notes: null,
};

type PdfResult = InvoiceDraft & { file_name: string; extracted_fields: string[]; warning: string };
const extractionLabels: Record<string, string> = {
  'Consumo faturado': 'consumo faturado', 'Energia injetada': 'energia injetada', 'Energia compensada': 'energia compensada',
  'Créditos acumulados': 'créditos acumulados', 'Valor total': 'valor total da fatura', 'Valor pago': 'valor pago', Vencimento: 'vencimento',
};

function statusTone(status: Invoice['payment_status']): 'green' | 'amber' | 'red' | 'neutral' {
  return status === 'paid' ? 'green' : status === 'overdue' ? 'red' : status === 'partial' ? 'amber' : 'neutral';
}
function statusLabel(status: Invoice['payment_status']): string {
  return status === 'paid' ? 'Pago' : status === 'overdue' ? 'Em atraso' : status === 'partial' ? 'Parcial' : 'Pendente';
}

function EditField({ label, field, draft, setDraft, kind = 'text', suffix }: { label: string; field: keyof InvoiceDraft; draft: InvoiceDraft; setDraft: (draft: InvoiceDraft) => void; kind?: 'text' | 'date' | 'number' | 'select'; suffix?: string }) {
  const value = draft[field];
  const shared = { value: value == null ? '' : String(value), onChange: (event: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const raw = event.target.value;
    const parsed = kind === 'number' ? (raw === '' ? null : Number(raw)) : (raw === '' ? null : raw);
    setDraft({ ...draft, [field]: parsed } as InvoiceDraft);
  } };
  return <Field label={label}>{kind === 'select' ? <select {...shared}>
    <option value="pending">Pendente</option><option value="paid">Pago</option><option value="partial">Parcial</option><option value="overdue">Em atraso</option>
  </select> : <div className="input-suffix-wrap"><input type={kind} min={kind === 'number' ? '0' : undefined} step={kind === 'number' ? '0.01' : undefined} {...shared} />{suffix && <span>{suffix}</span>}</div>}</Field>;
}

function InvoiceModal({ initial, fileFields, onClose, onSaved }: { initial: InvoiceDraft; fileFields?: string[]; onClose: () => void; onSaved: (draft: InvoiceDraft) => Promise<void> }) {
  const [draft, setDraft] = useState<InvoiceDraft>(initial);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const isExtract = Boolean(fileFields);
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    const hasValue = [draft.billing_period_start, draft.billing_period_end, draft.issue_date, draft.due_date, draft.paid_date, draft.billed_consumption_kwh, draft.injected_kwh, draft.compensated_kwh, draft.accumulated_credits_kwh, draft.total_amount_brl, draft.paid_amount_brl].some((value) => value !== null && value !== '');
    if (!hasValue) { setError('Informe pelo menos um dado da fatura antes de salvar.'); return; }
    setSaving(true); setError('');
    try { await onSaved(draft); } catch (reason) { setError(reason instanceof Error ? reason.message : 'Não foi possível salvar.'); } finally { setSaving(false); }
  }
  const fields: Array<{ label: string; key: keyof InvoiceDraft; kind?: 'date' | 'number'; suffix?: string }> = [
    { label: 'Início do período', key: 'billing_period_start', kind: 'date' },
    { label: 'Fim do período', key: 'billing_period_end', kind: 'date' },
    { label: 'Data de emissão', key: 'issue_date', kind: 'date' },
    { label: 'Vencimento', key: 'due_date', kind: 'date' },
    { label: 'Data de pagamento', key: 'paid_date', kind: 'date' },
    { label: 'Consumo faturado', key: 'billed_consumption_kwh', kind: 'number', suffix: 'kWh' },
    { label: 'Energia injetada', key: 'injected_kwh', kind: 'number', suffix: 'kWh' },
    { label: 'Energia compensada', key: 'compensated_kwh', kind: 'number', suffix: 'kWh' },
    { label: 'Créditos acumulados', key: 'accumulated_credits_kwh', kind: 'number', suffix: 'kWh' },
    { label: 'Valor total da fatura', key: 'total_amount_brl', kind: 'number', suffix: 'R$' },
    { label: 'Valor pago', key: 'paid_amount_brl', kind: 'number', suffix: 'R$' },
  ];
  return <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <section className="modal-card invoice-modal" role="dialog" aria-modal="true" aria-labelledby="invoice-dialog-title">
      <div className="modal-heading"><div><span className="eyebrow">NEOENERGIA PERNAMBUCO</span><h2 id="invoice-dialog-title">{isExtract ? 'Revise os dados extraídos' : 'Cadastrar fatura'}</h2><p>{isExtract ? `Arquivo: ${draft.source_filename || 'PDF'}. Confira e corrija antes de gravar.` : 'Preencha os dados disponíveis. Campos desconhecidos podem ficar vazios.'}</p></div><button className="icon-button" onClick={onClose} aria-label="Fechar"><X size={18} /></button></div>
      {fileFields && <div className="extraction-notice"><FileSearch2 size={17} /><div><strong>{fileFields.length} campos identificados no PDF</strong><span>{fileFields.length ? fileFields.map((field) => extractionLabels[field] || field).join(' · ') : 'Nenhum campo reconhecido — preencha manualmente.'}</span></div></div>}
      <form onSubmit={submit}>
        <div className="invoice-fields">{fields.map((item) => <EditField key={item.key} label={item.label} field={item.key} draft={draft} setDraft={setDraft} kind={item.kind || 'text'} suffix={item.suffix} />)}
          <EditField label="Situação de pagamento" field="payment_status" draft={draft} setDraft={setDraft} kind="select" />
          <Field label="Observações"><textarea rows={2} value={draft.notes || ''} onChange={(event) => setDraft({ ...draft, notes: event.target.value || null })} placeholder="Anotações opcionais" /></Field>
        </div>
        {error && <div className="inline-error">{error}</div>}
        <div className="modal-actions"><span className="muted-note">Somente os campos salvos ficarão no histórico.</span><button type="button" className="button button-quiet" onClick={onClose}>Cancelar</button><button type="submit" className="button button-primary" disabled={saving}>{saving ? <LoaderCircle size={15} className="spin" /> : <Check size={15} />}Salvar fatura</button></div>
      </form>
    </section>
  </div>;
}

export function InvoicesPage({ invoices, onRefresh, notify }: { invoices: Invoice[]; onRefresh: () => Promise<void>; notify: (message: string, tone?: 'success' | 'error') => void }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dialog, setDialog] = useState<{ draft: InvoiceDraft; extracted?: string[] } | null>(null);
  const [uploading, setUploading] = useState(false);
  const paidTotal = invoices.filter((invoice) => invoice.payment_status === 'paid' && invoice.paid_amount_brl != null).reduce((sum, invoice) => sum + (invoice.paid_amount_brl || 0), 0);
  const pendingTotal = invoices.filter((invoice) => invoice.payment_status !== 'paid' && invoice.total_amount_brl != null).reduce((sum, invoice) => sum + (invoice.total_amount_brl || 0), 0);

  async function handleFile(file?: File) {
    if (!file) return;
    setUploading(true);
    try {
      const form = new FormData(); form.append('file', file);
      const extracted = await api<PdfResult>('/invoices/extract', { method: 'POST', body: form });
      const { extracted_fields, warning, file_name, ...draft } = extracted;
      setDialog({ draft: { ...blankDraft, ...draft, source_filename: file_name }, extracted: extracted_fields });
      if (!extracted_fields.length) notify('PDF recebido, mas nenhum campo foi reconhecido. Revise e preencha os dados manualmente.', 'error');
    } catch (error) { notify(error instanceof Error ? error.message : 'Falha ao ler o PDF.', 'error'); }
    finally { setUploading(false); if (inputRef.current) inputRef.current.value = ''; }
  }

  async function saveDraft(draft: InvoiceDraft) {
    await api<Invoice>('/invoices', { method: 'POST', body: JSON.stringify(draft) });
    setDialog(null); notify('Fatura salva no histórico.'); await onRefresh();
  }

  async function removeInvoice(invoice: Invoice) {
    if (!window.confirm(`Excluir a fatura de ${invoice.billing_period_end ? formatDate(invoice.billing_period_end) : 'período não informado'}?`)) return;
    try { await api<void>(`/invoices/${invoice.id}`, { method: 'DELETE' }); notify('Fatura removida.'); await onRefresh(); }
    catch (error) { notify(error instanceof Error ? error.message : 'Não foi possível remover.', 'error'); }
  }

  const invoiceSorted = [...invoices].sort((a, b) => (b.billing_period_end || b.created_at).localeCompare(a.billing_period_end || a.created_at));
  return <div className="page-content module-page">
    <SectionTitle eyebrow="NEOENERGIA PERNAMBUCO" title="Faturas & pagamentos" detail="Revise os dados da distribuidora e compare a conta com a energia solar medida." action={<><input ref={inputRef} className="visually-hidden" type="file" accept="application/pdf,.pdf" onChange={(event) => handleFile(event.target.files?.[0])} /><button className="button button-quiet" onClick={() => setDialog({ draft: { ...blankDraft } })}><Plus size={16} />Cadastrar manualmente</button><button className="button button-primary" disabled={uploading} onClick={() => inputRef.current?.click()}>{uploading ? <LoaderCircle size={15} className="spin" /> : <Upload size={16} />}Importar PDF</button></>} />
    <div className="invoice-summary-grid"><Panel className="summary-card"><span className="summary-icon summary-emerald"><Check size={17} /></span><div><span>Pagamentos registrados</span><strong>{formatBrl(paidTotal)}</strong><small>{invoices.filter((invoice) => invoice.payment_status === 'paid').length} faturas marcadas como pagas</small></div></Panel><Panel className="summary-card"><span className="summary-icon summary-amber"><CalendarClock size={17} /></span><div><span>Em aberto / parcial</span><strong>{formatBrl(pendingTotal)}</strong><small>Valor total das faturas não marcadas como pagas</small></div></Panel><Panel className="summary-card"><span className="summary-icon summary-blue"><FileText size={17} /></span><div><span>Faturas no histórico</span><strong>{invoices.length.toString().padStart(2, '0')}</strong><small>Inclui registros reais e demonstração identificada</small></div></Panel></div>
    <Panel className="invoice-table-panel"><div className="table-head"><div><h3>Histórico de faturas</h3><p>Os valores permanecem locais e editáveis antes de salvar.</p></div><button className="button button-quiet button-small" onClick={() => window.location.assign('/api/export.csv?kind=invoices')}><FileDown size={15} />Exportar CSV</button></div>
      {invoiceSorted.length ? <div className="table-scroll"><table className="data-table"><thead><tr><th>Período</th><th>Consumo faturado</th><th>Injetada</th><th>Compensada</th><th>Créditos</th><th>Vencimento</th><th>Valor total</th><th>Valor pago</th><th>Situação</th><th></th></tr></thead><tbody>{invoiceSorted.map((invoice) => <tr key={invoice.id}>
        <td><strong>{invoice.billing_period_end ? formatDate(invoice.billing_period_end, { month: 'short', year: 'numeric' }) : 'Período —'}</strong>{invoice.is_demo && <span className="row-demo">DEMO</span>}</td>
        <td>{formatKwh(invoice.billed_consumption_kwh)}</td><td>{formatKwh(invoice.injected_kwh)}</td><td>{formatKwh(invoice.compensated_kwh)}</td><td>{formatKwh(invoice.accumulated_credits_kwh)}</td><td>{formatDate(invoice.due_date)}</td><td className="table-money">{formatBrl(invoice.total_amount_brl)}</td><td>{formatBrl(invoice.paid_amount_brl)}</td><td><Badge tone={statusTone(invoice.payment_status)} dot>{statusLabel(invoice.payment_status)}</Badge></td><td><button className="icon-button icon-button-danger" aria-label="Excluir fatura" title="Excluir fatura" onClick={() => removeInvoice(invoice)}><X size={15} /></button></td>
      </tr>)}</tbody></table></div> : <EmptyState icon={<FileText size={20} />} title="Nenhuma fatura cadastrada" detail="Importe um PDF ou registre os valores manualmente. Campos não encontrados no documento ficam em branco." />}
      <div className="invoice-privacy-note"><FileSearch2 size={15} /><span>A extração é local e serve como ponto de partida: sempre confira os valores na fatura original antes de salvar.</span><ArrowDownToLine size={15} className="privacy-arrow" /></div>
    </Panel>
    {dialog && <InvoiceModal initial={dialog.draft} fileFields={dialog.extracted} onClose={() => setDialog(null)} onSaved={saveDraft} />}
  </div>;
}
