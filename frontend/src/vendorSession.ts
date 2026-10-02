import type { VendorAccount, LoginResponse } from './types';
import { isVendorAccount, readSession, saveSession } from './lib/session';
const SESSION_KEY = 'synetra.vendor.session.v1';

export function readVendorSession() {
  return readSession(SESSION_KEY, isVendorAccount);
}
export function saveVendorSession(result: LoginResponse<VendorAccount>) {
  return saveSession(SESSION_KEY, result);
}
export function clearVendorSession() {
  sessionStorage.removeItem(SESSION_KEY);
}
