import type { ChangeEvent, FormEvent } from 'react';
import type { CameraHealth, CameraStream, CameraStreamInput, StreamProtocol, RegistryCamera, RegistrySource, FleetHealth, ImportResult } from '../types';
import { errorMessage, errorStatus } from '../lib/errors';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Activity, ArrowLeft, Braces, Camera, Check, CircleAlert, CircleCheck, CloudDownload, Database,
  FilePenLine, Link2, LogOut, MapPin, Plus, RefreshCw, Search, SlidersHorizontal, Trash2, Upload, Wifi, X,
} from 'lucide-react';
import {
  createVendorCamera, deleteVendorCamera, getVendorCameras, getVendorFleetHealth, getVendorIdentity,
  getVendorCameraStreams, getVendorSources, importVendorCameras, logoutVendor, syncVendorSource, updateVendorCamera,
} from '../api';
import { clearVendorSession, readVendorSession } from '../vendorSession';

interface CameraForm {
  external_id: string; name: string; location: string; department: string; camera_type: string; ownership: string;
  streams: CameraStream[]; latitude: string | number; longitude: string | number; provenance: string;
}
const EMPTY_CAMERA: CameraForm = {
  external_id: '', name: '', location: '', department: '', camera_type: '', ownership: '',
  streams: [{ label: 'Main stream', protocol: 'rtsp', url: '', managed: false }],
  latitude: '', longitude: '', provenance: '',
};

const HEALTH_LABELS: Record<string, string> = {
  healthy: 'Frames received', pending: 'Confirming fault', degraded: 'Quality concern',
  unreachable: 'Unreachable', auth_failed: 'Authentication failed', decode_failed: 'Decode failed',
  stale: 'Measurement expired', unmonitored: 'Not checked yet', disabled: 'Monitoring disabled',
  unsupported: 'Protocol not supported', not_configured: 'No stream configured', probe_error: 'Monitor configuration issue',
};

const HEALTH_ATTENTION = new Set([
  'pending', 'degraded', 'unreachable', 'auth_failed', 'decode_failed',
  'unsupported', 'not_configured', 'probe_error', 'disabled',
]);

const IMPORT_EXAMPLE = JSON.stringify([{
  external_id: 'CAM-WEST-001',
  name: 'West gate camera',
  location: 'West entrance, Sector 8',
  department: 'Traffic',
  camera_type: 'Fixed',
  ownership: 'Gujarat Police',
  streams: [{ label: 'Main', protocol: 'rtsp', url: 'rtsp://10.0.0.15/live' }],
  coordinates: { latitude: 23.0225, longitude: 72.5714, provenance: 'Site survey' },
}], null, 2);

function effectiveHealthStatus(health: CameraHealth | undefined, now: number) {
  const expired = health?.expires_at && Date.parse(health.expires_at) <= now;
  return expired && health?.status !== 'disabled' ? 'stale' : health?.status || 'unmonitored';
}

function readableHealthValue(value: string | undefined) {
  return value ? value.replaceAll('_', ' ') : 'unknown';
}

function CameraHealthCell({ health, now }: { health: CameraHealth; now: number }) {
  const status = effectiveHealthStatus(health, now);
  const reasons = health?.reasons?.map(readableHealthValue).join(', ');
  const connectivity = status === 'stale' ? 'unknown' : readableHealthValue(health?.connectivity);
  const quality = status === 'stale' ? 'unknown' : readableHealthValue(health?.video_quality);
  return <td title={status === 'stale' ? 'A fresh measurement is needed.' : reasons}>
    <span className={`vendor-health-badge status-${status}`}><span />{HEALTH_LABELS[status] || readableHealthValue(status)}</span>
    <small>Link: {connectivity} · Quality: {quality}</small>
    <small>{health?.checked_at ? `Checked ${new Date(health.checked_at).toLocaleTimeString()}` : 'Awaiting background monitor'}</small>
    {reasons && status !== 'healthy' && <small className="vendor-health-reason">{reasons}</small>}
  </td>;
}

