import type { FormEvent } from 'react';
import type { AccessUser, SystemRole, ScopeType } from '../types';
import { errorMessage } from '../lib/errors';
import { useEffect, useState } from 'react';
import { Plus, RefreshCw, Shield, UserRound } from 'lucide-react';
import { createAccessUser, getAccessUsers } from '../api';
import { useAuthenticatedDashboard } from '../DashboardAuth';

const ROLES: SystemRole[] = ['master_admin', 'investigator', 'maintenance', 'it_operator'];
const SCOPES: ScopeType[] = ['global', 'department', 'vendor', 'state', 'district', 'commissionerate', 'zone', 'police_station'];

export default function AccessManagement() {
  const auth = useAuthenticatedDashboard();
  const [users, setUsers] = useState<AccessUser[]>([]);
  const [form, setForm] = useState<{ email: string; display_name: string; password: string; role: SystemRole; scope_type: ScopeType; scope_id: string }>({ email: '', display_name: '', password: '', role: 'investigator', scope_type: 'global', scope_id: '' });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  async function load() {
    try { setUsers((await getAccessUsers(auth.session.token)).data); } catch (requestError) { setError(errorMessage(requestError)); }
  }
  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError('');
    try {
      await createAccessUser(auth.session.token, {
        email: form.email, display_name: form.display_name, password: form.password,
        assignments: [{ role: form.role, scope_type: form.scope_type,
          scope_id: form.scope_type === 'global' ? null : form.scope_id }],
      });
      setForm({ email: '', display_name: '', password: '', role: 'investigator', scope_type: 'global', scope_id: '' });
      await load();
    } catch (requestError) { setError(errorMessage(requestError)); }
    finally { setBusy(false); }
  }
  return <div className="page-body rbac-ops-page">
    <div className="rbac-page-heading"><div><span>MASTER ADMIN</span><h1>Access management</h1><p>Create dashboard identities and review their active role and jurisdiction assignments.</p></div><button onClick={load}><RefreshCw size={15} /> Refresh</button></div>
    {error && <div className="rbac-page-error">{error}</div>}
    <section className="rbac-access-layout">
      <form className="rbac-access-form" onSubmit={submit}><div><Plus size={18} /><h2>Add dashboard user</h2></div><label><span>Display name</span><input value={form.display_name} onChange={event => setForm(current => ({ ...current, display_name: event.target.value }))} required /></label><label><span>Official email</span><input type="email" value={form.email} onChange={event => setForm(current => ({ ...current, email: event.target.value }))} required /></label><label><span>Temporary password</span><input type="password" minLength={12} value={form.password} onChange={event => setForm(current => ({ ...current, password: event.target.value }))} required /></label><label><span>Role</span><select value={form.role} onChange={event => setForm(current => ({ ...current, role: event.target.value as SystemRole }))}>{ROLES.map(role => <option key={role} value={role}>{role.replaceAll('_', ' ')}</option>)}</select></label><label><span>Jurisdiction type</span><select value={form.scope_type} onChange={event => setForm(current => ({ ...current, scope_type: event.target.value as ScopeType, scope_id: '' }))}>{SCOPES.map(scope => <option key={scope} value={scope}>{scope.replaceAll('_', ' ')}</option>)}</select></label>{form.scope_type !== 'global' && <label><span>Jurisdiction identifier</span><input value={form.scope_id} onChange={event => setForm(current => ({ ...current, scope_id: event.target.value }))} placeholder={form.scope_type === 'department' ? 'e.g. Ahmedabad City' : `${form.scope_type} ID`} required /></label>}<button disabled={busy}>{busy ? 'Creating…' : 'Create user'}</button></form>
      <section className="rbac-table-card"><div><h2>Dashboard users</h2><span>{users.length} identities</span></div><div className="rbac-table-wrap" tabIndex={0} role="region" aria-label="Dashboard users table"><table><thead><tr><th>User</th><th>Role</th><th>Scope</th><th>Status</th></tr></thead><tbody>{users.map(user => <tr key={user.id}><td><strong>{user.display_name}</strong><small>{user.email}</small></td><td>{user.roles.map(role => <span className="rbac-role" key={role}><Shield size={11} />{role.replaceAll('_', ' ')}</span>)}</td><td>{user.assignments.map(item => <small key={item.id}>{item.scope_type}{item.scope_id ? ` · ${item.scope_id}` : ''}</small>)}</td><td><span className={`rbac-status ${user.active ? 'healthy' : 'disabled'}`}><UserRound size={11} />{user.active ? 'Active' : 'Disabled'}</span></td></tr>)}</tbody></table></div></section>
    </section>
  </div>;
}
