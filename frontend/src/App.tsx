import { useCallback, useEffect, useRef, useState } from 'react';
import { Activity, AlertTriangle, ArrowUpRight, Check, ChevronRight, Command, FileText, Gauge, Leaf, LoaderCircle, LogOut, RefreshCw, Settings2, SunMedium } from 'lucide-react';
import { api, ApiError } from './lib/api';
import type { AuthStatus, DashboardData, DemoStatus, EnergyRecord, GoodWeStatus, Invoice, Period, Section, Tariffs } from './types';
import { Dashboard, GoodWePage, InvoicesPage, ReadingsPage, SettingsPage } from './components';
import { LoginPage } from './components/LoginPage';
import { Badge, Panel } from './components/Primitives';

const navigation: Array<{ id: Section; label: string; icon: typeof SunMedium; group: 'monitoramento' | 'conta' }> = [
  { id: 'dashboard', label: 'Visão geral', icon: Gauge, group: 'monitoramento' },
  { id: 'readings', label: 'Leituras de energia', icon: Activity, group: 'monitoramento' },
  { id: 'invoices', label: 'Faturas Neoenergia', icon: FileText, group: 'conta' },
  { id: 'goodwe', label: 'GoodWe SEMS+', icon: SunMedium, group: 'conta' },
  { id: 'settings', label: 'Configurações', icon: Settings2, group: 'conta' },
];
const emptyTariffs: Tariffs = { energy_rate_brl_kwh: null, availability_cost_brl: null, compensation_factor_percent: null };
const titles: Record<Section, string> = { dashboard: 'Visão geral', readings: 'Leituras de energia', invoices: 'Faturas Neoenergia', goodwe: 'GoodWe SEMS+', settings: 'Configurações' };

function LogoMark() {
  return <div className="brand-lockup"><span className="brand-mark"><SunMedium size={21} strokeWidth={1.65} /><i /></span><span className="brand-name">SOLAR<span>ANALYTICS</span></span></div>;
}

function Sidebar({ active, setActive, demo }: { active: Section; setActive: (id: Section) => void; demo: DemoStatus | null }) {
  return <aside className="sidebar">
    <div className="sidebar-top"><LogoMark /><div className="sidebar-tagline">INTELIGÊNCIA ENERGÉTICA</div></div>
    <div className="nav-section-label">MONITORAMENTO</div>
    <nav className="main-nav" aria-label="Navegação principal">{navigation.filter((item) => item.group === 'monitoramento').map((item) => { const Icon = item.icon; return <button key={item.id} className={`nav-item ${active === item.id ? 'nav-active' : ''}`} onClick={() => setActive(item.id)}><Icon size={17} strokeWidth={1.7} /><span>{item.label}</span>{active === item.id && <ChevronRight size={14} className="nav-chevron" />}</button>; })}</nav>
    <div className="nav-section-label nav-gap">GESTÃO & INTEGRAÇÕES</div>
    <nav className="main-nav" aria-label="Gestão e integrações">{navigation.filter((item) => item.group === 'conta').map((item) => { const Icon = item.icon; return <button key={item.id} className={`nav-item ${active === item.id ? 'nav-active' : ''}`} onClick={() => setActive(item.id)}><Icon size={17} strokeWidth={1.7} /><span>{item.label}</span>{item.id === 'goodwe' && <span className="nav-indicator" />}{active === item.id && <ChevronRight size={14} className="nav-chevron" />}</button>; })}</nav>
    <div className="sidebar-spacer" />
    <div className="sidebar-system"><div className="system-status-dot" /><span>Banco SQLite</span><span className="system-separator">·</span><span>{demo?.enabled ? 'Modo demonstração' : 'Dados registrados'}</span></div>
    <div className="sidebar-footer"><div className="mini-plant"><span className="plant-glow"><Leaf size={16} /></span><div><strong>Residencial</strong><small>Central inteligente</small></div><ArrowUpRight size={14} /></div><p>Inteligência que transforma energia em economia.</p></div>
  </aside>;
}

function Toast({ message, tone, onClose }: { message: string; tone: 'success' | 'error'; onClose: () => void }) {
  return <div className={`toast toast-${tone}`} role="status"><span>{tone === 'success' ? <Check size={16} /> : <AlertTriangle size={16} />}</span><strong>{message}</strong><button onClick={onClose} aria-label="Fechar mensagem">×</button></div>;
}

