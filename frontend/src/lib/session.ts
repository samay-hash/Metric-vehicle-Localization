import type { DashboardAccount, LoginResponse, Session, VendorAccount } from '../types';
function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null;
}
function isStringArray(value: unknown): value is string[] {
    return Array.isArray(value) && value.every(item => typeof item === 'string');
}
export function isDashboardAccount(value: unknown): value is DashboardAccount {
    return isRecord(value) && typeof value.id === 'string' && typeof value.email === 'string'
        && typeof value.display_name === 'string' && typeof value.landing_path === 'string'
        && isStringArray(value.permissions) && isStringArray(value.roles)
        && value.roles.every(role => ['master_admin', 'investigator', 'maintenance', 'it_operator'].includes(role))
        && Array.isArray(value.scopes) && value.scopes.every((scope: unknown) => isRecord(scope)
        && typeof scope.type === 'string' && ['global', 'state', 'district', 'commissionerate', 'zone', 'police_station', 'department', 'vendor'].includes(scope.type)
        && (scope.id === null || typeof scope.id === 'string'));
}
export function isVendorAccount(value: unknown): value is VendorAccount {
    return isRecord(value) && ['id', 'vendor_id', 'vendor_name', 'email', 'display_name'].every(key => typeof value[key] === 'string');
}
export function readSession<T>(key: string, isAccount: (value: unknown) => value is T): Session<T> | null {
    try {
        const value: unknown = JSON.parse(sessionStorage.getItem(key) ?? 'null');
        if (isRecord(value) && typeof value.token === 'string' && value.token.length > 0
            && typeof value.expiresAt === 'string' && Number.isFinite(Date.parse(value.expiresAt))
            && Date.parse(value.expiresAt) > Date.now() && isAccount(value.account)) {
            return { token: value.token, expiresAt: value.expiresAt, account: value.account };
        }
    }
    catch { /* Invalid or unavailable storage is treated as a signed-out session. */ }
    try {
        sessionStorage.removeItem(key);
    }
    catch { /* Storage may be unavailable. */ }
    return null;
}
export function saveSession<T>(key: string, result: LoginResponse<T>): Session<T> {
    const session = { token: result.access_token, expiresAt: result.expires_at, account: result.account };
    sessionStorage.setItem(key, JSON.stringify(session));
    return session;
}
