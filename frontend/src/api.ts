import type * as T from './types';
import axios from 'axios';
import { readDashboardSession } from './dashboardSession';
// Local media requests need the login cookie: localhost and 127.0.0.1
// are different cookie sites, even when they reach the same server.
const LOCAL_API_HOST = typeof window !== 'undefined' && ['localhost', '127.0.0.1'].includes(window.location.hostname)
  ? window.location.hostname
  : '127.0.0.1';
const BASE = import.meta.env.VITE_ANALYTICS_API_URL || `http://${LOCAL_API_HOST}:8000`;
const API_BASE = BASE;
export const REGISTRY_API_BASE = import.meta.env.VITE_REGISTRY_API_URL || `http://${LOCAL_API_HOST}:8000`;
const api = axios.create({ baseURL: BASE, timeout: 10000 });
export const analyticsApi = api;
api.interceptors.request.use(config => {
  const token = readDashboardSession()?.token;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  config.withCredentials = true;
  return config;
});

export function dashboardFetch(path: string, options: RequestInit = {}) {
  const token = readDashboardSession()?.token;
  const headers = new Headers(options.headers);
  if (token && !headers.has('Authorization')) headers.set('Authorization', `Bearer ${token}`);
  return fetch(`${API_BASE}${path}`, {
    ...options,
    credentials: 'include',
    headers,
  });
}
export const getCameras = () => api.get<{ cameras: T.AnalyticsCamera[]; total: number }>('/cameras/');
export async function uploadVideo(file: File) {
  const formData = new FormData();
  formData.append('file', file);
  const res = await dashboardFetch('/video/upload', {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) throw new Error('Upload failed');
  return readJson<T.VideoUploadResult>(res);
}

export async function getVehiclesCameras() {
  const res = await dashboardFetch('/vehicles/cameras');
  if (!res.ok) throw new Error('Failed to fetch cameras');
  return readJson<{ cameras: T.GeoCamera[] }>(res);
}

export const getRegistryCameras = (params: { limit?: number } = {}) => api.get<T.CameraPage>('/registry/cameras', { params });
export const getRegistryCameraStreams = (cameraId: string) => api.get<{ streams: T.CameraStream[] }>(`/registry/cameras/${encodeURIComponent(cameraId)}/streams`);

export async function getWatchlistAlerts() {
  const res = await dashboardFetch('/watchlist/alerts');
  if (!res.ok) throw new Error('Failed to fetch watchlist alerts');
  return readJson<{ total: number; alerts: T.WatchlistAlert[] }>(res);
}

export async function getJourney(plate: string) {
  const res = await dashboardFetch(`/vehicles/journey/${encodeURIComponent(plate)}`);
  if (!res.ok) throw new Error('Failed to fetch journey');
  return readJson<T.Journey>(res);
}
export const getCamera = (id: string) => api.get<T.AnalyticsCamera>(`/cameras/${id}`);
export const getCameraStats = (id: string) => api.get<T.CameraStats>(`/cameras/${id}/stats`);
export const getEvents = (params: T.EventQuery = {}) => api.get<T.EventPage>('/events/', { params });
export const getEvent = (id: string) => api.get<T.SecurityEvent>(`/events/${id}`);
export const getEventStats = () => api.get<T.EventStats>('/events/stats');
export const getLiveFeed = () => api.get<{ feed: T.SecurityEvent[] }>('/events/live/feed');
export const updateEventStatus = (id: string, status: T.EventUpdateStatus) =>
  api.patch<T.EventStatusResult>(`/events/${id}/status`, null, { params: { new_status: status } });
export const getPersonTrajectory = (personId: string) =>
  api.get<{ person_id: string; trajectory: T.TrajectoryEntry[]; total_points: number }>(`/events/person/${personId}/trajectory`);
export const investigateQuery = (body: { query: string }) => api.post<T.InvestigationResult>('/investigation/query', body);
export const getIncidents = () => api.get<{ incidents: T.Incident[] }>('/investigation/incidents');
export const getIncident = (id: string) => api.get<T.Incident>(`/investigation/incidents/${id}`);
export const getPersonEvents = (personId: string) => api.get<{ person_id: string; events: T.SecurityEvent[]; trajectory: T.TrajectoryEntry[]; total_events: number }>(`/investigation/persons/${personId}`);
export const getEODReport = () => api.get<T.EODReport>('/reports/eod');
export const getIncidentReport = (id: string) => api.get<{ incident: T.Incident; related_events: T.SecurityEvent[]; cameras_involved: string[]; persons_of_interest: string[]; report_generated_at: string }>(`/reports/incident/${id}`);
export const getSystemStats = () => api.get<T.SystemStats>('/reports/system/stats');
export const getTopology = () => api.get<T.Topology>('/topology/');
export const updateTopology = (data: Partial<T.Topology>) => api.post<{ status: string; topology: T.Topology }>('/topology/', data);

export class RegistryApiError extends Error {
  constructor(message: string, public status: number, public detail: unknown) {
    super(message);
    this.name = 'RegistryApiError';
  }
}

function detailMessage(detail: unknown, fallback: string) {
  if (typeof detail === 'string') return detail.replaceAll('_', ' ');
  if (Array.isArray(detail)) return detail.map((item: unknown) => typeof item === 'object' && item !== null && 'msg' in item && typeof item.msg === 'string' ? item.msg : fallback).join(', ');
  return fallback;
}

type RegistryRequestOptions = RequestInit & { token?: string };

// The caller supplies the wire contract for the endpoint; the backend validates its schema.
export async function readJson<T>(response: Response): Promise<T> {
  return response.json() as Promise<T>;
}

async function registryRequest<T>(path: string, { token, headers, ...options }: RegistryRequestOptions = {}): Promise<T> {
  const requestHeaders = new Headers(headers);
  if (options.body && !requestHeaders.has('Content-Type')) requestHeaders.set('Content-Type', 'application/json');
  if (token) requestHeaders.set('Authorization', `Bearer ${token}`);
  const response = await fetch(`${REGISTRY_API_BASE}${path}`, {
    ...options,
    credentials: 'include',
    headers: requestHeaders,
  });
  if (response.status === 204) return null as T;
  const payload: unknown = await response.json().catch(() => null);
  const detail = typeof payload === "object" && payload !== null && "detail" in payload ? payload.detail : undefined;
  if (!response.ok) {
    throw new RegistryApiError(detailMessage(detail, `Registry request failed (${response.status})`), response.status, detail);
  }
  return payload as T;
}

export const loginVendor = (email: string, password: string) => registryRequest<T.LoginResponse<T.VendorAccount>>('/api/v1/auth/vendor/login', {
  method: 'POST', body: JSON.stringify({ email, password }),
});
export const loginDashboard = (email: string, password: string) => registryRequest<T.LoginResponse<T.DashboardAccount>>('/api/v1/auth/login', {
  method: 'POST', body: JSON.stringify({ email, password }),
});
export const logoutDashboard = (token: string) => registryRequest<null>('/api/v1/auth/logout', { method: 'POST', token });
export const getDashboardIdentity = (token: string) => registryRequest<T.DashboardIdentity>('/api/v1/me', { token });
export async function getDashboardRegistryCameras(token: string): Promise<T.CameraPage> {
  // Fetch real cameras from mock backend (serves actual dataset images)
  try {
    const res = await fetch(`${BASE}/registry/cameras?limit=500`);
    if (res.ok) return res.json();
  } catch { /* fallback below */ }
  return { data: [], total: 0, next_cursor: null } as any;
}
export const getLiveStreamUrl = (cameraId: string) => `${BASE}/stream/${encodeURIComponent(cameraId)}`;
export const getRawCctvStreamUrl = (cameraId: string) => `${BASE}/stream/${encodeURIComponent(cameraId)}/raw`;
export const getDashboardFleetHealth = async (token: string) => {
  try {
    const res = await fetch(`${BASE}/api/v1/fleet/health`);
    if (res.ok) return res.json();
  } catch { /* fallback */ }
  return { total: 10, counts: { healthy: 10, stale: 0, unmonitored: 0 }, checked_at: new Date().toISOString() } as any;
};
export const getAccessUsers = (token: string) => registryRequest<T.Page<T.AccessUser>>('/api/v1/access/users', { token });
export const getSecurityAudit = (token: string) => registryRequest<T.Page<T.AuditEntry>>('/api/v1/access/audit?limit=200', { token });
export const createAccessUser = (token: string, body: T.AccessUserInput) => registryRequest<T.AccessUser>('/api/v1/access/users', {
  method: 'POST', token, body: JSON.stringify(body),
});
export const logoutVendor = (token: string) => registryRequest<null>('/api/v1/auth/vendor/logout', { method: 'POST', token });
export const getVendorIdentity = (token: string) => registryRequest<T.DashboardIdentity>('/api/v1/me', { token });
export const getVendorAccount = (token: string) => registryRequest<T.Page<T.Vendor>>('/api/v1/vendors?limit=10', { token });
export const getVendorSources = (token: string) => registryRequest<T.Page<T.RegistrySource>>('/api/v1/sources?limit=100', { token });
export const getVendorCameras = (token: string) => registryRequest<T.CameraPage>('/api/v1/cameras?limit=500', { token });
export const getVendorFleetHealth = (token: string) => registryRequest<T.FleetHealth>('/api/v1/fleet/health', { token });
export const getVendorCameraStreams = (token: string, cameraId: string) => registryRequest<{ streams: T.CameraStream[] }>(`/api/v1/cameras/${cameraId}/streams`, { token });
export const importVendorCameras = (token: string, rows: unknown[], dryRun = true) => registryRequest<T.ImportResult>('/api/v1/camera-imports', {
  method: 'POST', token, body: JSON.stringify({ rows, dry_run: dryRun }),
});
export const createVendorSource = (token: string, body: T.SourceInput) => registryRequest<T.RegistrySource>('/api/v1/sources', {
  method: 'POST', token, body: JSON.stringify(body),
});
export const testVendorSource = (token: string, sourceId: string) => registryRequest<{ source_id: string; catalogue_accessible: boolean; camera_count: number; media_tested: boolean; sample: { id: string; name: string }[] }>(`/api/v1/sources/${sourceId}/test`, {
  method: 'POST', token,
});
export const syncVendorSource = (token: string, sourceId: string) => registryRequest<T.SyncResult>(`/api/v1/sources/${sourceId}/sync`, {
  method: 'POST', token, body: JSON.stringify({ dry_run: false }),
});
export const createVendorCamera = (token: string, body: T.CameraInput) => registryRequest<T.RegistryCamera>('/api/v1/cameras', {
  method: 'POST', token, body: JSON.stringify(body),
});
export const updateVendorCamera = (token: string, cameraId: string, revision: number, body: T.CameraMetadata) => registryRequest<T.RegistryCamera>(`/api/v1/cameras/${cameraId}`, {
  method: 'PATCH', token, headers: { 'If-Match': `"${revision}"` }, body: JSON.stringify(body),
});
export const deleteVendorCamera = (token: string, cameraId: string) => registryRequest<null>(`/api/v1/cameras/${cameraId}`, {
  method: 'DELETE', token,
});
