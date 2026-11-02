import { useEffect, useState } from 'react';
import { Activity, Check, CircleAlert, KeyRound, LockKeyhole, RefreshCw, ShieldCheck, SunMedium } from 'lucide-react';
import { api } from '../lib/api';
import type { GoodWeStatus } from '../types';
import { Badge, Field, Panel, SectionTitle } from './Primitives';

export function GoodWePage({ status, onRefresh, notify }: { status: GoodWeStatus; onRefresh: () => Promise<void>; notify: (message: string, tone?: 'success' | 'error') => void }) {
  const [appId, setAppId] = useState(status.app_id || '');
  const [appSecret, setAppSecret] = useState('');
  const [plantId, setPlantId] = useState(status.plant_id || '');
  const [busy, setBusy] = useState(false);
  useEffect(() => { setAppId(status.app_id || ''); setPlantId(status.plant_id || ''); }, [status.app_id, status.plant_id]);

  async function save(event: React.FormEvent) {
    event.preventDefault();
    if (!appId.trim() || !plantId.trim()) { notify('Informe AppID e identificação da usina.', 'error'); return; }
    setBusy(true);
    try {
      const next = await api<GoodWeStatus>('/goodwe/credentials', { method: 'PUT', body: JSON.stringify({ app_id: appId.trim(), app_secret: appSecret || null, plant_id: plantId.trim() }) });
      setAppSecret(''); await onRefresh();
      notify(next.secret_configured ? 'Identificadores salvos; o AppSecret está guardado pelo sistema operacional. Nenhuma conexão foi iniciada.' : 'Identificadores salvos. Configure o AppSecret no cofre local para completar as credenciais.', next.secret_configured ? 'success' : 'error');
    } catch (error) { notify(error instanceof Error ? error.message : 'Não foi possível salvar as credenciais.', 'error'); }
    finally { setBusy(false); }
  }

  async function clear() {
    if (!window.confirm('Remover as credenciais GoodWe guardadas neste computador?')) return;
    setBusy(true);
    try { await api('/goodwe/credentials', { method: 'DELETE' }); setAppId(''); setPlantId(''); setAppSecret(''); await onRefresh(); notify('Credenciais locais removidas.'); }
    catch (error) { notify(error instanceof Error ? error.message : 'Não foi possível limpar as credenciais.', 'error'); }
    finally { setBusy(false); }
  }

  return <div className="page-content module-page goodwe-page">
    <SectionTitle eyebrow="INTEGRAÇÃO PREPARADA · API NÃO CONECTADA" title="GoodWe SEMS+" detail="Estrutura isolada pronta para integração oficial. Esta versão não faz autenticação nem consulta a API." action={<Badge tone="amber" dot>{status.status}</Badge>} />
    <Panel className="goodwe-status-card"><div className="goodwe-orb"><SunMedium size={25} /></div><div className="goodwe-status-copy"><span className="eyebrow">STATUS DE INTEGRAÇÃO</span><h2>{status.status}</h2><p>Não há conexão ativa com o SEMS+. Nenhuma geração, consumo ou potência está sendo recebida da GoodWe.</p></div><Badge tone="amber" dot>Não conectada</Badge></Panel>
    <div className="goodwe-grid"><Panel className="settings-panel"><div className="panel-heading"><div><span className="eyebrow">CONFIGURAÇÃO LOCAL</span><h3>Credenciais & usina</h3></div><span className="panel-heading-icon"><KeyRound size={17} /></span></div><p className="settings-intro">Os identificadores são guardados no banco local. O AppSecret é enviado apenas ao backend local e guardado no cofre de credenciais do sistema operacional; nunca é devolvido à interface.</p>
      <form className="goodwe-form" onSubmit={save}><Field label="AppID"><input value={appId} onChange={(event) => setAppId(event.target.value)} placeholder={status.app_id ? 'AppID já configurado — deixe em branco para manter' : 'AppID da aplicação GoodWe'} autoComplete="off" /></Field>
        <Field label="AppSecret" hint={status.secret_configured ? 'Já existe um segredo no cofre. Deixe vazio para manter o valor atual.' : 'Será encaminhado somente à API local e armazenado no cofre do sistema.'}><input type="password" value={appSecret} onChange={(event) => setAppSecret(event.target.value)} placeholder={status.secret_configured ? '••••••••••••••••' : 'AppSecret'} autoComplete="new-password" /></Field>
        <Field label="Identificação da usina"><input value={plantId} onChange={(event) => setPlantId(event.target.value)} placeholder="Identificador da usina/plant" autoComplete="off" /></Field>
        <div className="credential-actions"><button className="button button-primary" disabled={busy}>{busy ? 'Salvando…' : <><LockKeyhole size={15} />Salvar credenciais localmente</>}</button>{(status.app_id || status.plant_id || status.secret_configured) && <button type="button" className="button button-danger-quiet" disabled={busy} onClick={clear}>Remover</button>}</div>
      </form>
      <div className="secure-note"><ShieldCheck size={15} /><span>AppSecret não é salvo no SQLite, não aparece em logs e não pode ser lido de volta pela interface.</span></div>
    </Panel>

    <div className="goodwe-side"><Panel className="goodwe-capability"><div className="panel-heading"><div><span className="eyebrow">ARQUITETURA PREPARADA</span><h3>Escopo futuro</h3></div><span className="panel-heading-icon"><Activity size={17} /></span></div><div className="capability-list"><div><SunMedium size={16} /><span>Consulta de geração</span><Badge tone="neutral">Aguardando API</Badge></div><div><Activity size={16} /><span>Consumo & potência</span><Badge tone="neutral">Aguardando API</Badge></div><div><RefreshCw size={16} /><span>Autenticação & sincronização</span><Badge tone="neutral">Desativada</Badge></div></div><div className="api-honesty"><CircleAlert size={15} /><span>Não existe sincronização simulada. A rota de sincronização responde indisponível até a integração oficial ser implementada e validada.</span></div></Panel>
      <Panel className="status-panel"><span className="status-check"><Check size={16} /></span><div><strong>{status.secret_configured ? 'Segredo protegido no cofre local' : 'Nenhum AppSecret configurado'}</strong><p>{status.secret_configured ? 'A presença do segredo é exibida sem revelar seu conteúdo.' : 'O estado permanece aguardando credenciais, sem tentativa de conexão.'}</p></div></Panel></div>
    </div>
  </div>;
}
