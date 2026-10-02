import { beforeEach, describe, expect, it, vi } from 'vitest';
import { clearDashboardSession, readDashboardSession, saveDashboardSession } from '../dashboardSession';
import { readVendorSession, saveVendorSession } from '../vendorSession';
import type { DashboardAccount, VendorAccount } from '../types';

const dashboard: DashboardAccount = {
  id: 'user-1', email: 'user@example.test', display_name: 'Test user', roles: ['investigator'],
  permissions: ['dashboard.access', 'event.read'], scopes: [{ type: 'global', id: null }], landing_path: '/dashboard',
};
const vendor: VendorAccount = {
  id: 'vendor-user-1', vendor_id: 'vendor-1', vendor_name: 'Test vendor', email: 'vendor@example.test', display_name: 'Vendor user',
};
const key = 'synetra.dashboard.session.v1';
let storage: Map<string, string>;
beforeEach(() => {
  storage = new Map();
  vi.stubGlobal('sessionStorage', {
    getItem: (name: string) => storage.get(name) ?? null,
    setItem: (name: string, value: string) => storage.set(name, value),
    removeItem: (name: string) => storage.delete(name),
  });
});

function validSession() {
  return { token: 'test-token', expiresAt: new Date(Date.now() + 60_000).toISOString(), account: dashboard };
}

describe('dashboard session storage', () => {
  it('round-trips login responses using the existing storage key', () => {
    const saved = saveDashboardSession({ access_token: 'test-token', expires_at: validSession().expiresAt, token_type: 'bearer', account: dashboard });
    expect(readDashboardSession()).toEqual(saved);
    expect(storage.has(key)).toBe(true);
    clearDashboardSession();
    expect(readDashboardSession()).toBeNull();
  });

  it.each([
    ['expired', () => ({ ...validSession(), expiresAt: '2000-01-01T00:00:00Z' })],
    ['invalid expiration', () => ({ ...validSession(), expiresAt: 'not-a-date' })],
    ['missing account', () => ({ ...validSession(), account: null })],
    ['malformed permissions', () => ({ ...validSession(), account: { ...dashboard, permissions: 'event.read' } })],
    ['invalid role', () => ({ ...validSession(), account: { ...dashboard, roles: ['not-a-role'] } })],
    ['empty token', () => ({ ...validSession(), token: '' })],
  ])('discards a %s session', (_label, makeSession) => {
    storage.set(key, JSON.stringify(makeSession()));
    expect(readDashboardSession()).toBeNull();
    expect(storage.has(key)).toBe(false);
  });

  it('discards malformed JSON', () => {
    storage.set(key, '{');
    expect(readDashboardSession()).toBeNull();
    expect(storage.has(key)).toBe(false);
  });

  it('treats blocked browser storage as signed out', () => {
    vi.stubGlobal('sessionStorage', {
      getItem() { throw new Error('Storage blocked'); },
      removeItem() { throw new Error('Storage blocked'); },
    });
    expect(readDashboardSession()).toBeNull();
  });
});

it('keeps vendor sessions separate from dashboard sessions', () => {
  const saved = saveVendorSession({ access_token: 'vendor-token', expires_at: validSession().expiresAt, token_type: 'bearer', account: vendor });
  expect(readVendorSession()).toEqual(saved);
  expect(readDashboardSession()).toBeNull();
});
