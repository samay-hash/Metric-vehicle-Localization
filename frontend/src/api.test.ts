import { beforeEach, expect, it, vi } from 'vitest';
import { dashboardFetch, getDashboardRegistryCameras, deleteVendorCamera, getVendorCameras, loginDashboard, RegistryApiError, updateVendorCamera } from './api';
import { readDashboardSession } from './dashboardSession';

vi.mock('./dashboardSession', () => ({ readDashboardSession: vi.fn() }));
const fetchMock = vi.fn<typeof fetch>();
beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock);
  vi.mocked(readDashboardSession).mockReturnValue(null);
});

it('preserves Headers input and includes dashboard credentials', async () => {
  vi.mocked(readDashboardSession).mockReturnValue({
    token: 'dashboard-token', expiresAt: '2099-01-01T00:00:00Z',
    account: { id: '1', email: 'user@example.test', display_name: 'User', roles: ['investigator'], permissions: [], scopes: [], landing_path: '/dashboard' },
  });
  fetchMock.mockResolvedValue(new Response('{}'));
  await dashboardFetch('/events/', { headers: new Headers({ 'X-Request-ID': 'test' }) });
  const [url, options] = fetchMock.mock.calls[0];
  expect(url).toBe('http://127.0.0.1:8000/events/');
  expect(options?.credentials).toBe('include');
  const headers = new Headers(options?.headers);
  expect(headers.get('Authorization')).toBe('Bearer dashboard-token');
  expect(headers.get('X-Request-ID')).toBe('test');
});

it('does not add an authorization header when signed out', async () => {
  fetchMock.mockResolvedValue(new Response('{}'));
  await dashboardFetch('/events/');
  expect(new Headers(fetchMock.mock.calls[0][1]?.headers).has('Authorization')).toBe(false);
});

it('returns registry JSON and sends the vendor bearer token', async () => {
  const page = { data: [], total: 0, next_cursor: null };
  fetchMock.mockResolvedValue(Response.json(page));
  expect(await getVendorCameras('vendor-token')).toEqual(page);
  const headers = new Headers(fetchMock.mock.calls[0][1]?.headers);
  expect(headers.get('Authorization')).toBe('Bearer vendor-token');
});

it('preserves optimistic concurrency and JSON request bodies for camera edits', async () => {
  fetchMock.mockResolvedValue(Response.json({ id: 'camera-1' }));
  await updateVendorCamera('vendor-token', 'camera-1', 7, { name: 'West gate' });
  const [, options] = fetchMock.mock.calls[0];
  expect(options?.method).toBe('PATCH');
  expect(options?.body).toBe(JSON.stringify({ name: 'West gate' }));
  const headers = new Headers(options?.headers);
  expect(headers.get('If-Match')).toBe('"7"');
  expect(headers.get('Content-Type')).toBe('application/json');
});

it('handles successful empty delete responses', async () => {
  fetchMock.mockResolvedValue(new Response(null, { status: 204 }));
  expect(await deleteVendorCamera('vendor-token', 'camera-1')).toBeNull();
});

it('keeps validation details and HTTP status in registry errors', async () => {
  const detail = [{ loc: ['body', 'email'], msg: 'Invalid email', type: 'value_error' }];
  fetchMock.mockResolvedValue(Response.json({ detail }, { status: 422 }));
  const request = loginDashboard('invalid', 'password');
  await expect(request).rejects.toBeInstanceOf(RegistryApiError);
  await expect(request).rejects.toMatchObject({ message: 'Invalid email', status: 422, detail });
});

it('reports a useful error when the registry sends a non-JSON failure', async () => {
  fetchMock.mockResolvedValue(new Response('Service unavailable', { status: 503 }));
  await expect(getVendorCameras('vendor-token')).rejects.toMatchObject({ message: 'Registry request failed (503)', status: 503 });
});


it('loads every page of scoped dashboard cameras with the same credentials', async () => {
  fetchMock.mockResolvedValueOnce(Response.json({ data: [{ id: 'camera-a' }], total: 2, next_cursor: 'cursor-a' }));
  fetchMock.mockResolvedValueOnce(Response.json({ data: [{ id: 'camera-b' }], total: 2, next_cursor: null }));
  expect(await getDashboardRegistryCameras('dashboard-token')).toEqual({
    data: [{ id: 'camera-a' }, { id: 'camera-b' }], total: 2, next_cursor: null,
  });
  expect(String(fetchMock.mock.calls[1][0])).toContain('/api/v1/cameras?limit=500&after=cursor-a');
  for (const [, options] of fetchMock.mock.calls) {
    expect(new Headers(options?.headers).get('Authorization')).toBe('Bearer dashboard-token');
  }
});

it('rejects an incomplete camera inventory if a later page fails', async () => {
  fetchMock.mockResolvedValueOnce(Response.json({ data: [{ id: 'camera-a' }], total: 2, next_cursor: 'cursor-a' }));
  fetchMock.mockResolvedValueOnce(Response.json({ detail: 'Unavailable' }, { status: 503 }));
  await expect(getDashboardRegistryCameras('dashboard-token')).rejects.toMatchObject({ status: 503 });
});
