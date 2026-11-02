import { FormEvent, useState } from 'react';
import { AlertTriangle, ArrowRight, LoaderCircle, LockKeyhole, ShieldCheck, SunMedium } from 'lucide-react';

export function LoginPage({ onLogin, volatileStorage }: { onLogin: (username: string, password: string) => Promise<void>; volatileStorage: boolean }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    setPending(true);
    try {
      await onLogin(username, password);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Não foi possível autenticar.');
    } finally {
      setPending(false);
    }
  }

  return <main className="login-page">
    <section className="login-shell" aria-labelledby="login-title">
      <div className="login-brand">
        <span className="login-mark"><SunMedium size={23} strokeWidth={1.6} /><i /></span>
        <span className="brand-name">SOLAR<span>ANALYTICS</span></span>
      </div>
      <div className="login-card panel">
        <div className="login-lock-icon"><LockKeyhole size={19} /></div>
        <span className="eyebrow">ACESSO ADMINISTRATIVO</span>
        <h1 id="login-title">Sua energia, sob controle.</h1>
        <p className="login-intro">Entre com a conta administrativa para consultar a instalação, leituras e faturas.</p>
        {volatileStorage && <div className="free-storage-banner login-storage-warning"><AlertTriangle size={17} /><div><strong>Hospedagem gratuita · armazenamento temporário</strong><span>Use apenas dados fictícios. Leituras e faturas podem desaparecer quando o serviço reiniciar ou entrar em suspensão.</span></div></div>}
        <form className="login-form" onSubmit={(event) => void submit(event)}>
          <label className="login-field"><span>Usuário</span><input name="username" type="text" value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" maxLength={128} required autoFocus /></label>
          <label className="login-field"><span>Senha</span><input name="password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" maxLength={1024} required /></label>
          {error && <div className="inline-error" role="alert">{error}</div>}
          <button className="button button-primary login-submit" type="submit" disabled={pending}>
            {pending ? <LoaderCircle size={16} className="spin" /> : <><span>Entrar no painel</span><ArrowRight size={15} /></>}
          </button>
        </form>
        <div className="login-security-note"><ShieldCheck size={15} /><span>Conta única, sem cadastro público. A sessão expira após 12 horas.</span></div>
      </div>
      <p className="login-tagline">Inteligência que transforma energia em economia.</p>
    </section>
  </main>;
}
