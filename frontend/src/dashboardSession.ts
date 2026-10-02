import type { DashboardAccount, LoginResponse } from './types';
import { isDashboardAccount, readSession, saveSession } from './lib/session';
const SESSION_KEY = 'synetra.dashboard.session.v1';

export function readDashboardSession() {
  return readSession(SESSION_KEY, isDashboardAccount);
}
export function saveDashboardSession(result: LoginResponse<DashboardAccount>) {
  return saveSession(SESSION_KEY, result);
}
export function clearDashboardSession() {
  sessionStorage.removeItem(SESSION_KEY);
}
