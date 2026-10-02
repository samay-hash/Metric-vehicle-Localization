import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Connector:
    """Approved server configuration; clients cannot redirect credentials elsewhere."""

    catalogue_url: str
    login_url: str
    credentials_prefix: str
    rtsp_origin: str
    hls_origin: str
    whep_origin: str
    rtsp_path_template: str
    hls_path_template: str
    whep_path_template: str

    def __post_init__(self):
        for url in (self.catalogue_url, self.login_url):
            parsed = urlsplit(url)
            if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
                raise ValueError("Catalogue and login require HTTPS URLs without credentials, query or fragment")
        if urlsplit(self.login_url).netloc != urlsplit(self.catalogue_url).netloc:
            raise ValueError("Login and catalogue must share an approved origin")
        for url, protocols in ((self.rtsp_origin, ("rtsp", "rtsps")), (self.hls_origin, ("https",)), (self.whep_origin, ("http", "https"))):
            parsed = urlsplit(url)
            if parsed.scheme not in protocols or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ("", "/"):
                raise ValueError("Media origins must be bare approved origins without credentials")
        for template in (self.rtsp_path_template, self.hls_path_template, self.whep_path_template):
            if not template.startswith("/") or template.count("{camera_id}") != 1 or "?" in template or "#" in template:
                raise ValueError("Stream path templates require one {camera_id} placeholder and no query or fragment")
        if not self.credentials_prefix.replace("_", "").isalnum():
            raise ValueError("Invalid credentials prefix")


@dataclass(frozen=True)
class Settings:
    database_url: str
    admin_token: str = field(repr=False)
    reader_token: str = field(default="", repr=False)
    connectors: dict[str, Connector] = field(default_factory=dict)
    cors_origins: tuple[str, ...] = ()
    max_catalogue_bytes: int = 8_000_000
    max_catalogue_cameras: int = 100_000
    vendor_session_hours: int = 12
    health_worker_token: str = field(default="", repr=False)
    health_interval_seconds: int = 600
    health_stale_seconds: int = 1800
    health_failure_threshold: int = 3
    health_recovery_threshold: int = 2
    health_retention_days: int = 7

    def __post_init__(self):
        if len(self.admin_token) < 32:
            raise ValueError("REGISTRY_ADMIN_TOKEN must contain at least 32 characters")
        if self.reader_token and (len(self.reader_token) < 32 or self.reader_token == self.admin_token):
            raise ValueError("REGISTRY_READER_TOKEN must be distinct and at least 32 characters")
        if not 1 <= self.vendor_session_hours <= 168:
            raise ValueError("REGISTRY_VENDOR_SESSION_HOURS must be between 1 and 168")
        if self.health_worker_token and (len(self.health_worker_token) < 32 or self.health_worker_token in (self.admin_token, self.reader_token)):
            raise ValueError("REGISTRY_HEALTH_WORKER_TOKEN must be distinct and at least 32 characters")
        if not 10 <= self.health_interval_seconds <= 3600 or not self.health_interval_seconds < self.health_stale_seconds <= 86400:
            raise ValueError("Health interval must be 10..3600 seconds and freshness must exceed it (max 86400)")
        if not 1 <= self.health_failure_threshold <= 20 or not 1 <= self.health_recovery_threshold <= 20:
            raise ValueError("Health persistence thresholds must be 1..20")
        if not 1 <= self.health_retention_days <= 30:
            raise ValueError("Health retention must be 1..30 days")

    @classmethod
    def from_env(cls):
        default_db = Path(__file__).resolve().parents[1] / "registry-data" / "registry.sqlite3"
        profiles = json.loads(os.getenv("REGISTRY_CONNECTORS_JSON", "{}"))
        return cls(
            database_url=os.getenv("REGISTRY_DATABASE_URL", f"sqlite:///{default_db}"),
            admin_token=os.getenv("REGISTRY_ADMIN_TOKEN", ""),
            reader_token=os.getenv("REGISTRY_READER_TOKEN", ""),
            connectors={key: Connector(**value) for key, value in profiles.items()},
            cors_origins=tuple(s.strip() for s in os.getenv("REGISTRY_CORS_ORIGINS", "").split(",") if s.strip()),
            vendor_session_hours=int(os.getenv("REGISTRY_VENDOR_SESSION_HOURS", "12")),
            health_worker_token=os.getenv("REGISTRY_HEALTH_WORKER_TOKEN", ""),
            health_interval_seconds=int(os.getenv("REGISTRY_HEALTH_INTERVAL_SECONDS", "600")),
            health_stale_seconds=int(os.getenv("REGISTRY_HEALTH_STALE_SECONDS", "1800")),
            health_failure_threshold=int(os.getenv("REGISTRY_HEALTH_FAILURE_THRESHOLD", "3")),
            health_recovery_threshold=int(os.getenv("REGISTRY_HEALTH_RECOVERY_THRESHOLD", "2")),
            health_retention_days=int(os.getenv("REGISTRY_HEALTH_RETENTION_DAYS", "7")),
        )
