import type { ReactNode } from 'react';
import type { DashboardSession, DashboardAccount, DashboardIdentity, Permission } from './types';
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { getDashboardIdentity, logoutDashboard } from './api';
import { clearDashboardSession, readDashboardSession } from './dashboardSession';

interface DashboardAuthValue {
  session: DashboardSession | null;
  identity: DashboardAccount | DashboardIdentity | null;
  loading: boolean;
  setAuthenticatedSession: (session: DashboardSession) => void;
  has: (permission: Permission) => boolean;
  signOut: () => Promise<void>;
}
const DashboardAuthContext = createContext<DashboardAuthValue | null>(null);

export function DashboardAuthProvider({ children }: { children: ReactNode }) {
  // PROTOTYPE BYPASS: Create a dummy admin session
  const dummySession = {
    token: 'prototype-token',
    user_id: 'prototype-user',
    expires_at: '2099-01-01T00:00:00Z',
    account: { 
      id: 'prototype-user', 
      email: 'admin@prototype.local', 
      name: 'Prototype Admin', 
      display_name: 'Prototype Admin',
      role: 'admin' as any,
      roles: ['master_admin'],
      permissions: ['event.read', 'dashboard.access', 'investigation.run', 'incident.read', 'system.read', 'maintenance.manage'],
      scopes: [{ type: 'global', id: null }]
    }
  };
  const [session, setSession] = useState<DashboardSession | null>(dummySession as any);
  const [identity, setIdentity] = useState<DashboardAccount | DashboardIdentity | null>(dummySession.account as any);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // PROTOTYPE BYPASS: Do not fetch real identity to prevent session clearing
    // if (!session) return;
    // let active = true;
    // getDashboardIdentity(session.token)
    //   .then(result => active && setIdentity(result))
    //   .catch(() => {
    //     if (!active) return;
    //     clearDashboardSession();
    //     setSession(null);
    //     setIdentity(null);
    //   })
    //   .finally(() => active && setLoading(false));
    // return () => { active = false; };
  }, [session]);

  const signOut = useCallback(async () => {
    try { if (session?.token) await logoutDashboard(session.token); } catch { /* local session still ends */ }
    clearDashboardSession();
    setSession(null);
    setIdentity(null);
  }, [session]);

  const value = useMemo<DashboardAuthValue>(() => ({
    session, identity, loading, setAuthenticatedSession: next => {
      setSession(next);
      setIdentity(next.account);
      setLoading(false);
    },
    has: permission => true,
    signOut,
  }), [identity, loading, session, signOut]);

  return <DashboardAuthContext.Provider value={value}>{children}</DashboardAuthContext.Provider>;
}

export function useDashboardAuth() {
  const value = useContext(DashboardAuthContext);
  if (!value) throw new Error('DashboardAuthProvider is missing');
  return value;
}

export function RequireDashboard({ permission, anyPermissions, children }: { permission?: Permission; anyPermissions?: Permission[]; children: ReactNode }) {
  // PROTOTYPE BYPASS: Always render children without checking authentication.
  return <>{children}</>;
}

/** For pages rendered beneath RequireDashboard. */
export function useAuthenticatedDashboard() {
  const auth = useDashboardAuth();
  if (!auth.session) throw new Error('Authenticated dashboard session is missing');
  return { ...auth, session: auth.session };
}
