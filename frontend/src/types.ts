/** Wire contracts shared by the API clients and dashboard pages. */
export type Severity = 'critical' | 'high' | 'medium' | 'low';
export type EventUpdateStatus = 'pending_review' | 'under_investigation' | 'resolved' | 'escalated' | 'false_positive';
export type EventStatus = EventUpdateStatus | 'open' | 'alert';
export type SystemRole = 'master_admin' | 'investigator' | 'maintenance' | 'it_operator';
export type ScopeType = 'global' | 'state' | 'district' | 'commissionerate' | 'zone' | 'police_station' | 'department' | 'vendor';
export type Permission = 'source.read' | 'dashboard.access' | 'camera.stream.view' | 'event.read' | 'investigation.run' | 'incident.read' | 'report.read' | 'evidence.upload' | 'topology.read' | 'maintenance.manage' | 'system.read' | 'user.manage' | 'audit.read';
export interface DashboardAccount {
    id: string;
    email: string;
    display_name: string;
    roles: SystemRole[];
    permissions: string[];
    scopes: {
        type: ScopeType;
        id: string | null;
    }[];
    landing_path: string;
}
export interface DashboardIdentity {
    actor: string;
    permissions: string[];
    roles: string[];
    landing_path: string;
    display_name?: string;
    email?: string;
}
export interface VendorAccount {
    id: string;
    vendor_id: string;
    vendor_name: string;
    email: string;
    display_name: string;
}
export interface LoginResponse<T> {
    access_token: string;
    expires_at: string;
    token_type: 'bearer';
    account: T;
}
export interface Session<T> {
    token: string;
    expiresAt: string;
    account: T;
}
export type DashboardSession = Session<DashboardAccount>;
export type VendorSession = Session<VendorAccount>;
export interface RoleAssignment {
    id: string;
    role: SystemRole;
    scope_type: ScopeType;
    scope_id: string | null;
}
export interface AccessUser {
    id: string;
    display_name: string;
    email: string;
    active: boolean;
    roles: SystemRole[];
    assignments: RoleAssignment[];
}
export interface AccessUserInput {
    email: string;
    display_name: string;
    password: string;
    assignments: Omit<RoleAssignment, 'id'>[];
}
export interface AuditEntry {
    id: string;
    created_at: string;
    actor: string;
    action: string;
    target_id: string | null;
    details: Record<string, unknown>;
}
export interface Page<T> {
    data: T[];
    next_cursor: string | null;
    total?: number | null;
}
export interface CameraPage extends Page<RegistryCamera> {
    total: number;
}
export type StreamProtocol = 'rtsp' | 'rtsps' | 'hls' | 'whep' | 'http' | 'https';
export interface CameraStreamInput {
    label: string;
    protocol: StreamProtocol;
    url: string;
}
export interface CameraStream extends CameraStreamInput {
    id?: string | null;
    managed?: boolean;
    auth?: string;
}
export interface Coordinates {
    latitude: number;
    longitude: number;
    provenance: string;
}
export interface CameraHealth {
    status: string;
    freshness: 'fresh' | 'stale' | 'never_checked';
    connectivity: string;
    video_quality: string;
    analytics: 'not_configured';
    checked_at: string | null;
    expires_at: string | null;
    reasons: string[];
    metrics: {
        sharpness?: number | null;
        frames_decoded?: number;
        sample_seconds?: number;
        dark_ratio?: number | null;
        repeated_frame_ratio?: number | null;
    };
}
export interface RegistryCamera {
    id: string;
    external_id: string;
    source_id: string;
    vendor_id: string;
    vendor_name: string;
    name: string;
    location: string | null;
    department: string | null;
    camera_type: string | null;
    ownership: string | null;
    coordinates: Coordinates | null;
    health: CameraHealth;
    streams: CameraStream[];
    stream: {
        configured: boolean;
        count: number;
        protocols: string[];
    };
    enabled: boolean;
    revision: number;
    missing_metadata: string[];
    catalogue_status: 'present' | 'missing_from_source';
    source_state: 'draft' | 'approved' | 'disabled';
    infrastructure: Record<string, unknown>;
}
export interface CameraMetadata {
    name?: string;
    location?: string | null;
    department?: string | null;
    camera_type?: string | null;
    ownership?: string | null;
    coordinates?: Coordinates | null;
    streams?: CameraStreamInput[];
    enabled?: boolean;
}
export interface CameraInput extends CameraMetadata {
    external_id: string;
    name: string;
    source_id?: string;
}
export interface RegistrySource {
    id: string;
    vendor_id: string;
    name: string;
    slug: string;
    adapter: 'sentinel' | 'manual';
    state: 'draft' | 'approved' | 'disabled';
    last_sync_at: string | null;
    last_sync_error: string | null;
    last_sync_count: number | null;
    revision: number;
}
export interface SourceInput {
    vendor_id: string;
    name: string;
    slug: string;
    adapter: 'sentinel' | 'manual';
    connector_profile?: string;
    department?: string;
}
export interface Vendor {
    id: string;
    name: string;
    slug: string;
    active: boolean;
    created_at: string;
}
export interface FleetHealth {
    total: number;
    counts: Record<string, number>;
    checked_at?: string | null;
}
export interface ImportResult {
    created: number;
    skipped: number;
    rows: {
        row: number;
        external_id: string;
        action: 'create' | 'skip_existing';
    }[];
}
export interface SyncResult {
    created: number;
    updated: number;
}
export interface TimelineEntry {
    time: string;
    event: string;
    camera: string;
    type?: string;
}
export interface DetectionPerson {
    person_id: string;
    zone: string;
    confidence?: number;
    bbox?: number[];
}
export interface SecurityEvent {
    id: string;
    event_type: string;
    camera_id: string;
    camera_name: string;
    timestamp: string;
    severity: Severity;
    status: EventStatus;
    confidence: number;
    zone: string;
    description: string;
    duration_sec?: number;
    summary?: string;
    person_id?: string | null;
    clip_ref?: string | null;
    thumbnail?: string | null;
    persons?: DetectionPerson[];
    person_ids?: string[];
    vlm_analysis?: {
        summary: string;
        confidence?: number;
        flags?: string[];
        objects_detected?: string[];
        activity?: string;
        person_count?: number;
        frame_timestamp_sec?: number;
        persons?: {
            id: string;
            zone: string;
        }[];
    } | null;
}
export interface EventQuery {
    severity?: string;
    status?: string;
    zone?: string;
    limit?: number;
    camera_id?: string;
    offset?: number;
}
export interface EventPage {
    events: SecurityEvent[];
    total: number;
}
export interface Incident {
    id: string;
    title: string;
    summary: string;
    severity: Severity;
    status: EventStatus;
    notes?: string;
    event_ids?: string[];
    events_linked?: string[];
    camera_ids?: string[];
    person_ids?: string[];
    timeline?: TimelineEntry[];
}
export interface InvestigationResult {
    answer: string;
    events?: SecurityEvent[];
    relevant_events?: SecurityEvent[];
    timeline?: TimelineEntry[];
    confidence?: number;
}
export interface InvestigationMessage {
    role: 'ai' | 'user';
    content: string;
    timestamp: string;
    events?: SecurityEvent[];
    timeline?: TimelineEntry[];
    confidence?: number;
}
export interface SystemStats {
    cameras_online?: number;
    cameras_warning?: number;
    cameras_offline?: number;
    events_today?: number;
    critical_events?: number;
    high_events?: number;
    pending_review?: number;
    active_incidents?: number;
    total_events?: number;
    events_processed?: number;
    hardware?: {
        cpu: number;
        ram: number;
        gpu_util: number;
        gpu_mem: number;
    };
}
export interface ReportEntry {
    event_id: string;
    timestamp: string;
    camera: string;
    description: string;
    person_id?: string;
    status: EventStatus;
}
export interface EODReport {
    report_date: string;
    generated_at: string;
    network?: string;
    branch?: string;
    total_cameras?: number;
    cameras_online?: number;
    cameras_active?: number;
    total_events: number;
    critical_events?: number;
    critical_incidents?: number;
    executive_summary: string;
    critical_section: (ReportEntry & {
        confidence: number;
    })[];
    high_section: ReportEntry[];
    recommendations: string[];
    camera_health: {
        camera_id: string;
        name: string;
        status: string;
        fps: number;
        zone: string;
    }[];
}
export interface GeoCamera {
    camera_id: string;
    external_id?: string;
    name: string;
    lat: number;
    lng: number;
    city: string;
    zone?: string;
}
export interface JourneyStep {
    step: number;
    camera_id: string;
    camera_name: string;
    city: string;
    lat: number | null;
    lng: number | null;
    timestamp: string;
    confidence: number;
    pts_ms: number;
    plate?: string;
}
export interface Journey {
    plate: string;
    route: JourneyStep[];
}
export interface ActiveVehicle {
    plate: string;
    sightings_last_5min: number;
    last_camera: string;
    last_seen: string;
}
export interface StreamDetections {
    status: string;
    total_objects: number;
    persons: number;
    vehicles: number;
    confirmed_plates: string[];
    classes: [
        string,
        number
    ][];
    timestamp: string;
}
export interface WatchlistEntry {
    plate: string;
    make: string;
}
export interface Watchlist {
    entries: WatchlistEntry[];
    total: number;
}
export interface ChatCompletion {
    error?: {
        message: string;
    };
    choices?: {
        message: {
            content: string;
        };
    }[];
}
export interface AnalysisStatus {
    is_running: boolean;
}
export interface AnalyticsCamera {
    id: string;
    name: string;
    location: string;
    zone: string;
    status: string;
    fps: number;
    resolution: string;
    rtsp: string;
}
export interface CameraStats {
    camera_id: string;
    fps_live: number;
    gpu_decode_ms: number;
    inference_ms: number;
    tracker_ms: number;
    total_latency_ms: number;
    persons_in_frame: number;
    objects_in_frame: number;
    zone: string;
}
export interface EventStats {
    total_events: number;
    by_severity: Record<string, number>;
    by_status: Record<string, number>;
    by_zone: Record<string, number>;
}
export interface EventStatusResult {
    message: string;
    event_id: string;
    status: EventUpdateStatus;
}
export interface TrajectoryEntry {
    camera: string;
    time: string;
    zone: string;
    event: string;
}
export interface Topology {
    floor_plan_url: string;
    cameras: {
        camera_id: string;
        x: number;
        y: number;
    }[];
}
export interface VideoUploadResult {
    message: string;
    file_id: string;
    filename: string;
    status: 'processing';
}
export interface WatchlistAlert {
    id: string;
    timestamp: string;
    plate: string;
    camera_id: string;
    pts_ms: number;
    watchlist_entry: WatchlistEntry;
    severity: 'CRITICAL';
    message: string;
}
