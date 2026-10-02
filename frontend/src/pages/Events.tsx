import type { SecurityEvent, EventUpdateStatus } from '../types';
import { useEffect, useState } from 'react';
import { getEvents, updateEventStatus } from '../api';
import {
  SeverityBadge, StatusBadge, PersonPill,
  ConfidenceBar, formatDateTime, EmptyState, LoadingDots,
} from '../components/Shared';
import { Filter, RefreshCw, Eye } from 'lucide-react';
const EVENT_ICONS: Record<string, string> = {
  restricted_entry:     '⚑',
  after_hours_presence: '◑',
  loitering:            '◎',
  unattended_object:    '◻',
  camera_tampering:     '✕',
  object_removal:       '◈',
  repeated_approach:    '↺',
  person_following:     '⇥',
  atm_obstruction:      '⊘',
  suspicious_motion:    '◉',
  normal_activity:      '○',
  counter_approach:     '→',
  restricted_zone_entry:'⚠',
};
export default function Events() {
  const [events, setEvents]   = useState<SecurityEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ severity: '', status: '', zone: '' });
  const [selected, setSelected] = useState<SecurityEvent | null>(null);
  const [updating, setUpdating] = useState<string | null>(null);
  async function load() {
    setLoading(true);
    try {
      const params = Object.fromEntries(Object.entries(filters).filter(([, v]) => v));
      const res = await getEvents(params);
      setEvents(res.data.events || []);
    } catch {
      setEvents([]);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => { load(); }, [filters]);
  async function handleStatus(id: string, status: EventUpdateStatus) {
    setUpdating(id);
    try {
      await updateEventStatus(id, status);
      setEvents(ev => ev.map(e => e.id === id ? { ...e, status } : e));
      if (selected?.id === id) setSelected(s => s ? { ...s, status } : null);
    } finally {
      setUpdating(null);
    }
  }
  return (
    <div
      className="page-body"
      style={{ display: 'grid', gridTemplateColumns: selected ? '1fr 380px' : '1fr', gap: 16 }}
    >
      {}
      <div>
        <div className="page-header">
          <div className="page-title">Event Log</div>
          <div className="page-desc">AI-detected events from all branch cameras</div>
        </div>
        <div className="flex items-center gap-2 mb-3" style={{ flexWrap: 'wrap' }}>
          <Filter size={12} color="var(--text-muted)" />
          {[
            { key: 'severity', label: 'All Severity', opts: ['critical','high','medium','low'] },
            { key: 'status',   label: 'All Status',   opts: ['pending_review','under_investigation','resolved','escalated','false_positive'] },
            { key: 'zone',     label: 'All Zones',    opts: ['restricted','cash_counter','atm','entrance','exterior','lobby','unknown'] },
          ].map(({ key, label, opts }) => (
            <select
              key={key}
              className="filter-select"
              value={filters[key as keyof typeof filters]}
              onChange={e => setFilters(f => ({ ...f, [key]: e.target.value }))}
            >
              <option value="">{label}</option>
              {opts.map(o => <option key={o} value={o}>{o.replace(/_/g, ' ')}</option>)}
            </select>
          ))}
          <button className="btn btn-secondary btn-sm" onClick={load}>
            <RefreshCw size={11} /> Refresh
          </button>
          <span className="text-xs text-muted" style={{ marginLeft: 'auto' }}>
            {events.length} event{events.length !== 1 ? 's' : ''}
          </span>
        </div>
        {loading ? (
          <div className="card flex items-center gap-2" style={{ justifyContent: 'center', padding: 32 }}>
            <LoadingDots />
            <span className="text-xs text-muted">Loading events…</span>
          </div>
        ) : events.length === 0 ? (
          <div className="card">
            <EmptyState icon="○" title="No events yet" desc="Upload a CCTV video to run AI analysis. Events will appear here automatically." />
          </div>
        ) : (
          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Event</th>
                  <th>Camera</th>
                  <th>Person</th>
                  <th>Time</th>
                  <th>Severity</th>
                  <th>Confidence</th>
                  <th>Status</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {events.map(ev => (
                  <tr
                    key={ev.id}
                    className={selected?.id === ev.id ? 'row-selected' : ''}
                    style={{ cursor: 'pointer' }}
                    onClick={() => setSelected(s => s?.id === ev.id ? null : ev)}
                  >
                    <td>
                      <div className="flex items-center gap-2">
                        <span style={{ fontSize: 14, color: 'var(--text-muted)', fontFamily: 'monospace' }}>
                          {EVENT_ICONS[ev.event_type] || '·'}
                        </span>
                        <div>
                          <div className="font-semibold" style={{ fontSize: 12 }}>
                            {ev.event_type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                          </div>
                          <div className="font-mono text-xs text-muted">{ev.id}</div>
                        </div>
                      </div>
                    </td>
                    <td>
                      <div className="font-semibold" style={{ fontSize: 12 }}>{ev.camera_name}</div>
                      <div className="font-mono text-xs text-muted">{ev.camera_id}</div>
                    </td>
                    <td>
                      {ev.person_id
                        ? <PersonPill id={ev.person_id} />
                        : <span className="text-muted">—</span>}
                    </td>
                    <td>
                      <span className="font-mono text-xs">{formatDateTime(ev.timestamp)}</span>
                    </td>
                    <td><SeverityBadge severity={ev.severity} /></td>
                    <td style={{ minWidth: 110 }}>
                      <ConfidenceBar value={Math.min(ev.confidence, 0.99)} />
                    </td>
                    <td><StatusBadge status={ev.status} /></td>
                    <td>
                      <button
                        className="btn btn-ghost btn-icon btn-sm"
                        onClick={e => { e.stopPropagation(); setSelected(ev); }}
                      >
                        <Eye size={12} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      {}
      {selected && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12, overflowY: 'auto', maxHeight: 'calc(100vh - 80px)' }}>
          <div className="card">
            <div className="card-header">
              <span className="card-title">Event Detail</span>
              <button className="btn btn-ghost btn-sm" onClick={() => setSelected(null)}>✕</button>
            </div>
            {}
            {selected.thumbnail && (
              <div style={{ marginBottom: 14, borderRadius: 6, overflow: 'hidden', border: '1px solid var(--border)' }}>
                <img
                  src={selected.thumbnail?.startsWith('http') ? selected.thumbnail : `http://127.0.0.1:8000${selected.thumbnail}`}
                  alt="AI annotated evidence frame"
                  style={{ width: '100%', display: 'block', maxHeight: 210, objectFit: 'cover' }}
                  onError={e => e.currentTarget.style.display = 'none'}
                />
                <div style={{
                  background: 'var(--bg-surface)', padding: '4px 10px',
                  fontSize: 10, color: 'var(--text-muted)', fontFamily: 'var(--mono)',
                  display: 'flex', justifyContent: 'space-between',
                }}>
                  <span>EVIDENCE FRAME — {selected.id}</span>
                  <span>YOLO + EDGE AI ANNOTATED</span>
                </div>
              </div>
            )}
            {}
            {selected.clip_ref && (
              <div style={{ marginBottom: 14 }}>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: 1 }}>
                  Evidence Clip
                </div>
                <video
                  src={selected.clip_ref.startsWith('http') ? selected.clip_ref : `http://127.0.0.1:8000${selected.clip_ref}`}
                  controls
                  autoPlay
                  loop
                  muted
                  style={{ width: '100%', borderRadius: 6, border: '1px solid var(--border)', maxHeight: 160, background: '#000' }}
                  onError={(e) => {
                    // Fallback to the live stream if the pre-recorded clip is missing
                    if (!e.currentTarget.dataset.fallback) {
                      e.currentTarget.dataset.fallback = 'true';
                      e.currentTarget.src = `http://127.0.0.1:8000/stream/${selected.camera_id}`;
                    } else {
                      e.currentTarget.style.display = 'none';
                    }
                  }}
                />
              </div>
            )}
            <div className="flex items-center gap-3 mb-3">
              <span style={{ fontSize: 24, color: 'var(--text-muted)' }}>
                {EVENT_ICONS[selected.event_type] || '◉'}
              </span>
              <div>
                <div className="font-bold" style={{ fontSize: 14 }}>
                  {selected.event_type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                </div>
                <div className="font-mono text-xs text-muted">{selected.id}</div>
              </div>
            </div>
            <p style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.65, marginBottom: 14 }}>
              {selected.description}
            </p>
            {}
            {selected.vlm_analysis?.activity && (
              <div style={{
                marginBottom: 12, padding: '6px 10px',
                background: 'rgba(99,102,241,0.08)', border: '1px solid rgba(99,102,241,0.2)',
                borderRadius: 6, fontSize: 11, color: '#818cf8',
              }}>
                🎯 <strong>Activity:</strong> {selected.vlm_analysis.activity}
              </div>
            )}
            {}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 14 }}>
              {[
                { label: 'Camera',    val: selected.camera_name },
                { label: 'Zone',      val: selected.zone.replace(/_/g, ' ') },
                { label: 'Duration',  val: selected.duration_sec != null ? `${selected.duration_sec}s` : '—' },
                { label: 'Confidence',val: `${Math.round(Math.min(selected.confidence, 0.99) * 100)}%` },
                { label: 'Persons',   val: selected.vlm_analysis?.person_count ?? 1 },
                { label: 'At',        val: selected.vlm_analysis?.frame_timestamp_sec != null ? `${selected.vlm_analysis.frame_timestamp_sec}s` : '—' },
              ].map(({ label, val }) => (
                <div key={label} style={{
                  background: 'var(--bg-surface)', padding: '8px 10px',
                  borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)',
                }}>
                  <div className="text-xs text-muted mb-1">{label}</div>
                  <div className="font-mono font-semibold" style={{ fontSize: 12 }}>{val}</div>
                </div>
              ))}
            </div>
            {}
            {selected.vlm_analysis?.persons && selected.vlm_analysis.persons.length > 0 && (
              <div style={{ marginBottom: 14 }}>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: 1 }}>
                  Tracked Persons
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
                  {selected.vlm_analysis.persons.map(p => (
                    <div key={p.id} style={{
                      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                      background: 'var(--bg-surface)', borderRadius: 6, padding: '6px 10px',
                      border: '1px solid var(--border)',
                    }}>
                      <span className="font-mono" style={{ fontSize: 11, color: 'var(--text-primary)' }}>👤 {p.id}</span>
                      <span style={{
                        fontSize: 10, padding: '2px 6px', borderRadius: 3, fontWeight: 600,
                        background: ['restricted','cash_counter'].includes(p.zone) ? 'rgba(239,68,68,0.12)' : 'rgba(16,185,129,0.1)',
                        color:      ['restricted','cash_counter'].includes(p.zone) ? '#ef4444' : '#10b981',
                        border:     ['restricted','cash_counter'].includes(p.zone) ? '1px solid rgba(239,68,68,0.3)' : '1px solid rgba(16,185,129,0.2)',
                      }}>
                        {p.zone.replace(/_/g, ' ')}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
            <div className="flex gap-2 mb-3" style={{ flexWrap: 'wrap' }}>
              {selected.person_id && <PersonPill id={selected.person_id} />}
              <SeverityBadge severity={selected.severity} />
              <StatusBadge status={selected.status} />
            </div>
            <div style={{ borderTop: '1px solid var(--border)', paddingTop: 12 }}>
              <div className="text-xs text-muted mb-2">Update Status</div>
              <div className="flex gap-2" style={{ flexWrap: 'wrap' }}>
                {(['under_investigation', 'resolved', 'escalated', 'false_positive'] as const).map(s => (
                  <button
                    key={s}
                    className="btn btn-secondary btn-sm"
                    disabled={updating === selected.id || selected.status === s}
                    onClick={() => handleStatus(selected.id, s)}
                    style={{ fontSize: 10 }}
                  >
                    {s.replace(/_/g, ' ')}
                  </button>
                ))}
              </div>
            </div>
          </div>
          {}
          {selected.vlm_analysis && (
            <div className="card amber-accent">
              <div className="card-header">
                <span className="card-title">✦ Local Edge AI Analysis</span>
                <span className="text-xs" style={{ color: 'var(--amber)', fontWeight: 700 }}>
                  {Math.round(Math.min(selected.vlm_analysis.confidence ?? 0.9, 0.99) * 100)}% conf
                </span>
              </div>
              <p style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.65, marginBottom: 12 }}>
                {selected.vlm_analysis.summary}
              </p>
              {selected.vlm_analysis.flags && selected.vlm_analysis.flags.length > 0 && (
                <div className="mb-3">
                  <div className="text-xs text-muted mb-2">Detected Flags</div>
                  <div className="flex gap-1" style={{ flexWrap: 'wrap' }}>
                    {selected.vlm_analysis.flags.map(f => (
                      <span key={f} style={{
                        background: 'var(--red-dim)', border: '1px solid rgba(244,63,94,0.2)',
                        color: 'var(--red)', borderRadius: 4, padding: '2px 7px',
                        fontSize: 10, fontWeight: 600,
                      }}>{f.replace(/_/g, ' ')}</span>
                    ))}
                  </div>
                </div>
              )}
              {selected.vlm_analysis.objects_detected && selected.vlm_analysis.objects_detected.length > 0 && (
                <div>
                  <div className="text-xs text-muted mb-2">Objects Detected</div>
                  <div className="flex gap-1" style={{ flexWrap: 'wrap' }}>
                    {selected.vlm_analysis.objects_detected.map(obj => (
                      <span key={obj} style={{
                        background: 'var(--bg-surface)', border: '1px solid var(--border)',
                        borderRadius: 4, padding: '2px 7px', fontSize: 10, color: 'var(--text-secondary)',
                      }}>{obj}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}