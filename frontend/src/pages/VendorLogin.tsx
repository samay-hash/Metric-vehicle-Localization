import type { FormEvent } from 'react';
import { errorMessage, errorStatus } from '../lib/errors';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, Camera, Database, Eye, EyeOff, LockKeyhole, MapPinned, RadioTower, ShieldCheck } from 'lucide-react';
import { loginVendor } from '../api';
import { readVendorSession, saveVendorSession } from '../vendorSession';

const DEMO_ACCOUNTS = [
  { email: 'sentinel.vendor@synetra.local', label: 'Sentinel / 30 feeds' },
  { email: 'vendor2@synetra.local', label: 'Pioneer Monitoring' },
  { email: 'vendor3@synetra.local', label: 'Harbor Secure' },
  { email: 'vendor4@synetra.local', label: 'Sterling Systems' },
  { email: 'vendor5@synetra.local', label: 'Sterling Vision' },
];

const STEPS = [
  { icon: ShieldCheck, index: '01', title: 'Verify vendor', copy: 'Use an account approved by the registry administrator.' },
  { icon: RadioTower, index: '02', title: 'Connect source', copy: 'Register a catalogue or manual camera collection.' },
  { icon: MapPinned, index: '03', title: 'Complete metadata', copy: 'Add location, ownership, type and GIS coordinates.' },
];

export default function VendorLogin() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('sentinel.vendor@synetra.local');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (readVendorSession()) navigate('/vendor/onboarding', { replace: true });
  }, [navigate]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError('');
    try {
      const result = await loginVendor(email, password);
      saveVendorSession(result);
      navigate('/vendor/onboarding', { replace: true });
    } catch (requestError) {
      setError(errorStatus(requestError) === 401 ? 'The email or password is incorrect.' : errorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="vendor-portal vendor-login-shell">
      <section className="vendor-login-intro" aria-labelledby="vendor-login-title">
        <button className="vendor-wordmark" type="button" onClick={() => navigate('/dashboard')} aria-label="Return to Synetra dashboard">
          <span className="vendor-mark"><Camera size={18} /></span>
          <span><strong>SYNETRA</strong><small>CCTV REGISTRY</small></span>
        </button>

        <div className="vendor-intro-copy">
          <span className="vendor-kicker"><span /> Vendor intake workspace</span>
          <h1 id="vendor-login-title">One catalogue.<br />Every camera accounted for.</h1>
          <p>Register camera assets once, complete their GIS records, and give authorised departments one standard API to work with.</p>
        </div>

        <ol className="vendor-route" aria-label="Registry onboarding steps">
          {STEPS.map(({ icon: Icon, index, title, copy }) => (
            <li key={index}>
              <span className="vendor-route-node"><Icon size={16} /></span>
              <span className="vendor-route-index">{index}</span>
              <span><strong>{title}</strong><small>{copy}</small></span>
            </li>
          ))}
        </ol>

        <div className="vendor-catalogue-strip">
          <span><Database size={14} /> Registry API / v1</span>
          <span className="vendor-live-dot">Online</span>
        </div>
      </section>

      <section className="vendor-login-panel" aria-label="Vendor sign in">
        <div className="vendor-login-card">
          <div className="vendor-card-heading">
            <span className="vendor-eyebrow">Authorised access</span>
            <h2>Sign in to your registry</h2>
            <p>Only whitelisted vendor accounts can onboard and maintain camera records.</p>
          </div>

          <form onSubmit={handleSubmit} className="vendor-login-form">
            <label>
              <span>Work email</span>
              <input type="email" value={email} onChange={event => setEmail(event.target.value)} autoComplete="username" required />
            </label>
            <label>
              <span>Password</span>
              <div className="vendor-password-field">
                <LockKeyhole size={16} aria-hidden="true" />
                <input type={showPassword ? 'text' : 'password'} value={password} onChange={event => setPassword(event.target.value)} autoComplete="current-password" minLength={8} required />
                <button type="button" onClick={() => setShowPassword(value => !value)} aria-label={showPassword ? 'Hide password' : 'Show password'}>
                  {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
                </button>
              </div>
            </label>
            {error && <div className="vendor-form-error" role="alert">{error}</div>}
            <button className="vendor-primary-button" type="submit" disabled={loading}>
              <span>{loading ? 'Checking credentials…' : 'Open vendor workspace'}</span>
              <ArrowRight size={17} />
            </button>
          </form>

          {import.meta.env.DEV && (
            <div className="vendor-demo-accounts">
              <div><span>Demo accounts</span><small>Use the shared password from your registry administrator.</small></div>
              <div className="vendor-account-list">
                {DEMO_ACCOUNTS.map(account => (
                  <button type="button" key={account.email} onClick={() => setEmail(account.email)} className={email === account.email ? 'selected' : ''}>
                    <span>{account.label}</span><small>{account.email}</small>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
        <p className="vendor-security-note"><ShieldCheck size={14} /> Session credentials stay in this browser tab and expire automatically.</p>
      </section>
    </main>
  );
}
