from datetime import date, datetime
from typing import Annotated, Generic, Literal, TypeVar
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator
from urllib.parse import urlsplit

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Slug = Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9-]{0,79}$")]
ExternalId = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,199}$")]
Email = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=320, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)


class VendorCreate(StrictModel):
    name: Name
    slug: Slug


class KeyCreate(StrictModel):
    label: Annotated[str, StringConstraints(min_length=1, max_length=100)]


class VendorLogin(StrictModel):
    email: Email
    password: Annotated[str, StringConstraints(min_length=8, max_length=128)]

    @field_validator("email")
    @classmethod
    def normalize_login_email(cls, value):
        return value.casefold()


class VendorAccountRead(BaseModel):
    id: str
    vendor_id: str
    vendor_name: str
    email: str
    display_name: str


class VendorLoginResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"]
    expires_at: datetime
    account: VendorAccountRead


SystemRole = Literal["master_admin", "investigator", "maintenance", "it_operator"]
ScopeType = Literal["global", "state", "district", "commissionerate", "zone", "police_station", "department", "vendor"]


class RoleAssignmentInput(StrictModel):
    role: SystemRole
    scope_type: ScopeType = "global"
    scope_id: Annotated[str, StringConstraints(min_length=1, max_length=200)] | None = None

    @model_validator(mode="after")
    def valid_scope(self):
        if self.scope_type == "global" and self.scope_id is not None:
            raise ValueError("Global role assignments cannot include a scope ID")
        if self.scope_type != "global" and self.scope_id is None:
            raise ValueError("Scoped role assignments require a scope ID")
        return self


class DashboardUserCreate(StrictModel):
    email: Email
    display_name: Name
    password: Annotated[str, StringConstraints(min_length=12, max_length=128)]
    assignments: list[RoleAssignmentInput] = Field(min_length=1, max_length=20)


class DashboardAssignmentsReplace(StrictModel):
    assignments: list[RoleAssignmentInput] = Field(min_length=1, max_length=20)


class SourceCreate(StrictModel):
    vendor_id: str
    slug: Slug
    name: Name
    adapter: Literal["sentinel", "manual"]
    connector_profile: Slug | None = None
    department: Name | None = None

    @model_validator(mode="after")
    def profile_matches(self):
        if (self.adapter == "sentinel") != (self.connector_profile is not None):
            raise ValueError("Sentinel requires a connector profile; manual sources cannot use one")
        return self


class SourceState(StrictModel):
    state: Literal["approved", "disabled"]


class SourcePatch(StrictModel):
    name: Name | None = None
    department: Name | None = None

    @model_validator(mode="after")
    def name_cannot_be_null(self):
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("Source name cannot be null")
        return self