function DataUnavailable({ message, retry }: { message: string; retry: () => void }) {
  return <div className="loading-wrap"><Panel className="connection-card"><div className="connection-icon"><AlertTriangle size={20} /></div><span className="eyebrow">SERVIÇO INDISPONÍVEL</span><h2>Não foi possível carregar os dados</h2><p>{message}</p><button className="button button-primary" onClick={retry}><RefreshCw size={15} />Tentar novamente</button><small>Confira se o servidor FastAPI está ativo e tente de novo.</small></Panel></div>;
}

export default function App() {
  const [active, setActive] = useState<Section>('dashboard');
  const [period, setPeriod] = useState<Period>('month');
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [readings, setReadings] = useState<EnergyRecord[]>([]);
  const [tariffs, setTariffs] = useState<Tariffs>(emptyTariffs);
  const [goodwe, setGoodwe] = useState<GoodWeStatus>({ app_id: null, plant_id: null, secret_configured: false, status: 'Aguardando credenciais da API GoodWe' });
  const [demo, setDemo] = useState<DemoStatus | null>(null);
  const [authStatus, setAuthStatus] = useState<AuthStatus | null>(null);
  const [authReady, setAuthReady] = useState(false);
  const [authProblem, setAuthProblem] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [toast, setToast] = useState<{ message: string; tone: 'success' | 'error' } | null>(null);
  const toastTimer = useRef<number | null>(null);

  const notify = useCallback((message: string, tone: 'success' | 'error' = 'success') => {
    setToast({ message, tone });
    if (toastTimer.current) window.clearTimeout(toastTimer.current);
    toastTimer.current = window.setTimeout(() => setToast(null), 4800);
  }, []);

  const verifyAuth = useCallback(async () => {
    setAuthProblem('');
    setAuthReady(false);
    try {
      const status = await api<AuthStatus>('/auth/status');
      setAuthStatus(status);
    } catch (reason) {
      setAuthProblem(reason instanceof Error ? reason.message : 'Não foi possível verificar a sessão.');
    } finally {
      setAuthReady(true);
      setLoading(false);
    }
  }, []);

  const reload = useCallback(async () => {
    try {
      setError('');
      const [nextDashboard, nextInvoices, nextReadings, nextTariffs, nextGoodwe, nextDemo] = await Promise.all([
        api<DashboardData>(`/dashboard?period=${period}`),
        api<Invoice[]>('/invoices'),
        api<EnergyRecord[]>('/readings'),
        api<Tariffs>('/settings/tariffs'),
        api<GoodWeStatus>('/goodwe/status'),
        api<DemoStatus>('/demo/status'),
      ]);
      setDashboard(nextDashboard); setInvoices(nextInvoices); setReadings(nextReadings); setTariffs(nextTariffs); setGoodwe(nextGoodwe); setDemo(nextDemo);
    } catch (reason) {
      if (reason instanceof ApiError && reason.status === 401) {
        setAuthStatus((current) => current ? { ...current, authenticated: false } : current);
        setDashboard(null);
        setInvoices([]);
        setReadings([]);
        setDemo(null);
        setError('Sua sessão expirou. Entre novamente.');
      } else {
        setError(reason instanceof Error ? reason.message : 'O servidor não respondeu.');
      }
    } finally { setLoading(false); }
  }, [period]);

  useEffect(() => { void verifyAuth(); }, [verifyAuth]);
  useEffect(() => {
    if (authReady && authStatus && (!authStatus.auth_required || authStatus.authenticated)) void reload();
  }, [authReady, authStatus, reload]);
  useEffect(() => () => { if (toastTimer.current) window.clearTimeout(toastTimer.current); }, []);

  async function submitLogin(username: string, password: string) {
    const status = await api<AuthStatus>('/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) });
    setError('');
    setAuthProblem('');
    setAuthStatus(status);
    setLoading(true);
  }

  async function logout() {
    try {
      await api<{ authenticated: boolean }>('/auth/logout', { method: 'POST' });
      setAuthStatus((current) => current ? { ...current, authenticated: false } : current);
      setDashboard(null); setInvoices([]); setReadings([]); setDemo(null); setLoading(false);
      notify('Sessão encerrada.');
    } catch (reason) {
      notify(reason instanceof Error ? reason.message : 'Não foi possível encerrar a sessão.', 'error');
    }
  }

  async function removeDemo() {
    if (!window.confirm('Remover todos os registros identificados como demonstração? Os dados reais serão mantidos. Esta ação não pode ser desfeita.')) return;
    try {
      const result = await api<{ removed_records: number; removed_invoices: number }>('/demo', { method: 'DELETE' });
      notify(`${result.removed_records} medições e ${result.removed_invoices} faturas fictícias removidas. Dados reais preservados.`);
      await reload();
    } catch (reason) { notify(reason instanceof Error ? reason.message : 'Não foi possível remover os dados de demonstração.', 'error'); }
  }

  if (!authReady) return <div className="loading-wrap"><div className="loading-orb"><LoaderCircle size={21} className="spin" /></div><span>Verificando o acesso…</span></div>;
  if (authProblem) return <DataUnavailable message={authProblem} retry={() => void verifyAuth()} />;
  if (authStatus?.auth_required && !authStatus.authenticated) return <LoginPage onLogin={submitLogin} volatileStorage={authStatus.volatile_storage} />;

  const sectionComponent = dashboard ? <>
    {active === 'dashboard' && <Dashboard data={dashboard} period={period} onPeriodChange={setPeriod} onNavigate={setActive} />}
    {active === 'invoices' && <InvoicesPage invoices={invoices} onRefresh={reload} notify={notify} />}
    {active === 'readings' && <ReadingsPage readings={readings} onRefresh={reload} notify={notify} />}
    {active === 'goodwe' && <GoodWePage status={goodwe} onRefresh={reload} notify={notify} />}
    {active === 'settings' && <SettingsPage tariffs={tariffs} onRefresh={reload} notify={notify} />}
  </> : null;
  const protectedSession = authStatus?.auth_required === true;

  return <div className="app-shell">
    <Sidebar active={active} setActive={setActive} demo={demo} />
    <main className="app-main">
      <header className="topbar"><div className="topbar-left"><span className="topbar-kicker">SOLAR ANALYTICS</span><ChevronRight size={14} /><span>{titles[active]}</span></div><div className="topbar-right"><span className="local-status"><i />{protectedSession ? 'Acesso protegido' : 'Ambiente local'}</span><button className="icon-button refresh-button" title="Atualizar os dados" aria-label="Atualizar os dados" onClick={() => void reload()}><RefreshCw size={16} /></button>{protectedSession && <button className="icon-button" title="Encerrar sessão" aria-label="Encerrar sessão" onClick={() => void logout()}><LogOut size={16} /></button>}<div className="topbar-user"><span className="user-avatar"><SunMedium size={15} /></span><span><strong>{protectedSession ? 'Administrador' : 'Instalação residencial'}</strong><small>PE · Brasil</small></span></div></div></header>
      <div className="main-scroll">
        {authStatus?.volatile_storage && <div className="free-storage-banner" role="alert"><AlertTriangle size={17} /><div><strong>Render Free · armazenamento temporário</strong><span>Use apenas dados fictícios. Leituras, faturas e ajustes podem desaparecer em reinicializações, suspensão ou novos deploys. Baixe backups para seu computador.</span></div></div>}
        {demo?.enabled && <div className="demo-banner"><div className="demo-banner-symbol"><Command size={15} /></div><div><strong>Modo demonstração</strong><span>Dados fictícios para ilustrar o painel. Não representam sua instalação ou fatura real.</span></div><Badge tone="amber">{demo.demo_records + demo.demo_invoices} amostras</Badge><button className="button button-danger-quiet button-small" onClick={removeDemo}>Remover dados fictícios</button></div>}
        {loading && !dashboard ? <div className="loading-wrap"><div className="loading-orb"><LoaderCircle size={21} className="spin" /></div><span>Conectando ao banco SQLite…</span></div> : error && !dashboard ? <DataUnavailable message={error} retry={() => void reload()} /> : sectionComponent}
        {error && dashboard && <div className="soft-error">{error}<button onClick={() => void reload()}>Recarregar</button></div>}
      </div>
      <footer className="global-footer"><span><span className="footer-pulse" />{protectedSession ? 'Sessão administrativa protegida' : 'Operação local · Nenhuma hospedagem externa'}</span><span>© SOLAR ANALYTICS <i>•</i> v1.1.0</span></footer>
    </main>
    {toast && <Toast message={toast.message} tone={toast.tone} onClose={() => setToast(null)} />}
  </div>;
}