function CameraQualityCell({ health, rating, now }: { health: CameraHealth; rating?: number; now: number }) {
  const status = effectiveHealthStatus(health, now);
  const sharpness = health?.metrics?.sharpness;
  const hasMeasurement = status !== 'stale' && typeof sharpness === 'number' && Number.isFinite(sharpness);
  const suspectedBlur = health?.reasons?.includes('blur_suspected');
  if (!hasMeasurement) return <td className="vendor-quality-cell">
    <strong>Not rated</strong>
    <small>{status === 'stale' ? 'Measurement expired' : 'Awaiting decoded frames'}</small>
  </td>;
  return <td className="vendor-quality-cell">
    {rating ? <>
      <div className="vendor-clarity-rating" aria-label={`Relative clarity rating ${rating} out of 5`} title="Relative to fresh sharpness measurements from this vendor's visible cameras">
        <span className="vendor-clarity-bars" aria-hidden="true">{[1, 2, 3, 4, 5].map(level => <i key={level} className={level <= rating ? 'filled' : ''} />)}</span>
        <strong>{rating}/5</strong>
      </div>
      <small>Relative clarity · {Math.round(sharpness).toLocaleString()} sharpness</small>
    </> : <><strong>Measured</strong><small>{Math.round(sharpness).toLocaleString()} sharpness · more fleet samples needed</small></>}
    {suspectedBlur && <small className="vendor-quality-warning">Possible blur detected</small>}
  </td>;
}

function BulkImportSheet({ token, onClose, onImported }: { token: string; onClose: () => void; onImported: (result: ImportResult) => Promise<void> }) {
  const [jsonText, setJsonText] = useState('');
  const [preview, setPreview] = useState<ImportResult | null>(null);
  const [previewRows, setPreviewRows] = useState<unknown[] | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState('');

  function updateText(value: string) {
    setJsonText(value);
    setPreview(null);
    setPreviewRows(null);
    setError('');
  }

  function parseRows(): unknown[] {
    let parsed: unknown;
    try {
      parsed = JSON.parse(jsonText);
    } catch (parseError) {
      throw new Error(`Invalid JSON: ${errorMessage(parseError)}`);
    }
    const rows: unknown = Array.isArray(parsed) ? parsed : (typeof parsed === 'object' && parsed !== null && 'rows' in parsed ? parsed.rows : undefined);
    if (!Array.isArray(rows)) throw new Error('Paste a JSON array of cameras or an object with a rows array.');
    if (rows.length < 1 || rows.length > 1000) throw new Error('Import between 1 and 1,000 cameras at a time.');
    return rows;
  }

  async function previewImport() {
    setError('');
    setBusy('preview');
    try {
      const rows = parseRows();
      const result = await importVendorCameras(token, rows, true);
      setPreview(result);
      setPreviewRows(rows);
    } catch (requestError) {
      setPreview(null);
      setPreviewRows(null);
      setError(errorMessage(requestError));
    } finally {
      setBusy('');
    }
  }

  async function applyImport() {
    if (!previewRows) return;
    setError('');
    setBusy('apply');
    try {
      const result = await importVendorCameras(token, previewRows, false);
      await onImported(result);
    } catch (requestError) {
      setError(errorMessage(requestError));
    } finally {
      setBusy('');
    }
  }

  return <div className="vendor-sheet-backdrop" role="presentation" onMouseDown={event => event.target === event.currentTarget && onClose()}>
    <aside className="vendor-camera-sheet vendor-import-sheet" role="dialog" aria-modal="true" aria-labelledby="camera-import-title">
      <div className="vendor-sheet-header">
        <div><span className="vendor-eyebrow">Create-only bulk import</span><h2 id="camera-import-title">Import cameras from JSON</h2></div>
        <button type="button" className="vendor-icon-button" onClick={onClose} aria-label="Close JSON import"><X size={18} /></button>
      </div>
      <div className="vendor-import-copy">
        <p>Paste up to 1,000 camera records. Preview validates every record without saving. Applying creates new IDs and safely skips IDs already in your vendor camera collection.</p>
        <button type="button" className="vendor-example-button" onClick={() => updateText(IMPORT_EXAMPLE)}><Braces size={14} /> Load example JSON</button>
      </div>
      <label className="vendor-json-field">
        <span>Camera JSON *</span>
        <textarea value={jsonText} onChange={event => updateText(event.target.value)} placeholder={IMPORT_EXAMPLE} spellCheck="false" aria-describedby="camera-import-help" />
        <small id="camera-import-help">Required per camera: <code>external_id</code> and <code>name</code>. Streams, coordinates, department, type, ownership and infrastructure are optional.</small>
      </label>
      {error && <div className="vendor-form-error" role="alert">{error}</div>}
      {preview && <section className="vendor-import-preview" aria-live="polite">
        <div className="vendor-import-result"><span>Validated</span><strong>{preview.rows.length}</strong></div>
        <div className="vendor-import-result create"><span>Will create</span><strong>{preview.created}</strong></div>
        <div className="vendor-import-result skip"><span>Will skip</span><strong>{preview.skipped}</strong></div>
        <div className="vendor-import-preview-rows">
          {preview.rows.slice(0, 8).map(row => <div key={`${row.row}-${row.external_id}`}><code>{row.external_id}</code><span className={`vendor-import-action ${row.action}`}>{row.action === 'create' ? 'Create' : 'Skip existing'}</span></div>)}
          {preview.rows.length > 8 && <small>+ {preview.rows.length - 8} more validated records</small>}
        </div>
      </section>}
      <div className="vendor-sheet-actions">
        <button type="button" className="vendor-secondary-button" onClick={onClose}>Cancel</button>
        <button type="button" className="vendor-secondary-button" onClick={previewImport} disabled={!jsonText.trim() || Boolean(busy)}>{busy === 'preview' ? 'Validating…' : 'Preview import'}</button>
        <button type="button" className="vendor-primary-button" onClick={applyImport} disabled={!preview || Boolean(busy) || preview.created === 0}>{busy === 'apply' ? 'Importing…' : <><Upload size={15} /> Import {preview?.created || 0}</>}</button>
      </div>
    </aside>
  </div>;
}