class Coordinates(StrictModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    provenance: Annotated[str, StringConstraints(min_length=1, max_length=500)]


class Infrastructure(StrictModel):
    installed_on: date | None = None
    maintenance_due_on: date | None = None
    maintenance_status: Literal["unknown", "operational", "due", "under_maintenance", "retired"] = "unknown"
    storage_type: Literal["unknown", "none", "nvr", "on_camera", "department_server", "other"] = "unknown"
    storage_location: Annotated[str, StringConstraints(max_length=500)] | None = None
    retention_days: int | None = Field(default=None, ge=0, le=36500)
    connectivity_type: Annotated[str, StringConstraints(max_length=80)] | None = None


class CameraStreamInput(StrictModel):
    label: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    protocol: Literal["rtsp", "rtsps", "hls", "whep", "http", "https"]
    url: Annotated[str, StringConstraints(strip_whitespace=True, min_length=6, max_length=2048)]

    @model_validator(mode="after")
    def protocol_matches_url(self):
        parsed = urlsplit(self.url)
        if parsed.scheme not in ("rtsp", "rtsps", "http", "https") or not parsed.hostname:
            raise ValueError("Stream URL must use RTSP, RTSPS, HTTP or HTTPS and include a host")
        expected = {"rtsp": ("rtsp",), "rtsps": ("rtsps",), "hls": ("http", "https"),
                    "whep": ("http", "https"), "http": ("http",), "https": ("https",)}
        if parsed.scheme not in expected[self.protocol]:
            raise ValueError("Stream protocol does not match the URL scheme")
        return self


class CameraMetadata(StrictModel):
    name: Name | None = None
    location: Annotated[str, StringConstraints(max_length=500)] | None = None
    coordinates: Coordinates | None = None
    camera_type: Annotated[str, StringConstraints(max_length=80)] | None = None
    ownership: Name | None = None
    department: Name | None = None
    stream_url: Annotated[str, StringConstraints(strip_whitespace=True, min_length=6, max_length=2048)] | None = None
    stream_protocol: Literal["rtsp", "rtsps", "hls", "whep", "http", "https"] | None = None
    streams: list[CameraStreamInput] | None = Field(default=None, max_length=12)
    infrastructure: Infrastructure | None = None
    enabled: bool = True

    @model_validator(mode="after")
    def stream_fields_match(self):
        if self.streams is not None and ("stream_url" in self.model_fields_set or "stream_protocol" in self.model_fields_set):
            raise ValueError("Use streams or the legacy stream fields, not both")
        supplied = "stream_url" in self.model_fields_set or "stream_protocol" in self.model_fields_set
        if not supplied:
            return self
        if (self.stream_url is None) != (self.stream_protocol is None):
            raise ValueError("Stream URL and protocol must be supplied together")
        if self.stream_url:
            parsed = urlsplit(self.stream_url)
            if parsed.scheme not in ("rtsp", "rtsps", "http", "https") or not parsed.hostname:
                raise ValueError("Stream URL must use RTSP, RTSPS, HTTP or HTTPS and include a host")
            expected = {"rtsp": ("rtsp",), "rtsps": ("rtsps",), "hls": ("http", "https"),
                        "whep": ("http", "https"), "http": ("http",), "https": ("https",)}
            if parsed.scheme not in expected[self.stream_protocol]:
                raise ValueError("Stream protocol does not match the URL scheme")
        return self


class CameraCreate(CameraMetadata):
    source_id: str | None = None
    external_id: ExternalId
    name: Name


class CameraPatch(CameraMetadata):
    pass


class ImportRow(CameraMetadata):
    external_id: ExternalId
    name: Name


class CameraImport(StrictModel):
    source_id: str | None = None
    rows: list[ImportRow] = Field(min_length=1, max_length=1000)
    dry_run: bool = True


class SyncRequest(StrictModel):
    dry_run: bool = True
    allow_empty: bool = False


class CatalogueEntry(StrictModel):
    id: ExternalId
    name: Name


class VendorRead(BaseModel):
    id: str
    name: str
    slug: str
    active: bool
    created_at: datetime


class SourceRead(BaseModel):
    id: str
    vendor_id: str
    slug: str
    name: str
    adapter: Literal["sentinel", "manual"]
    connector_profile: str | None
    department: str | None
    state: Literal["draft", "approved", "disabled"]
    last_sync_at: datetime | None
    last_sync_error: str | None
    last_sync_count: int | None
    revision: int


class CameraHealth(BaseModel):
    status: str = "unmonitored"
    freshness: Literal["fresh", "stale", "never_checked"] = "never_checked"
    connectivity: str
    video_quality: str
    analytics: Literal["not_configured"]
    checked_at: datetime | None
    expires_at: datetime | None = None
    last_frame_at: datetime | None = None
    stream_key: str | None = None
    reasons: list[str] = Field(default_factory=list)
    metrics: dict = Field(default_factory=dict)
    consecutive_count: int = 0


class HealthMetrics(StrictModel):
    frames_decoded: int = Field(0, ge=0, le=100)
    sample_seconds: float = Field(ge=0, le=120)
    dark_ratio: float | None = Field(None, ge=0, le=1)
    sharpness: float | None = Field(None, ge=0, le=1_000_000)
    repeated_frame_ratio: float | None = Field(None, ge=0, le=1)


class HealthObservation(StrictModel):
    id: UUID
    camera_id: UUID
    target_revision: Annotated[str, StringConstraints(pattern=r"^[0-9]+:[0-9]+$", max_length=64)]
    stream_key: Annotated[str, StringConstraints(min_length=1, max_length=100)]
    checked_at: AwareDatetime
    connectivity: Literal["reachable", "unreachable", "auth_failed", "decode_failed", "unsupported", "not_configured", "probe_error"]
    quality_flags: list[Literal["darkness_suspected", "blur_suspected", "freeze_suspected"]] = Field(default_factory=list, max_length=3)
    quality_checks: list[Literal["darkness_suspected", "blur_suspected", "freeze_suspected"]] = Field(default_factory=list, max_length=3)
    metrics: HealthMetrics
    detector_version: Literal["rtsp-health-v1"] = "rtsp-health-v1"

    @model_validator(mode="after")
    def coherent_measurement(self):
        if self.connectivity == "reachable" and self.metrics.frames_decoded < 1:
            raise ValueError("Reachability requires a decoded frame")
        if self.connectivity != "reachable" and (self.metrics.frames_decoded or self.quality_flags):
            raise ValueError("Unavailable video cannot have frame measurements or quality flags")
        if set(self.quality_flags) - set(self.quality_checks):
            raise ValueError("Quality flags must identify checks that were performed")
        return self


class Capabilities(BaseModel):
    source_protocols: list[Literal["rtsp", "hls", "webrtc"]]
    managed_playback: bool
    snapshots: bool
    crops: bool


class Point(BaseModel):
    type: Literal["Point"]
    coordinates: tuple[float, float]


class CameraRead(BaseModel):
    id: str
    external_id: str
    source_id: str
    vendor_id: str
    department: str | None
    name: str
    vendor_name: str
    location: str | None
    coordinates: Coordinates | None
    geometry: Point | None
    camera_type: str | None
    ownership: str | None
    infrastructure: dict
    enabled: bool
    catalogue_status: Literal["present", "missing_from_source"]
    source_state: Literal["draft", "approved", "disabled"]
    health: CameraHealth
    capabilities: Capabilities
    streams: list[dict]
    stream: dict
    missing_metadata: list[str]
    last_seen_in_catalogue_at: datetime | None
    created_at: datetime
    updated_at: datetime
    revision: int


T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    data: list[T]
    next_cursor: str | None
    total: int | None = None
