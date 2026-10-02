import { BrowserRouter, Routes, Route, Outlet, Navigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import TopHeader from './components/TopHeader';
import Dashboard from './pages/Dashboard';
import LiveFeed from './pages/LiveFeed';
import Events from './pages/Events';
import Investigate from './pages/Investigate';
import Incidents from './pages/Incidents';
import Reports from './pages/Reports';
import Topology from './pages/Topology';
import Landing from './pages/Landing';
import CVResults from './pages/CVResults';
import VendorLogin from './pages/VendorLogin';
import VendorOnboarding from './pages/VendorOnboarding';
import SystemOperations from './pages/SystemOperations';
import AccessManagement from './pages/AccessManagement';
import SecurityAudit from './pages/SecurityAudit';
import DashboardLogin, { Forbidden } from './pages/DashboardLogin';
import { DashboardAuthProvider, RequireDashboard, useDashboardAuth } from './DashboardAuth';
import { getEvents } from './api';
import { DashboardFleetProvider, useDashboardFleet } from './DashboardFleet';
import './vendor.css';
import './rbac.css';

function DashboardLayout() {
  const auth = useDashboardAuth();
  const fleet = useDashboardFleet();
  const [criticalCount, setCriticalCount] = useState<number | null>(null);
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    if (!auth.has('event.read')) return;
    let active = true;
    getEvents({ severity: 'critical', status: 'pending_review' })
      .then(res => { if (active) setCriticalCount(res.data.total); })
      .catch(() => { if (active) setCriticalCount(null); });
    return () => { active = false; };
  }, [refresh, auth.identity]);

  return (
    <div className="app-layout">
      <Sidebar criticalCount={criticalCount} />
      <div className="main-content">
        <TopHeader criticalCount={criticalCount} onRefresh={() => { setRefresh(r => r + 1); fleet.refresh(); }} />
        <Outlet />
      </div>
    </div>
  );
}

export default function App() {
  useEffect(() => {
    // Initialize theme
    if (localStorage.theme === 'dark' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
      document.documentElement.classList.add('dashboard-dark');
    } else {
      document.documentElement.classList.remove('dashboard-dark');
    }
  }, []);

  return (
    <BrowserRouter>
      <DashboardAuthProvider>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<DashboardLogin />} />
          <Route path="/forbidden" element={<Forbidden />} />
          <Route path="/sentinel" element={<RequireDashboard permission="camera.stream.view"><LiveFeed /></RequireDashboard>} />
          <Route path="/vendor/login" element={<VendorLogin />} />
          <Route path="/vendor/onboarding" element={<VendorOnboarding />} />

          <Route path="/dashboard" element={<RequireDashboard permission="dashboard.access"><DashboardFleetProvider><DashboardLayout /></DashboardFleetProvider></RequireDashboard>}>
            <Route index element={<RequireDashboard permission="event.read"><Dashboard /></RequireDashboard>} />
            <Route path="events" element={<RequireDashboard permission="event.read"><Events /></RequireDashboard>} />
            <Route path="investigate" element={<RequireDashboard permission="investigation.run"><Investigate /></RequireDashboard>} />
            <Route path="incidents" element={<RequireDashboard permission="incident.read"><Incidents /></RequireDashboard>} />
            <Route path="reports" element={<RequireDashboard permission="report.read"><Reports /></RequireDashboard>} />
            <Route path="upload" element={<Navigate to="/dashboard" replace />} />
            <Route path="topology" element={<RequireDashboard permission="topology.read"><Topology /></RequireDashboard>} />
            <Route path="maintenance" element={<Navigate to="/dashboard/system" replace />} />
            <Route path="system" element={<RequireDashboard anyPermissions={["system.read", "maintenance.manage"]}><SystemOperations /></RequireDashboard>} />
            <Route path="access" element={<RequireDashboard permission="user.manage"><AccessManagement /></RequireDashboard>} />
            <Route path="audit" element={<RequireDashboard permission="audit.read"><SecurityAudit /></RequireDashboard>} />
            <Route path="cv-results" element={<CVResults />} />
          </Route>
        </Routes>
      </DashboardAuthProvider>
    </BrowserRouter>
  );
}
