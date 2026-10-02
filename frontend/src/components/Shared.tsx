import type { ReactNode } from 'react';
import type { Severity, EventStatus } from '../types';
export function SeverityBadge({ severity }: { severity: Severity }) {
  const map = {
    critical: { cls: 'badge badge-critical', label: 'CRITICAL' },
    high:     { cls: 'badge badge-high',     label: 'HIGH' },
    medium:   { cls: 'badge badge-medium',   label: 'MEDIUM' },
    low:      { cls: 'badge badge-low',      label: 'LOW' },
  };
  const { cls, label } = map[severity] || map.medium;
  return <span className={cls}>{label}</span>;
}
export function StatusBadge({ status }: { status: EventStatus }) {
  const labels: Partial<Record<EventStatus, string>> = {
    pending_review:       'Pending',
    under_investigation:  'Investigating',
    resolved:             'Resolved',
    escalated:            'Escalated',
    false_positive:       'False +ve',
  };
  return (
    <span className={`status-badge ${status}`}>
      {labels[status] || status}
    </span>
  );
}
export function PersonPill({ id }: { id: string }) {
  return <span className="person-pill">👤 {id}</span>;
}
export function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const cls = pct > 90 ? 'high' : pct < 60 ? 'low' : '';
  return (
    <div className="confidence-bar">
      <div className="confidence-track">
        <div className={`confidence-fill ${cls}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="confidence-label">{pct}%</span>
    </div>
  );
}
export function LoadingDots() {
  return (
    <div className="loading-dots">
      <span /><span /><span />
    </div>
  );
}
export function EmptyState({ icon = '—', title, desc, sub }: { icon?: ReactNode; title: string; desc?: string; sub?: string }) {
  return (
    <div className="empty-state">
      <div className="empty-icon">{icon}</div>
      <div className="empty-title">{title}</div>
      {(desc || sub) && <div className="empty-desc">{desc || sub}</div>}
    </div>
  );
}
export function formatTime(isoStr: string | null | undefined) {
  if (!isoStr) return '—';
  return new Date(isoStr).toLocaleTimeString('en-IN', {
    hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
  });
}
export function formatDateTime(isoStr: string | null | undefined) {
  if (!isoStr) return '—';
  const d = new Date(isoStr);
  return d.toLocaleString('en-IN', {
    day: '2-digit', month: 'short',
    hour: '2-digit', minute: '2-digit', hour12: false,
  });
}
export function timeSince(isoStr: string | null | undefined) {
  if (!isoStr) return '';
  const s = (Date.now() - new Date(isoStr).getTime()) / 1000;
  if (s < 60)   return `${Math.floor(s)}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  return `${Math.floor(s / 3600)}h ago`;
}