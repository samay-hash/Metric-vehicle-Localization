import type { Permission } from '../types';
import type { LucideIcon } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';
import { LayoutDashboard, Video, AlertTriangle, Search, FileText, Shield, Map, Server, Users, ScrollText, ScanLine } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useDashboardAuth } from '../DashboardAuth';
import { useDashboardFleet } from '../DashboardFleet';
const NAV_GROUPS: { label: string; items: { path: string; icon: LucideIcon; label: string; permission: Permission; alternativePermission?: Permission; hasBadge?: boolean }[] }[] = [
  {
    label: 'Operations',
    items: [
      { path: '/dashboard/system', icon: Server, label: 'System control', permission: 'system.read', alternativePermission: 'maintenance.manage' },
    ],
  },
  {
    label: 'Monitoring',
    items: [
      { path: '/dashboard', icon: LayoutDashboard, label: 'Dashboard', permission: 'event.read' },
      { path: '/sentinel', icon: Video, label: 'Live Feeds', permission: 'camera.stream.view' },
      { path: '/dashboard/events', icon: AlertTriangle, label: 'Events', hasBadge: true, permission: 'event.read' },
    ],
  },
  {
    label: 'Investigation',
    items: [
      { path: '/dashboard/investigate', icon: Search, label: 'Investigate', permission: 'investigation.run' },
      { path: '/dashboard/incidents', icon: Shield, label: 'Incidents', permission: 'incident.read' },
    ],
  },
  {
    label: 'Reporting',
    items: [
      { path: '/dashboard/reports', icon: FileText, label: 'Reports', permission: 'report.read' },
      { path: '/dashboard/cv-results', icon: ScanLine, label: 'CV Results', permission: 'report.read' },
    ],
  },
  {
    label: 'Configuration',
    items: [
      { path: '/dashboard/topology', icon: Map, label: 'Topology', permission: 'topology.read' },
      { path: '/dashboard/access', icon: Users, label: 'Access', permission: 'user.manage' },
      { path: '/dashboard/audit', icon: ScrollText, label: 'Security audit', permission: 'audit.read' },
    ],
  },
];
export default function Sidebar({ criticalCount = null }: { criticalCount?: number | null }) {
  const auth = useDashboardAuth();
  const { fleet, healthError, loading } = useDashboardFleet();
  const healthy = fleet?.counts.healthy ?? 0;
  const healthColor = healthError ? 'var(--red)' : fleet && fleet.total > 0 && healthy === fleet.total ? 'var(--green)' : 'var(--text-muted)';
  const healthLabel = healthError ? 'Camera health unavailable' : !fleet ? 'Loading camera health…' : fleet.total === 0 ? 'No cameras registered' : healthy === fleet.total ? 'All cameras healthy' : 'Camera health overview';
  const location = useLocation();
  const navigate  = useNavigate();
  const [time, setTime] = useState(new Date());
  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);
  return (
    <div className="sidebar">
      {}
      <div className="sidebar-logo">
        <div className="logo-icon">🛡️</div>
        <div>
          <div className="logo-name">Sentinel AI</div>
          <div className="logo-tag">Gujarat Police Surveillance</div>
        </div>
      </div>
      {}
      <nav className="sidebar-nav">
        {NAV_GROUPS.map(group => ({ ...group, items: group.items.filter(item => auth.has(item.permission) || (item.alternativePermission && auth.has(item.alternativePermission))) })).filter(group => group.items.length).map(group => (
          <div key={group.label}>
            <div className="sidebar-section-label">{group.label}</div>
            {group.items.map(item => {
              const active = location.pathname === item.path;
              const Icon   = item.icon;
              return (
                <button
                  key={item.path}
                  className={`nav-item ${active ? 'active' : ''}`}
                  onClick={() => navigate(item.path)}
                >
                  <Icon size={14} />
                  <span>{item.label}</span>
                  {item.hasBadge && criticalCount !== null && criticalCount > 0 && (
                    <span className="badge">{criticalCount}</span>
                  )}
                </button>
              );
            })}
          </div>
        ))}
      </nav>
      {}
      <div className="sidebar-bottom">
        <div className="rbac-sidebar-user"><strong>{auth.identity?.display_name || auth.identity?.email}</strong><span>{auth.identity?.roles?.map(role => role.replaceAll('_', ' ')).join(' · ')}</span></div>
        <div className="flex justify-between items-center mb-2">
          <span className="text-xs text-muted">Camera health</span>
          <span className="font-mono text-xs text-muted">
            {time.toLocaleTimeString('en-IN', { hour12: false })}
          </span>
        </div>
        <div className="system-status" style={{ background: 'var(--bg-card)', borderColor: 'var(--border)' }}>
          <div className="status-dot" style={{ background: healthColor, animation: 'none' }} />
          <div>
            <div className="status-text" style={{ color: healthColor }}>{healthLabel}</div>
            <div className="status-sub">{fleet ? `${healthy}/${fleet.total} healthy${loading ? ' · refreshing' : ''}` : 'Status unknown'}</div>
          </div>
        </div>
      </div>
    </div>
  );
}
