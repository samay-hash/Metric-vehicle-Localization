from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import JSON, Boolean, CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow():
    return datetime.now(timezone.utc)


def new_id():
    return str(uuid4())


class Base(DeclarativeBase):
    pass


class Vendor(Base):
    __tablename__ = "registry_vendors"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ApiKey(Base):
    __tablename__ = "registry_api_keys"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    vendor_id: Mapped[str] = mapped_column(ForeignKey("registry_vendors.id"), index=True)
    label: Mapped[str] = mapped_column(String(100))
    digest: Mapped[str] = mapped_column(String(64), unique=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class VendorUser(Base):
    __tablename__ = "registry_vendor_users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    vendor_id: Mapped[str] = mapped_column(ForeignKey("registry_vendors.id"), index=True)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    display_name: Mapped[str] = mapped_column(String(200))
    password_hash: Mapped[str] = mapped_column(String(255))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class VendorSession(Base):
    __tablename__ = "registry_vendor_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("registry_vendor_users.id"), index=True)
    token_digest: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DashboardUser(Base):
    __tablename__ = "registry_dashboard_users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    display_name: Mapped[str] = mapped_column(String(200))
    password_hash: Mapped[str] = mapped_column(String(255))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DashboardRoleAssignment(Base):
    __tablename__ = "registry_dashboard_role_assignments"
    __table_args__ = (UniqueConstraint("user_id", "role", "scope_type", "scope_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("registry_dashboard_users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(40), index=True)
    scope_type: Mapped[str] = mapped_column(String(40), index=True)
    scope_id: Mapped[str] = mapped_column(String(200), default="", server_default="")
    created_by: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DashboardSession(Base):
    __tablename__ = "registry_dashboard_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("registry_dashboard_users.id", ondelete="CASCADE"), index=True)
    token_digest: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SecurityAudit(Base):
    __tablename__ = "registry_security_audit"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    actor: Mapped[str] = mapped_column(String(100), index=True)
    action: Mapped[str] = mapped_column(String(100), index=True)
    target_id: Mapped[str | None] = mapped_column(String(100), index=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class Source(Base):
    __tablename__ = "registry_sources"
    __table_args__ = (UniqueConstraint("vendor_id", "slug"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    vendor_id: Mapped[str] = mapped_column(ForeignKey("registry_vendors.id"), index=True)
    slug: Mapped[str] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(200))
    adapter: Mapped[str] = mapped_column(String(30))
    connector_profile: Mapped[str | None] = mapped_column(String(80))
    department: Mapped[str | None] = mapped_column(String(200), index=True)
    state: Mapped[str] = mapped_column(String(20), default="draft")
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_sync_error: Mapped[str | None] = mapped_column(String(60))
    last_sync_count: Mapped[int | None] = mapped_column(Integer)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    health_generation: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __mapper_args__ = {"version_id_col": revision}


class Camera(Base):
    __tablename__ = "registry_cameras"
    __table_args__ = (
        UniqueConstraint("source_id", "external_id"),
        CheckConstraint("latitude IS NULL OR (latitude >= -90 AND latitude <= 90)"),
        CheckConstraint("longitude IS NULL OR (longitude >= -180 AND longitude <= 180)"),
        CheckConstraint("(latitude IS NULL AND longitude IS NULL) OR (latitude IS NOT NULL AND longitude IS NOT NULL)"),
        Index("ix_registry_cameras_source_status", "source_id", "catalogue_status"),
        Index("ix_registry_cameras_coordinates", "longitude", "latitude"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    source_id: Mapped[str] = mapped_column(ForeignKey("registry_sources.id"), index=True)
    external_id: Mapped[str] = mapped_column(String(200))
    discovered_name: Mapped[str] = mapped_column(String(200))
    name_override: Mapped[str | None] = mapped_column(String(200))
    location: Mapped[str | None] = mapped_column(String(500))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    location_provenance: Mapped[str | None] = mapped_column(String(500))
    camera_type: Mapped[str | None] = mapped_column(String(80), index=True)
    ownership: Mapped[str | None] = mapped_column(String(200))
    department: Mapped[str | None] = mapped_column(String(200), index=True)
    stream_url: Mapped[str | None] = mapped_column(String(2048))
    stream_protocol: Mapped[str | None] = mapped_column(String(20))
    stream_endpoints: Mapped[list["CameraStream"]] = relationship(
        back_populates="camera", cascade="all, delete-orphan", lazy="selectin",
        order_by="CameraStream.position",
    )
    health_record: Mapped["CameraHealthRecord | None"] = relationship(lazy="selectin", uselist=False)
    infrastructure: Mapped[dict] = mapped_column(JSON, default=dict)
    catalogue_status: Mapped[str] = mapped_column(String(30), default="present")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_seen_in_catalogue_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    health_generation: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    __mapper_args__ = {"version_id_col": revision}


class CameraStream(Base):
    __tablename__ = "registry_camera_streams"
    __table_args__ = (
        UniqueConstraint("camera_id", "position"),
        Index("ix_registry_camera_streams_camera", "camera_id"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    camera_id: Mapped[str] = mapped_column(ForeignKey("registry_cameras.id", ondelete="CASCADE"))
    label: Mapped[str] = mapped_column(String(100))
    protocol: Mapped[str] = mapped_column(String(20))
    url: Mapped[str] = mapped_column(String(2048))
    position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    camera: Mapped[Camera] = relationship(back_populates="stream_endpoints")


class Audit(Base):
    __tablename__ = "registry_audit"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    vendor_id: Mapped[str] = mapped_column(ForeignKey("registry_vendors.id"), index=True)
    resource_id: Mapped[str] = mapped_column(String(36), index=True)
    actor: Mapped[str] = mapped_column(String(100))
    action: Mapped[str] = mapped_column(String(80))
    changes: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CameraHealthRecord(Base):
    __tablename__ = "registry_camera_health"
    camera_id: Mapped[str] = mapped_column(ForeignKey("registry_cameras.id", ondelete="CASCADE"), primary_key=True)
    stream_key: Mapped[str] = mapped_column(String(100))
    target_revision: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(30))
    candidate: Mapped[str] = mapped_column(String(30))
    consecutive_count: Mapped[int] = mapped_column(Integer)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    last_frame_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    details: Mapped[dict] = mapped_column(JSON)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    __mapper_args__ = {"version_id_col": revision}


class HealthMeasurement(Base):
    __tablename__ = "registry_health_measurements"
    __table_args__ = (Index("ix_health_measurements_camera_time", "camera_id", "checked_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    camera_id: Mapped[str] = mapped_column(ForeignKey("registry_cameras.id", ondelete="CASCADE"))
    stream_key: Mapped[str] = mapped_column(String(100))
    target_revision: Mapped[str] = mapped_column(String(64))
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    connectivity: Mapped[str] = mapped_column(String(30))
    previous_status: Mapped[str | None] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(30))
    details: Mapped[dict] = mapped_column(JSON)
