import { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { Bell, LogOut, RefreshCw, Moon, Sun, Monitor } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useDashboardAuth } from '../DashboardAuth';
const PAGE_META: Record<string, { title: string; desc: string }> = {
  '/':           { title: 'Command Center',        desc: 'City-wide traffic & threat monitoring' },
  '/live':       { title: 'City Grid Feeds',       desc: 'Multi-junction view with AI detection overlay' },
  '/events':     { title: 'Alert Log',             desc: 'All detected violations, alerts, and anomalies' },
  '/investigate':{ title: 'Semantic Search',       desc: 'Natural language investigation across city nodes' },
  '/incidents':  { title: 'Incident Management',   desc: 'Correlated incidents with evidence timelines' },
  '/reports':    { title: 'Daily Sentinel Report', desc: 'Daily public safety summary and documentation' },
  '/system':     { title: 'System Control', desc: 'Camera health, maintenance and analytics readiness' },
  '/access':     { title: 'Access Management', desc: 'Dashboard identities, roles and jurisdiction scopes' },
};
export default function TopHeader({ onRefresh, criticalCount }: { onRefresh: () => void; criticalCount: number | null }) {
  const auth = useDashboardAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [time, setTime] = useState(new Date());
  const meta = PAGE_META[location.pathname.replace('/dashboard', '') || '/'] || { title: 'Sentinel AI', desc: '' };
  
  const [themeMode, setThemeMode] = useState(() => localStorage.getItem('theme') || 'system');

  useEffect(() => {
    const applyTheme = (mode: string) => {
      const isDark = mode === 'dark' || (mode === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches);
      if (isDark) {
        document.documentElement.classList.add('dashboard-dark');
      } else {
        document.documentElement.classList.remove('dashboard-dark');
      }
    };
    applyTheme(themeMode);
    
    if (themeMode === 'system') {
      localStorage.removeItem('theme');
    } else {
      localStorage.setItem('theme', themeMode);
    }
  }, [themeMode]);

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);
  
  return (
    <div className="top-header">
      <div>
        <div className="header-title">{meta.title}</div>
        <div className="header-subtitle">{meta.desc}</div>
      </div>
      <div className="header-actions">
        <div className="header-time">
          {time.toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short' })}
          &nbsp;·&nbsp;
          {time.toLocaleTimeString('en-IN', { hour12: false })}
        </div>
        <div className="rbac-header-role"><strong>{auth.identity?.display_name || 'Authorised user'}</strong><span>{auth.identity?.roles?.[0]?.replaceAll('_', ' ')}</span></div>
        
        {/* Segmented Theme Toggle */}
        <div style={{ display: 'flex', background: 'rgba(128,128,128,0.1)', borderRadius: '24px', padding: '3px', border: '1px solid var(--border)', marginRight: '8px', gap: '2px' }}>
          <button 
            onClick={() => setThemeMode('light')} 
            style={{ padding: '6px 12px', borderRadius: '20px', border: 'none', background: themeMode === 'light' ? 'var(--bg-card)' : 'transparent', color: themeMode === 'light' ? 'var(--text-primary)' : 'var(--text-muted)', cursor: 'pointer', transition: 'all 0.2s', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: themeMode === 'light' ? '0 2px 4px rgba(0,0,0,0.1)' : 'none' }}
          >
            <Sun size={15} strokeWidth={themeMode === 'light' ? 2.5 : 2} />
          </button>
          <button 
            onClick={() => setThemeMode('dark')} 
            style={{ padding: '6px 12px', borderRadius: '20px', border: 'none', background: themeMode === 'dark' ? 'var(--bg-card)' : 'transparent', color: themeMode === 'dark' ? 'var(--text-primary)' : 'var(--text-muted)', cursor: 'pointer', transition: 'all 0.2s', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: themeMode === 'dark' ? '0 2px 4px rgba(0,0,0,0.2)' : 'none' }}
          >
            <Moon size={15} strokeWidth={themeMode === 'dark' ? 2.5 : 2} />
          </button>
          <button 
            onClick={() => setThemeMode('system')} 
            style={{ padding: '6px 12px', borderRadius: '20px', border: 'none', background: themeMode === 'system' ? 'var(--bg-card)' : 'transparent', color: themeMode === 'system' ? 'var(--text-primary)' : 'var(--text-muted)', cursor: 'pointer', transition: 'all 0.2s', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: themeMode === 'system' ? '0 2px 4px rgba(0,0,0,0.1)' : 'none' }}
          >
            <Monitor size={15} strokeWidth={themeMode === 'system' ? 2.5 : 2} />
          </button>
        </div>

        {onRefresh && (
          <button className="btn btn-secondary btn-icon" onClick={onRefresh} title="Refresh data">
            <RefreshCw size={15} />
          </button>
        )}
        <button className="btn btn-secondary btn-icon" style={{ position: 'relative' }} title={criticalCount === null ? "Alert count unavailable" : `${criticalCount} critical alerts`} disabled={!auth.has('event.read')} onClick={() => navigate('/dashboard/events')}>
          <Bell size={15} />
          {criticalCount !== null && criticalCount > 0 && <span style={{
            position: 'absolute', top: 5, right: 5,
            width: 5, height: 5, borderRadius: '50%',
            background: 'var(--red)',
          }} />}
        </button>
        <button className="btn btn-secondary btn-icon" title="Sign out" onClick={async () => { await auth.signOut(); navigate('/login', { replace: true }); }}><LogOut size={15} /></button>
      </div>
    </div>
  );
}
