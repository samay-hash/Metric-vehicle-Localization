import type { Incident } from '../types';
import { useState, useEffect } from 'react';
import { getIncidents } from '../api';
import { SeverityBadge, StatusBadge, formatDateTime, EmptyState, LoadingDots } from '../components/Shared';
import { ChevronDown, ChevronUp, ShieldAlert } from 'lucide-react';
function IncidentCard({ incident }: { incident: Incident }) {
  const [expanded, setExpanded] = useState(false);
  const eventIds   = incident.event_ids   || incident.events_linked || [];
  const cameraIds  = incident.camera_ids  || [];
  const personIds  = incident.person_ids  || [];
  const timeline   = incident.timeline    || [];
  return (
    <div className={`card ${incident.severity === 'critical' ? 'red-accent' : ''}`} style={{ marginBottom: 12 }}>
      <div className="flex gap-3">
        <div style={{
          width: 3, borderRadius: 3, flexShrink: 0,
          background: incident.severity === 'critical' ? 'var(--red)' : 'var(--amber)',
          alignSelf: 'stretch',
        }} />
        <div style={{ flex: 1 }}>
          <div className="flex justify-between items-start mb-2">
            <div>
              <div className="font-bold" style={{ fontSize: 14, marginBottom: 3 }}>{incident.title}</div>
              <div className="font-mono text-xs text-muted">{incident.id}</div>
            </div>
            <div className="flex gap-2">
              <SeverityBadge severity={incident.severity} />
              <StatusBadge status={incident.status} />
            </div>
          </div>
          <div className="flex gap-4 mb-4">
            {cameraIds.length > 0 && (
              <div style={{ width: '160px', height: '90px', flexShrink: 0, borderRadius: '6px', overflow: 'hidden', border: '1px solid var(--border)', background: '#000' }}>
                <video
                  src={`http://127.0.0.1:8000/stream/${cameraIds[0]}`}
                  autoPlay
                  loop
                  muted
                  style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                />
                <div style={{ position: 'absolute', marginTop: '-18px', marginLeft: '4px', fontSize: '9px', background: 'rgba(0,0,0,0.6)', color: '#fff', padding: '1px 4px', borderRadius: '2px', fontWeight: 'bold' }}>
                  AUTO-CAPTURE
                </div>
              </div>
            )}
            <p style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.6, margin: 0, flex: 1 }}>
              {incident.summary}
            </p>
          </div>
          <div className="flex gap-3 mb-3" style={{ flexWrap: 'wrap' }}>
            {cameraIds.length > 0 && (
              <span className="text-xs text-muted" style={{
                background: 'var(--bg-surface)', border: '1px solid var(--border)',
                borderRadius: 4, padding: '2px 8px',
              }}>
                {cameraIds.length} camera{cameraIds.length > 1 ? 's' : ''}
              </span>
            )}
            {personIds.length > 0 && (
              <span className="text-xs text-muted" style={{
                background: 'var(--bg-surface)', border: '1px solid var(--border)',
                borderRadius: 4, padding: '2px 8px',
              }}>
                {personIds.length} person{personIds.length > 1 ? 's' : ''}
              </span>
            )}
            {eventIds.length > 0 && (
              <span className="text-xs text-muted" style={{
                background: 'var(--bg-surface)', border: '1px solid var(--border)',
                borderRadius: 4, padding: '2px 8px',
              }}>
                {eventIds.length} event{eventIds.length > 1 ? 's' : ''}
              </span>
            )}
            {cameraIds.length > 0 && (
              <span className="text-xs font-mono text-muted">{cameraIds.join(' · ')}</span>
            )}
          </div>
          {personIds.length > 0 && (
            <div className="flex gap-2 mb-3" style={{ flexWrap: 'wrap' }}>
              {personIds.map(pid => (
                <span key={pid} className="font-mono text-xs" style={{
                  background: 'var(--bg-surface)', border: '1px solid var(--border)',
                  borderRadius: 20, padding: '2px 8px', color: 'var(--text-secondary)',
                }}>👤 {pid}</span>
              ))}
            </div>
          )}
          {timeline.length > 0 && (
            <button className="btn btn-secondary btn-sm" onClick={() => setExpanded(!expanded)}>
              {expanded ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
              {expanded ? 'Hide timeline' : 'Show timeline'}
            </button>
          )}
        </div>
      </div>
      {expanded && timeline.length > 0 && (
        <div style={{ marginTop: 16, borderTop: '1px solid var(--border)', paddingTop: 14 }}>
          <div className="timeline">
            {timeline.map((t, i) => (
              <div
                key={i}
                className={`timeline-item ${
                  t.type?.includes('restricted') || t.type?.includes('removal') ? 'tl-critical' :
                  t.type?.includes('after_hours') ? 'tl-amber' : ''
                }`}
              >
                <div className="timeline-time">{t.time?.slice(11, 19)}</div>
                <div className="timeline-event">{t.event}</div>
                <div className="timeline-camera">{t.camera}</div>
              </div>
            ))}
          </div>
          {incident.notes && (
            <div style={{
              marginTop: 12, background: 'var(--bg-surface)',
              border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '10px 12px',
            }}>
              <div className="text-xs text-muted mb-1" style={{ fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                Investigator Notes
              </div>
              <p style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.6 }}>{incident.notes}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
export default function Incidents() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    getIncidents()
      .then(res => {
        const data = res.data.incidents || [];
        setIncidents(data); 
      })
      .catch(() => setIncidents([]))
      .finally(() => setLoading(false));
  }, []);
  const counts = {
    total:         incidents.length,
    critical:      incidents.filter(i => i.severity === 'critical').length,
    investigating: incidents.filter(i => i.status === 'under_investigation').length,
    escalated:     incidents.filter(i => i.status === 'escalated').length,
  };
  return (
    <div className="page-body">
      <div className="page-header">
        <div className="page-title">Incident Management</div>
        <div className="page-desc">Correlated incidents with cross-camera evidence timelines</div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, marginBottom: 20 }}>
        {[
          { label: 'Total Incidents', val: counts.total },
          { label: 'Critical',        val: counts.critical,      color: counts.critical > 0 ? 'red' : '' },
          { label: 'Investigating',   val: counts.investigating },
          { label: 'Escalated',       val: counts.escalated },
        ].map(({ label, val, color }) => (
          <div key={label} className="card" style={{ padding: '14px 16px' }}>
            <div className={`metric-value ${color || ''}`} style={{ fontSize: 22 }}>{val}</div>
            <div className="metric-label">{label}</div>
          </div>
        ))}
      </div>
      {loading ? (
        <div className="card flex items-center gap-2" style={{ justifyContent: 'center', padding: 32 }}>
          <LoadingDots />
          <span className="text-xs text-muted">Loading incidents…</span>
        </div>
      ) : incidents.length === 0 ? (
        <div className="card">
          <EmptyState
            icon={<ShieldAlert size={32} color="rgba(255,255,255,0.07)" />}
            title="No active incidents"
            desc="Incidents are created when suspicious events are escalated for investigation. Upload a CCTV video and review detected events to create your first incident."
          />
        </div>
      ) : (
        incidents.map(inc => <IncidentCard key={inc.id} incident={inc} />)
      )}
    </div>
  );
}