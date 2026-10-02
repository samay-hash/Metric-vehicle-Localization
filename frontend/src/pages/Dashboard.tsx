import type { ReactNode } from 'react';
import type { RegistryCamera, SecurityEvent, SystemStats } from '../types';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getSystemStats, getEvents, getRawCctvStreamUrl } from '../api';
import { SeverityBadge, timeSince, EmptyState, LoadingDots } from '../components/Shared';
import { AlertTriangle, Camera, Eye, Shield, VideoOff } from 'lucide-react';
import { useDashboardFleet } from '../DashboardFleet';
import { useDashboardAuth } from '../DashboardAuth';
function MetricCard({ label, value, valueColor = '', icon, sub }: { label: string; value: ReactNode; valueColor?: string; icon: ReactNode; sub?: string }) {
  return (
    <div className="metric-card">
      <div className="metric-card-header">
        <div className="metric-icon-wrap">{icon}</div>
      </div>
      <div className={`metric-value ${valueColor}`}>{value}</div>
      <div className="metric-label">{label}</div>
      {sub && <div className="metric-sub">{sub}</div>}
    </div>
  );
}
function MiniCamera({ cam, hasEvents, canStream }: { cam: RegistryCamera; hasEvents: boolean; canStream: boolean }) {
  const navigate = useNavigate();
  const [failed, setFailed] = useState(false);
  const [connected, setConnected] = useState(false);
  const streamAvailable = canStream && cam.enabled && cam.source_state === 'approved' && cam.stream.configured;
  return (
    <div className="camera-cell" style={{ height: 150, aspectRatio: 'auto', border: hasEvents ? '1px solid rgba(239,68,68,0.35)' : undefined }}>
      {streamAvailable && !failed ? <img
        crossOrigin="use-credentials"
        src={getRawCctvStreamUrl(cam.id)} alt={`Live view of ${cam.name}`} loading="lazy"
        onLoad={() => setConnected(true)} onError={() => { setFailed(true); setConnected(false); }}
        style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover' }}
      /> : <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 6, color: '#cbd5e1', fontSize: 11 }}>
        <VideoOff size={16} />{failed ? 'Stream unavailable' : !canStream ? 'Preview restricted' : 'Stream not available'}
        {failed && <button className="btn btn-ghost btn-sm" style={{ color: '#cbd5e1' }} onClick={() => setFailed(false)}>Retry</button>}
      </div>}
      <div className="camera-top">
        <span style={{ fontSize: 9, color: '#fff', background: '#0009', padding: '2px 5px' }}>{connected ? 'LIVE' : (cam.health?.status ?? 'online').replaceAll('_', ' ')}</span>
        {hasEvents && <span style={{ fontSize: 9, color: '#fff', background: '#b91c1c', padding: '2px 5px' }}>ALERT</span>}
      </div>
      <div className="camera-overlay">
        <span className="camera-name">{cam.name}</span>
        {canStream && <button className="btn btn-ghost btn-sm" style={{ color: '#cbd5e1' }} aria-label={`Open ${cam.name}`} onClick={() => navigate(`/sentinel?camera=${encodeURIComponent(cam.id)}`)}>Open →</button>}
      </div>
    </div>
  );
}
const EVENT_ICONS: Record<string, string> = {
  restricted_entry:     '⚑',
  after_hours_presence: '◑',
  loitering:            '◎',
  unattended_object:    '◻',
  camera_tampering:     '✕',
  object_removal:       '◈',
  repeated_approach:    '↺',
  atm_obstruction:      '⊘',
  suspicious_motion:    '◉',
  normal_activity:      '·',
};
export default function Dashboard() {
  const navigate = useNavigate();
  const auth = useDashboardAuth();
  const { inventory, inventoryError, fleet, healthError, loading: fleetLoading, refresh: refreshFleet } = useDashboardFleet();
  const [error, setError] = useState('');
  const [stats, setStats]   = useState<SystemStats | null>(null);
  const [events, setEvents] = useState<SecurityEvent[]>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const [sRes, eRes] = await Promise.all([
          getSystemStats(),
          getEvents({ limit: 10 }),
        ]);
        if (!active) return;
        setError('');
        setStats(sRes.data);
        setEvents(eRes.data.events || []);
      } catch {
        if (active) {
          setStats(null);
          setEvents([]);
          setError('Analytics data is unavailable. Retrying automatically.');
        }
      } finally {
        if (active) setLoading(false);
      }
    }
    load();
    const t = setInterval(load, 10000);

    // WebSocket connection for real-time alerts
    const ws = new WebSocket(`ws://${window.location.hostname}:8000/ws`);
    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data) as { type?: string; data?: SecurityEvent } | null;
        if (msg?.type === 'new_event' && msg.data) {
          const newEvent = msg.data;
          setEvents(prev => [newEvent, ...prev].slice(0, 10));
          // Refresh the typed feed and counters when the server announces a new event.
          load();
        }
      } catch (err) {
        console.error('WS Error:', err);
      }
    };

    return () => {
      active = false;
      clearInterval(t);
      ws.close();
    };
  }, []);
  const alertCameraIds = new Set(
    events.filter(e => e.status === 'pending_review').map(e => e.camera_id)
  );
  return (
    <div className="page-body">
      <div className="page-header">
        <div className="page-title">City Security Observatory</div>
        <div className="page-desc">
          Gujarat Police Headquarters — Command & Control Center &nbsp;·&nbsp; Node ID: CCC-AHD-001
        </div>
      </div>
      {}
      {error && <div className="rbac-page-error" role="alert">{error}</div>}
      {loading ? (
        <div className="flex items-center gap-2 mb-4" style={{ color: 'var(--text-muted)' }}>
          <LoadingDots />
          <span style={{ fontSize: 12 }}>Loading system stats…</span>
        </div>
      ) : (
        <div className="metric-grid">
          <MetricCard
            label="Critical Events"
            value={stats?.critical_events ?? '—'}
            valueColor={(stats?.critical_events ?? 0) > 0 ? 'red' : ''}
            icon={<AlertTriangle size={14} color="var(--text-muted)" />}
            sub="Requires immediate review"
          />
          <MetricCard
            label="Active Incidents"
            value={stats?.active_incidents ?? '—'}
            icon={<Shield size={14} color="var(--text-muted)" />}
            sub="Under investigation"
          />
          <MetricCard
            label="Healthy Cameras"
            value={fleet ? `${fleet.counts.healthy ?? 0}/${fleet.total}` : '—'}
            valueColor={(fleet?.counts.healthy ?? 0) > 0 ? 'green' : ''}
            icon={<Camera size={14} color="var(--text-muted)" />}
            sub={healthError ? 'Camera health unavailable' : !fleet ? 'Loading camera health…' : `${fleet.counts.stale ?? 0} stale · ${fleet.counts.unmonitored ?? 0} unmonitored`}
          />
          <MetricCard
            label="Events Today"
            value={stats?.events_today ?? '—'}
            icon={<Eye size={14} color="var(--text-muted)" />}
            sub={(stats?.pending_review ?? 0) > 0 ? `${stats?.pending_review} pending review` : 'Detected activity across registered cameras'}
          />
        </div>
      )}
      
      {!loading && stats?.hardware && (
        <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem', marginBottom: '1.5rem', fontSize: '11px', color: 'var(--text-muted)', background: 'var(--bg-card)', padding: '8px 12px', borderRadius: '6px', border: '1px solid var(--border)' }}>
          <div style={{ fontWeight: 600 }}>Edge Node Telemetry</div>
          <div>CPU: <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{stats.hardware.cpu}%</span></div>
          <div>RAM: <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{stats.hardware.ram}%</span></div>
        </div>
      )}
      {}
      <div className="section-grid">
        {}
        <div className="card">
          <div className="card-header">
            <span className="card-title"><Camera size={11} /> Camera Overview</span>
            {auth.has('camera.stream.view') && <button className="btn btn-ghost btn-sm" onClick={() => navigate('/sentinel')}>
              View all →
            </button>}
          </div>
          {inventoryError ? <div className="rbac-page-error" role="alert">Camera registry unavailable. <button className="btn btn-secondary btn-sm" onClick={refreshFleet}>Retry</button></div>
            : !inventory && fleetLoading ? <div style={{ padding: 20 }}>Loading cameras…</div>
            : inventory?.data.length === 0 ? <EmptyState icon={<Camera size={24} />} title="No cameras registered" sub="Registered cameras will appear here." />
            : <>
              <div className="camera-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
                {inventory?.data.slice(0, 8).map(cam => <MiniCamera key={`${cam.id}-${cam.revision}`} cam={cam} canStream={auth.has('camera.stream.view')} hasEvents={alertCameraIds.has(cam.id) || alertCameraIds.has(cam.external_id)} />)}
              </div>
              {inventory && inventory.total > 8 && <p className="text-xs text-muted" style={{ padding: 12 }}>Showing 8 of {inventory.total} registered cameras</p>}
            </>}

        </div>
        {}
        <div className="card">
          <div className="card-header">
            <span className="card-title"><AlertTriangle size={11} /> Live Alert Feed</span>
            <button className="btn btn-ghost btn-sm" onClick={() => navigate('/dashboard/events')}>
              All events →
            </button>
          </div>
          {error ? <div style={{ padding: 24 }} className="text-muted">Alert feed unavailable</div> : events.length === 0 ? (
            <div style={{ padding: '24px 0' }}>
              <EmptyState
                icon={<Eye size={28} color="var(--border)" />}
                title="No events yet"
                sub="Detected events from registered cameras will appear here."
              />

            </div>
          ) : (
            <div className="alert-feed">
              {events.map(ev => (
                <div
                  key={ev.id}
                  className={`alert-item ${ev.severity}`}
                  onClick={() => navigate('/dashboard/events')}
                >
                  <span className="alert-icon" style={{ color: 'var(--text-muted)' }}>
                    {EVENT_ICONS[ev.event_type] || '·'}
                  </span>
                  <div className="alert-body">
                    <div className="alert-title">
                      {ev.event_type?.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </div>
                    <div className="alert-meta">
                      <span>{ev.camera_name}</span>
                      {ev.description && (
                        <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>
                          {ev.description.slice(0, 60)}{ev.description.length > 60 ? '…' : ''}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="alert-right">
                    <SeverityBadge severity={ev.severity} />
                    <span className="alert-time">{timeSince(ev.timestamp)}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
      {}
      <div className="flex gap-2 mt-4">
        <button className="btn btn-secondary" onClick={() => navigate('/dashboard/investigate')}>
          Start Investigation
        </button>
        <button className="btn btn-secondary" onClick={() => navigate('/dashboard/reports')}>
          Daily Report
        </button>
        {(stats?.active_incidents ?? 0) > 0 && (
          <button className="btn btn-secondary" onClick={() => navigate('/dashboard/incidents')}>
            Active Incidents ({stats?.active_incidents})
          </button>
        )}
      </div>
    </div>
  );
}
