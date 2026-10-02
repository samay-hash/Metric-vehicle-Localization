import type { FormEvent } from 'react';
import { errorMessage } from '../lib/errors';
import { useState } from 'react';
import { ArrowRight, Eye, EyeOff, LockKeyhole, ShieldCheck } from 'lucide-react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { loginDashboard } from '../api';
import { useDashboardAuth } from '../DashboardAuth';
import { saveDashboardSession } from '../dashboardSession';

const ROLE_ACCOUNTS = [
  ['Master admin', 'admin@synetra.local'],
  ['Investigator', 'investigator@synetra.local'],
  ['Maintenance', 'maintenance@synetra.local'],
  ['IT operator', 'it@synetra.local'],
];

export default function DashboardLogin() {
  const auth = useDashboardAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const requestedPath: unknown = location.state?.from;
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  if (auth.session && auth.identity) return <Navigate to={auth.identity.landing_path || '/dashboard'} replace />;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      const result = await loginDashboard(email, password);
      const session = saveDashboardSession(result);
      auth.setAuthenticatedSession(session);
      navigate((typeof requestedPath === 'string' && requestedPath) || result.account.landing_path || '/dashboard', { replace: true });
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setBusy(false);
    }
  }

  return <main className="rbac-login">
    <section className="rbac-login-context">
      <span className="rbac-classification">GUJARAT POLICE · AUTHORISED SYSTEM</span>
      <div><span className="rbac-mark"><ShieldCheck size={25} /></span><strong>SYNETRA</strong></div>
      <h1>Operational access follows your duty.</h1>
      <p>Camera feeds, incidents, maintenance, infrastructure and vendor records are separated by role and jurisdiction.</p>
      <dl><div><dt>5</dt><dd>Defined roles</dd></div><div><dt>Scoped</dt><dd>Jurisdiction access</dd></div><div><dt>Audited</dt><dd>Security actions</dd></div></dl>
    </section>
    <section className="rbac-login-panel">
      <form className="rbac-login-card" onSubmit={submit}>
        <span className="rbac-eyebrow">Identity verification</span>
        <h2>Sign in to command operations</h2>
        <p>Your assigned role controls every page, action and API request.</p>
        <label><span>Official email</span><input type="email" value={email} onChange={event => setEmail(event.target.value)} autoComplete="username" required /></label>
        <label><span>Password</span><div className="rbac-password"><LockKeyhole size={16} /><input type={showPassword ? 'text' : 'password'} value={password} onChange={event => setPassword(event.target.value)} autoComplete="current-password" required /><button type="button" onClick={() => setShowPassword(value => !value)} aria-label={showPassword ? 'Hide password' : 'Show password'}>{showPassword ? <EyeOff size={16} /> : <Eye size={16} />}</button></div></label>
        {error && <div className="rbac-error" role="alert">{error}</div>}
        <button className="rbac-submit" disabled={busy}>{busy ? 'Verifying…' : 'Continue'}<ArrowRight size={17} /></button>
        {import.meta.env.DEV && <div className="rbac-demo"><span>Local role accounts</span>{ROLE_ACCOUNTS.map(([label, value]) => <button type="button" key={value} onClick={() => setEmail(value)}><strong>{label}</strong><small>{value}</small></button>)}</div>}
      </form>
    </section>
  </main>;
}

export function Forbidden() {
  const navigate = useNavigate();
  return <main className="rbac-state forbidden"><ShieldCheck size={34} /><span>ACCESS RESTRICTED</span><h1>Your current role cannot open this workspace.</h1><p>Ask a Master Admin to update your role or jurisdiction if your duty requires access.</p><button onClick={() => navigate('/dashboard')}>Return to dashboard</button></main>;
}
