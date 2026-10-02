import type { AuditEntry } from '../types';
import { errorMessage } from '../lib/errors';
import { useEffect, useState } from 'react';
import { Clock3, RefreshCw, ScrollText } from 'lucide-react';
import { getSecurityAudit } from '../api';
import { useAuthenticatedDashboard } from '../DashboardAuth';

function readable(value: string) {
  return value.replaceAll('.', ' ').replaceAll('_', ' ');
}

export default function SecurityAudit() {
  const auth = useAuthenticatedDashboard();
  const [rows, setRows] = useState<AuditEntry[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  async function load() {
    setLoading(true);
    setError('');
    try { setRows((await getSecurityAudit(auth.session.token)).data); }
    catch (requestError) { setError(errorMessage(requestError)); }
    finally { setLoading(false); }
  }
  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return <div className="page-body rbac-ops-page">
    <div className="rbac-page-heading"><div><span>ACCOUNTABILITY</span><h1>Security audit</h1><p>Authentication, account and role changes recorded by the central identity authority.</p></div><button onClick={load} disabled={loading}><RefreshCw size={15} className={loading ? 'spin' : ''} /> Refresh</button></div>
    {error && <div className="rbac-page-error">{error}</div>}
    <section className="rbac-table-card">
      <div><h2><ScrollText size={15} /> Recent activity</h2><span>{rows.length} records</span></div>
      <div className="rbac-table-wrap" tabIndex={0} role="region" aria-label="Security audit table"><table><thead><tr><th>Time</th><th>Actor</th><th>Action</th><th>Target</th><th>Context</th></tr></thead><tbody>{rows.map(row => <tr key={row.id}><td><span className="rbac-audit-time"><Clock3 size={11} />{new Date(row.created_at).toLocaleString()}</span></td><td>{row.actor}</td><td><strong>{readable(row.action)}</strong></td><td>{row.target_id || '—'}</td><td><code>{Object.keys(row.details || {}).length ? JSON.stringify(row.details) : '—'}</code></td></tr>)}</tbody></table></div>
    </section>
  </div>;
}
