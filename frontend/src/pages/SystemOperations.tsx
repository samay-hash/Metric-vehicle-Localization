import type { SystemStats } from '../types';
import { errorMessage } from '../lib/errors';
import { useEffect, useState } from 'react';
import { Activity, AlertTriangle, Camera, CheckCircle2, RefreshCw, Server, Wrench } from 'lucide-react';
import { getSystemStats } from '../api';
import { useAuthenticatedDashboard } from '../DashboardAuth';
import { useDashboardFleet } from '../DashboardFleet';

function statusLabel(status: string | null | undefined) {
  return (status || 'unknown').replaceAll('_', ' ');
}

export default function SystemOperations() {
  const auth = useAuthenticatedDashboard();
  const { inventory, fleet, inventoryError, healthError, loading, refresh } = useDashboardFleet();
  const [system, setSystem] = useState<SystemStats | null>(null);
  const [systemError, setSystemError] = useState('');
  const [systemLoading, setSystemLoading] = useState(true);
  const [revision, setRevision] = useState(0);
  const canReadSystem = auth.has('system.read');

  useEffect(() => {
    if (!canReadSystem) return;
    let active = true;
    setSystemLoading(true);
    getSystemStats().then(response => {
      if (active) { setSystem(response.data); setSystemError(''); }
    }).catch(error => {
      if (active) { setSystem(null); setSystemError(errorMessage(error)); }
    }).finally(() => { if (active) setSystemLoading(false); });
    return () => { active = false; };
  }, [canReadSystem, revision]);

  const counts = fleet?.counts;
  const needsAttention = counts ? Object.entries(counts).reduce((total, [status, count]) =>
    ['healthy', 'unmonitored', 'disabled'].includes(status) ? total : total + count, 0) : null;
  const busy = loading || (canReadSystem && systemLoading);

  return <div className="page-body rbac-ops-page">
    <div className="rbac-page-heading"><div><span>TECHNICAL OPERATIONS</span><h1>System control</h1><p>Camera health, maintenance and analytics status across your assigned scope.</p></div><button onClick={() => { refresh(); setRevision(value => value + 1); }} disabled={busy}><RefreshCw size={15} className={busy ? 'spin' : ''} /> Refresh</button></div>
    {healthError && <div className="rbac-page-error" role="alert"><AlertTriangle size={16} />Camera health unavailable: {healthError}</div>}
    <section className="rbac-metric-grid">
      <article><Camera size={18} /><span>Registered cameras</span><strong>{inventory?.total ?? fleet?.total ?? '—'}</strong></article>
      <article className="good"><CheckCircle2 size={18} /><span>Healthy</span><strong>{counts ? counts.healthy ?? 0 : '—'}</strong></article>
      <article className="warn"><Wrench size={18} /><span>Needs attention</span><strong>{needsAttention ?? '—'}</strong></article>
      <article><Activity size={18} /><span>Not monitored</span><strong>{counts ? counts.unmonitored ?? 0 : '—'}</strong></article>
    </section>
    {canReadSystem && <>
      {systemError && <div className="rbac-page-error" role="alert">Analytics unavailable: {systemError}</div>}
      <section className="rbac-system-grid">
        <article><Server size={20} /><div><span>Analytics API</span><strong>{systemLoading ? 'Checking…' : systemError ? 'Unavailable' : system ? 'Responding' : 'Unknown'}</strong><p>Response status from the analytics service.</p></div></article>
        <article><Activity size={20} /><div><span>Events today</span><strong>{system?.events_today ?? '—'}</strong><p>{system?.pending_review !== undefined ? `${system.pending_review} awaiting review` : 'Review count unavailable'}</p></div></article>
      </section>
    </>}
    <section className="rbac-table-card">
      <div><h2>Camera maintenance</h2><span>{inventory ? `${inventory.data.length} visible records` : loading ? 'Loading cameras…' : 'Inventory unavailable'}</span></div>
      {inventoryError ? <p className="rbac-page-error" role="alert">{inventoryError}</p> : inventory?.data.length === 0 ? <p style={{ padding: 20 }}>No cameras registered in your scope.</p> : inventory && <div className="rbac-table-wrap" tabIndex={0} role="region" aria-label="Camera maintenance table"><table><thead><tr><th>Camera</th><th>Location</th><th>Status</th><th>Connectivity</th><th>Image quality</th><th>Last check</th></tr></thead><tbody>{inventory.data.map(camera => <tr key={camera.id}>
        <td><strong>{camera.name}</strong><small>{camera.external_id}</small></td>
        <td>{camera.location || 'Not recorded'}</td>
        <td><span className={`rbac-status ${camera.health.status}`}>{statusLabel(camera.health.status)}</span></td>
        <td>{statusLabel(camera.health.connectivity)}</td>
        <td>{camera.health.metrics.sharpness != null ? `${Math.round(camera.health.metrics.sharpness).toLocaleString()} sharpness` : statusLabel(camera.health.video_quality)}</td>
        <td>{camera.health.checked_at ? new Date(camera.health.checked_at).toLocaleString() : 'Never'}</td>
      </tr>)}</tbody></table></div>}
    </section>
  </div>;
}