function CameraEditor({ camera, onClose, onSaved, token }: { camera: RegistryCamera | 'new'; onClose: () => void; onSaved: (camera: RegistryCamera, isNew: boolean) => void; token: string }) {
  const isNew = camera === 'new';
  const [form, setForm] = useState<CameraForm>(() => isNew ? EMPTY_CAMERA : {
    external_id: camera.external_id,
    name: camera.name || '',
    location: camera.location || '',
    department: camera.department || '',
    camera_type: camera.camera_type || '',
    ownership: camera.ownership || '',
    streams: camera.streams || [],
    latitude: camera.coordinates?.latitude ?? '',
    longitude: camera.coordinates?.longitude ?? '',
    provenance: camera.coordinates?.provenance || '',
  });
  const [saving, setSaving] = useState(false);
  const [loadingStreams, setLoadingStreams] = useState(!isNew);
  const [error, setError] = useState('');

  useEffect(() => {
    if (isNew) return;
    let active = true;
    getVendorCameraStreams(token, camera.id)
      .then(result => active && setForm(current => ({ ...current, streams: result.streams || [] })))
      .catch(requestError => active && setError(`Could not load stream URLs: ${errorMessage(requestError)}`))
      .finally(() => active && setLoadingStreams(false));
    return () => { active = false; };
  }, [camera, isNew, token]);

  function field(name: Exclude<keyof CameraForm, 'streams'>) {
    return { value: form[name], onChange: (event: ChangeEvent<HTMLInputElement>) => setForm(current => ({ ...current, [name]: event.target.value })) };
  }

  function updateStream<K extends keyof CameraStreamInput>(index: number, key: K, value: CameraStreamInput[K]) {
    setForm(current => ({ ...current, streams: current.streams.map((stream, itemIndex) =>
      itemIndex === index ? { ...stream, [key]: value } : stream) }));
  }

  function addStream() {
    setForm(current => ({ ...current, streams: [...current.streams, {
      label: `Stream ${current.streams.length + 1}`, protocol: 'rtsp', url: '', managed: false,
    }] }));
  }

  function removeStream(index: number) {
    setForm(current => ({ ...current, streams: current.streams.filter((_, itemIndex) => itemIndex !== index) }));
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    const coordinateValues = [form.latitude, form.longitude, form.provenance];
    const hasAnyCoordinate = coordinateValues.some(value => String(value).trim() !== '');
    const hasAllCoordinates = coordinateValues.every(value => String(value).trim() !== '');
    if (hasAnyCoordinate && !hasAllCoordinates) {
      setError('Latitude, longitude and coordinate provenance must be supplied together.');
      return;
    }
    const editableStreams = form.streams.filter(stream => !stream.managed);
    const hasManagedStreams = form.streams.some(stream => stream.managed);
    if (!hasManagedStreams && editableStreams.length === 0) {
      setError('Add at least one live stream for this camera.');
      return;
    }
    if (editableStreams.some(stream => !stream.label.trim() || !stream.url.trim())) {
      setError('Every stream needs a label and URL.');
      return;
    }
    const metadata = {
      name: form.name,
      location: form.location || null,
      department: form.department || null,
      camera_type: form.camera_type || null,
      ownership: form.ownership || null,
      coordinates: hasAllCoordinates ? {
        latitude: Number(form.latitude), longitude: Number(form.longitude), provenance: form.provenance,
      } : null,
      streams: editableStreams.map(({ label, protocol, url }) => ({ label, protocol, url })),
    };
    setSaving(true);
    try {
      const saved = isNew
        ? await createVendorCamera(token, { ...metadata, external_id: form.external_id })
        : await updateVendorCamera(token, camera.id, camera.revision, metadata);
      onSaved(saved, isNew);
    } catch (requestError) {
      setError(errorStatus(requestError) === 412 ? 'This record changed in another session. Reload and try again.' : errorMessage(requestError));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="vendor-sheet-backdrop" role="presentation" onMouseDown={event => event.target === event.currentTarget && onClose()}>
      <aside className="vendor-camera-sheet" role="dialog" aria-modal="true" aria-labelledby="camera-editor-title">
        <div className="vendor-sheet-header">
          <div><span className="vendor-eyebrow">{isNew ? 'Camera registration' : camera.external_id}</span><h2 id="camera-editor-title">{isNew ? 'Add a camera' : 'Edit camera details'}</h2></div>
          <button type="button" className="vendor-icon-button" onClick={onClose} aria-label="Close camera editor"><X size={18} /></button>
        </div>
        <form className="vendor-camera-form" onSubmit={submit}>
          {isNew && <label><span>Camera ID *</span><input {...field('external_id')} required pattern="[A-Za-z0-9][A-Za-z0-9_.-]{0,199}" placeholder="CAM-WEST-001" /></label>}
          <label className={isNew ? '' : 'vendor-field-wide'}><span>Camera name *</span><input {...field('name')} required placeholder="West gate camera" /></label>
          <div className="vendor-form-divider vendor-field-wide"><Link2 size={15} /> Live streams</div>
          <div className="vendor-stream-list vendor-field-wide">
            {loadingStreams ? <div className="vendor-stream-loading"><RefreshCw size={15} className="spin" /> Loading configured streams…</div> : form.streams.map((stream, index) => (
              <div className={`vendor-stream-entry ${stream.managed ? 'managed' : ''}`} key={stream.id || `${index}-${stream.protocol}`}>
                <div className="vendor-stream-entry-head"><strong>{stream.managed ? 'Configured stream' : `Stream ${index + 1}`}</strong>{stream.managed ? <span><CloudDownload size={13} /> Synced</span> : <button type="button" onClick={() => removeStream(index)} aria-label={`Remove ${stream.label}`}><Trash2 size={14} /> Remove</button>}</div>
                <label><span>Label *</span><input value={stream.label} onChange={event => updateStream(index, 'label', event.target.value)} disabled={stream.managed} required={!stream.managed} placeholder="Main stream" /></label>
                <label><span>Protocol *</span><select value={stream.protocol} onChange={event => updateStream(index, 'protocol', event.target.value as StreamProtocol)} disabled={stream.managed}><option value="rtsp">RTSP</option><option value="rtsps">RTSPS</option><option value="hls">HLS</option><option value="whep">WebRTC / WHEP</option><option value="https">HTTPS</option><option value="http">HTTP</option></select></label>
                <label className="vendor-stream-url"><span>Stream URL *</span><input value={stream.url} onChange={event => updateStream(index, 'url', event.target.value)} readOnly={stream.managed} required={!stream.managed} placeholder="rtsp://camera-host/live/cam-01" spellCheck="false" /></label>
                {stream.managed && stream.auth && <small className="vendor-stream-auth">Authentication: {stream.auth.replaceAll('_', ' ')}</small>}
              </div>
            ))}
            {!loadingStreams && form.streams.length === 0 && <div className="vendor-stream-empty">No streams configured yet.</div>}
            {form.streams.filter(stream => !stream.managed).length < 12 && <button type="button" className="vendor-add-stream" onClick={addStream}><Plus size={15} /> Add another stream</button>}
          </div>
          <div className="vendor-form-divider vendor-field-wide"><Database size={15} /> Registry metadata</div>
          <label className="vendor-field-wide"><span>Location description</span><input {...field('location')} placeholder="West entrance, Sector 8" /></label>
          <label><span>Department</span><input {...field('department')} placeholder="Gujarat Police" /></label>
          <label><span>Camera type</span><input {...field('camera_type')} placeholder="Fixed / PTZ / ANPR" /></label>
          <label className="vendor-field-wide"><span>Ownership</span><input {...field('ownership')} placeholder="Department or institution" /></label>
          <div className="vendor-form-divider vendor-field-wide"><MapPin size={15} /> GIS coordinates</div>
          <label><span>Latitude</span><input {...field('latitude')} type="number" step="any" min="-90" max="90" placeholder="23.0225" /></label>
          <label><span>Longitude</span><input {...field('longitude')} type="number" step="any" min="-180" max="180" placeholder="72.5714" /></label>
          <label className="vendor-field-wide"><span>Coordinate provenance</span><input {...field('provenance')} placeholder="Site survey, municipal GIS, GPS reading…" /></label>
          {error && <div className="vendor-form-error vendor-field-wide" role="alert">{error}</div>}
          <div className="vendor-sheet-actions vendor-field-wide">
            <button type="button" className="vendor-secondary-button" onClick={onClose}>Cancel</button>
            <button type="submit" className="vendor-primary-button" disabled={saving || loadingStreams}>{saving ? 'Saving…' : isNew ? 'Add camera' : 'Save changes'} <Check size={16} /></button>
          </div>
        </form>
      </aside>
    </div>
  );
}

export default function VendorOnboarding() {
  const navigate = useNavigate();
  const [session] = useState(() => readVendorSession());
  const catalogueSyncStarted = useRef(false);
  const [catalogue, setCatalogue] = useState<RegistrySource | null>(null);
  const [cameras, setCameras] = useState<RegistryCamera[]>([]);
  const [cameraTotal, setCameraTotal] = useState(0);
  const [fleetHealth, setFleetHealth] = useState<FleetHealth>({ total: 0, counts: {} });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [action, setAction] = useState('');
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState('all');
  const [editor, setEditor] = useState<RegistryCamera | 'new' | null>(null);
  const [importerOpen, setImporterOpen] = useState(false);
  const [removingId, setRemovingId] = useState<string | null>(null);
  const [healthNow, setHealthNow] = useState(Date.now);
  const [healthRefreshError, setHealthRefreshError] = useState(false);

  const handleAuthError = useCallback((requestError: unknown) => {
    if (errorStatus(requestError) === 401) {
      clearVendorSession();
      navigate('/vendor/login', { replace: true });
      return true;
    }
    return false;
  }, [navigate]);

  const loadWorkspace = useCallback(async ({ refreshCatalogue = false } = {}) => {
    if (!session) {
      navigate('/vendor/login', { replace: true });
      return;
    }
    setLoading(true);
    setError('');
    try {
      const [, sourcePage, cameraPage, initialFleetHealth] = await Promise.all([
        getVendorIdentity(session.token), getVendorSources(session.token), getVendorCameras(session.token),
        getVendorFleetHealth(session.token),
      ]);
      const sentinelCatalogue = sourcePage.data.find(source => source.adapter === 'sentinel') || null;
      setCatalogue(sentinelCatalogue);
      let nextCameras = cameraPage.data;
      let nextCameraTotal = cameraPage.total;
      let nextFleetHealth = initialFleetHealth;
      const shouldSync = sentinelCatalogue && (refreshCatalogue || !catalogueSyncStarted.current);
      if (shouldSync) {
        catalogueSyncStarted.current = true;
        setAction('catalogue');
        try {
          const result = await syncVendorSource(session.token, sentinelCatalogue.id);
          const [refreshedCameras, refreshedFleetHealth] = await Promise.all([
            getVendorCameras(session.token), getVendorFleetHealth(session.token),
          ]);
          nextCameras = refreshedCameras.data;
          nextCameraTotal = refreshedCameras.total;
          nextFleetHealth = refreshedFleetHealth;
          if (refreshCatalogue) setNotice(`Camera catalogue refreshed: ${result.created} added and ${result.updated} updated.`);
        } catch (syncError) {
          setError(`The saved camera list is available, but catalogue refresh failed: ${errorMessage(syncError)}`);
        } finally {
          setAction('');
        }
      }
      setCameras(nextCameras);
      setCameraTotal(nextCameraTotal);
      setFleetHealth(nextFleetHealth);
    } catch (requestError) {
      if (!handleAuthError(requestError)) setError(errorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }, [handleAuthError, navigate, session]);

  useEffect(() => { loadWorkspace(); }, [loadWorkspace]);

  useEffect(() => {
    if (!session) return;
    let active = true;
    let pending = false;
    // One list request refreshes health for the visible inventory; no per-row requests.
    const timer = setInterval(async () => {
      if (pending || document.visibilityState === 'hidden') return;
      pending = true;
      try {
        const [page, currentFleetHealth] = await Promise.all([
          getVendorCameras(session.token), getVendorFleetHealth(session.token),
        ]);
        if (!active) return;
        const latest = new Map(page.data.map(camera => [camera.id, camera]));
        setCameras(current => current.map(camera => {
          const refreshed = latest.get(camera.id);
          return refreshed?.revision === camera.revision ? { ...camera, health: refreshed.health } : camera;
        }));
        setCameraTotal(page.total);
        setFleetHealth(currentFleetHealth);
        setHealthRefreshError(false);
      } catch (requestError) {
        if (active && !handleAuthError(requestError)) setHealthRefreshError(true);
      } finally {
        pending = false;
      }
    }, 30000);
    const clock = setInterval(() => setHealthNow(Date.now()), 5000);
    return () => { active = false; clearInterval(timer); clearInterval(clock); };
  }, [session, handleAuthError]);

  const stats = useMemo(() => cameras.reduce((result, camera) => {
    result.mapped += camera.coordinates ? 1 : 0;
    result.complete += camera.missing_metadata.length === 0 ? 1 : 0;
    result.connected += camera.stream?.configured ? 1 : 0;
    return result;
  }, { mapped: 0, complete: 0, connected: 0 }), [cameras]);
  const healthStats = useMemo(() => {
    const counts = fleetHealth?.counts || {};
    return {
      healthy: counts.healthy || 0,
      attention: [...HEALTH_ATTENTION].reduce((total, status) => total + (counts[status] || 0), 0),
      stale: counts.stale || 0,
      unmonitored: counts.unmonitored || 0,
    };
  }, [fleetHealth]);
  const filteredCameras = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return cameras.filter(camera => {
      const matchesQuery = !needle || `${camera.name} ${camera.external_id} ${camera.location || ''}`.toLowerCase().includes(needle);
      const matchesFilter = filter === 'all' || (filter === 'mapped' && camera.coordinates) ||
        (filter === 'missing-gis' && !camera.coordinates) || (filter === 'incomplete' && camera.missing_metadata.length > 0) ||
        (filter === 'stream-ready' && camera.stream?.configured) ||
        (filter === 'health-healthy' && effectiveHealthStatus(camera.health, healthNow) === 'healthy') ||
        (filter === 'health-attention' && HEALTH_ATTENTION.has(effectiveHealthStatus(camera.health, healthNow))) ||
        (filter === 'health-stale' && effectiveHealthStatus(camera.health, healthNow) === 'stale') ||
        (filter === 'health-unmonitored' && effectiveHealthStatus(camera.health, healthNow) === 'unmonitored');
      return matchesQuery && matchesFilter;
    });
  }, [cameras, filter, healthNow, query]);

  const clarityRatings = useMemo<Record<string, number>>(() => {
    const samples = cameras.flatMap(camera => {
      const sharpness = camera.health?.metrics?.sharpness;
      return effectiveHealthStatus(camera.health, healthNow) !== 'stale' && typeof sharpness === 'number' && Number.isFinite(sharpness)
        ? [{ id: camera.id, sharpness }]
        : [];
    }).sort((left, right) => left.sharpness - right.sharpness);
    if (samples.length < 5) return {};
    return Object.fromEntries(samples.map((sample, index) => [
      sample.id,
      Math.min(5, Math.floor(index * 5 / samples.length) + 1),
    ]));
  }, [cameras, healthNow]);

  async function signOut() {
    if (!session) return;
    setAction('logout');
    try { await logoutVendor(session.token); } catch { /* Clear local session even if the server is unavailable. */ }
    clearVendorSession();
    navigate('/vendor/login', { replace: true });
  }

  function cameraSaved(saved: RegistryCamera, isNew: boolean) {
    setCameras(current => isNew ? [...current, saved] : current.map(camera => camera.id === saved.id ? saved : camera));
    if (isNew) setCameraTotal(current => current + 1);
    setEditor(null);
    setNotice(isNew ? 'Camera added to your account.' : 'Camera details updated.');
  }

  async function camerasImported(result: ImportResult) {
    await loadWorkspace();
    setImporterOpen(false);
    setNotice(`JSON import complete: ${result.created} cameras created and ${result.skipped} existing IDs skipped.`);
  }

  async function removeCamera(camera: RegistryCamera) {
    if (!session) return;
    if (removingId !== camera.id) {
      setRemovingId(camera.id);
      return;
    }
    setAction(`remove-${camera.id}`);
    try {
      await deleteVendorCamera(session.token, camera.id);
      setCameras(current => current.filter(item => item.id !== camera.id));
      setCameraTotal(current => Math.max(0, current - 1));
      setNotice(`${camera.name} was removed from this vendor account.`);
    } catch (requestError) {
      if (!handleAuthError(requestError)) setError(errorMessage(requestError));
    } finally {
      setAction('');
      setRemovingId(null);
    }
  }

  if (!session) return null;

  return (
    <main className="vendor-portal vendor-workspace">
      <header className="vendor-workspace-header">
        <button className="vendor-wordmark" type="button" onClick={() => navigate('/dashboard')}><span className="vendor-mark"><Camera size={18} /></span><span><strong>SYNETRA</strong><small>VENDOR REGISTRY</small></span></button>
        <div className="vendor-header-context"><span className="vendor-api-status"><span /> Registry API online</span><span className="vendor-header-rule" /><span>{session.account.vendor_name}</span><button type="button" className="vendor-logout" onClick={signOut} disabled={action === 'logout'}><LogOut size={15} /> Sign out</button></div>
      </header>

      <div className="vendor-workspace-grid">
        <aside className="vendor-progress-rail">
          <button type="button" onClick={() => navigate('/dashboard')} className="vendor-back-link"><ArrowLeft size={14} /> Main dashboard</button>
          <div className="vendor-rail-label">Camera registration</div>
          <ol>
            <li className="done"><span><Check size={14} /></span><div><strong>Vendor verified</strong><small>{session.account.email}</small></div></li>
            <li className={cameras.length ? 'done' : 'active'}><span>{cameras.length ? <Check size={14} /> : '2'}</span><div><strong>Add cameras</strong><small>{cameras.length ? `${cameras.length} registered` : 'Add your first camera'}</small></div></li>
            <li className={cameras.length ? 'active' : ''}><span>3</span><div><strong>Complete details</strong><small>{cameras.length ? `${stats.complete} of ${cameras.length} complete` : 'Metadata and GIS'}</small></div></li>
          </ol>
          <div className="vendor-rail-foot"><Database size={15} /><span><strong>Standard output</strong><small>Every camera is available through Registry API v1.</small></span></div>
        </aside>

        <section className="vendor-workspace-content">
          <div className="vendor-page-heading">
            <div><span className="vendor-kicker"><span /> Vendor workspace</span><h1>Camera registry</h1><p>Add every camera your organisation operates, including its live stream endpoint, metadata and GIS position.</p></div>
            <div className="vendor-page-actions"><button className="vendor-secondary-button" type="button" onClick={() => setImporterOpen(true)}><Braces size={16} /> Import JSON</button><button className="vendor-primary-button" type="button" onClick={() => setEditor('new')}><Plus size={16} /> Add camera</button></div>
          </div>

          {error && <div className="vendor-alert error" role="alert"><CircleAlert size={17} /><span><strong>Action needed</strong>{error}</span></div>}
          {healthRefreshError && <div className="vendor-alert error" role="status"><CircleAlert size={17} /><span>Health refresh unavailable. Measurements expire automatically until the registry reconnects.</span></div>}
          {notice && <div className="vendor-alert success" role="status"><CircleCheck size={17} /><span><strong>Done</strong>{notice}</span><button type="button" onClick={() => setNotice('')} aria-label="Dismiss"><X size={15} /></button></div>}

          {catalogue && <section className="vendor-catalogue-note"><span className="vendor-source-icon"><CloudDownload size={19} /></span><div><span className="vendor-eyebrow">Automatic catalogue</span><strong>Your registered cameras refresh automatically when this account signs in.</strong><small>The same list below can still include cameras you add yourself.</small></div><button type="button" className="vendor-secondary-button" onClick={() => loadWorkspace({ refreshCatalogue: true })} disabled={action === 'catalogue'}><RefreshCw size={15} className={action === 'catalogue' ? 'spin' : ''} /> {action === 'catalogue' ? 'Refreshing…' : 'Refresh now'}</button></section>}

          <section className="vendor-stat-row" aria-label="Camera registry summary">
            <div><span>Total cameras</span><strong>{cameraTotal}</strong><small>in this vendor account</small></div>
            <div><span>Streams configured</span><strong>{stats.connected}</strong><small>{cameras.length - stats.connected} endpoints pending</small></div>
            <div><span>GIS mapped</span><strong>{stats.mapped}</strong><small>{cameras.length - stats.mapped} coordinates pending</small></div>
            <div><span>Metadata complete</span><strong>{stats.complete}</strong><small>{cameras.length - stats.complete} records need work</small></div>
          </section>

          <section className="vendor-health-panel" aria-labelledby="vendor-health-title">
            <div className="vendor-health-heading"><div><span className="vendor-section-number">LIVE STATUS</span><h2 id="vendor-health-title"><Activity size={20} /> Camera health</h2></div><small>{fleetHealth?.checked_at ? `Updated ${new Date(fleetHealth.checked_at).toLocaleTimeString()}` : 'Waiting for registry health'}</small></div>
            <div className="vendor-health-grid">
              <button type="button" className="healthy" onClick={() => setFilter('health-healthy')}><span>Healthy</span><strong>{healthStats.healthy}</strong><small>fresh frames received</small></button>
              <button type="button" className="attention" onClick={() => setFilter('health-attention')}><span>Needs attention</span><strong>{healthStats.attention}</strong><small>faults or quality concerns</small></button>
              <button type="button" className="stale" onClick={() => setFilter('health-stale')}><span>Stale</span><strong>{healthStats.stale}</strong><small>measurement expired</small></button>
              <button type="button" className="unmonitored" onClick={() => setFilter('health-unmonitored')}><span>Not monitored</span><strong>{healthStats.unmonitored}</strong><small>awaiting first probe</small></button>
            </div>
          </section>

          <section className="vendor-camera-register">
            <div className="vendor-register-heading">
              <div><span className="vendor-section-number">CAMERAS / {cameraTotal}</span><h2>Your camera inventory</h2>{cameraTotal > cameras.length && <small className="vendor-inventory-limit">Showing the first {cameras.length} records. Use the Registry API for the full inventory.</small>}</div>
              <div className="vendor-register-tools">
                <label className="vendor-search"><Search size={15} /><input value={query} onChange={event => setQuery(event.target.value)} placeholder="Search name, ID or location" aria-label="Search cameras" /></label>
                <label className="vendor-filter"><SlidersHorizontal size={15} /><select value={filter} onChange={event => setFilter(event.target.value)} aria-label="Filter camera records"><option value="all">All cameras</option><optgroup label="Health"><option value="health-healthy">Healthy</option><option value="health-attention">Needs attention</option><option value="health-stale">Stale measurements</option><option value="health-unmonitored">Not monitored</option></optgroup><optgroup label="Registration"><option value="stream-ready">Stream ready</option><option value="missing-gis">Missing GIS</option><option value="mapped">GIS mapped</option><option value="incomplete">Incomplete metadata</option></optgroup></select></label>
              </div>
            </div>
            {loading ? <div className="vendor-loading"><RefreshCw size={22} className="spin" /><span>{action === 'catalogue' ? 'Refreshing camera catalogue…' : 'Reading camera registry…'}</span></div> : filteredCameras.length ? (
              <div className="vendor-table-wrap"><table className="vendor-camera-table">
                <thead><tr><th>Camera</th><th>Location / department</th><th>Stream</th><th>Camera health</th><th>Image quality</th><th>GIS</th><th>Metadata</th><th><span className="sr-only">Actions</span></th></tr></thead>
                <tbody>{filteredCameras.map(camera => <tr key={camera.id}>
                  <td><span className="vendor-camera-name"><Camera size={15} />{camera.name}</span><code>{camera.external_id}</code></td>
                  <td><strong>{camera.location || 'Location pending'}</strong><small>{camera.department || 'Department pending'}</small></td>
                  <td>{camera.stream?.configured ? <><span className="vendor-positive"><Wifi size={14} /> {camera.stream.count} {camera.stream.count === 1 ? 'stream' : 'streams'}</span><small>{camera.stream.protocols?.map(protocol => protocol.toUpperCase()).join(' · ')}</small></> : <span className="vendor-pending">Missing URL</span>}</td>
                  <CameraHealthCell health={camera.health} now={healthNow} />
                  <CameraQualityCell health={camera.health} rating={clarityRatings[camera.id]} now={healthNow} />
                  <td>{camera.coordinates ? <span className="vendor-positive"><MapPin size={14} /> Mapped</span> : <span className="vendor-pending">Missing</span>}</td>
                  <td><strong>{camera.missing_metadata.length ? `${camera.missing_metadata.length} missing` : 'Complete'}</strong><small>{camera.missing_metadata.length ? camera.missing_metadata.slice(0, 2).join(', ') : 'Ready for use'}</small></td>
                  <td><div className="vendor-row-actions"><button type="button" className="vendor-edit-button" onClick={() => { setRemovingId(null); setEditor(camera); }}><FilePenLine size={15} /> Edit</button><button type="button" className={`vendor-remove-button ${removingId === camera.id ? 'confirm' : ''}`} onClick={() => removeCamera(camera)} disabled={action === `remove-${camera.id}`}><Trash2 size={14} /> {removingId === camera.id ? 'Confirm' : 'Remove'}</button></div></td>
                </tr>)}</tbody>
              </table></div>
            ) : <div className="vendor-empty-state"><Camera size={24} /><h3>{cameras.length ? 'No cameras match this view' : 'Add your first camera'}</h3><p>{cameras.length ? 'Change the search or filter to see other records.' : 'Register the stream URL, camera details and GIS position directly in your vendor account.'}</p>{!cameras.length && <button type="button" className="vendor-primary-button" onClick={() => setEditor('new')}><Plus size={16} /> Add camera</button>}</div>}
          </section>
        </section>
      </div>
      {editor && <CameraEditor camera={editor} token={session.token} onClose={() => setEditor(null)} onSaved={cameraSaved} />}
      {importerOpen && <BulkImportSheet token={session.token} onClose={() => setImporterOpen(false)} onImported={camerasImported} />}
    </main>
  );
}
