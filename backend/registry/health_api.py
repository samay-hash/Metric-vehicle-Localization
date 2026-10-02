"""Scoped camera health reads and a separate, least-privilege worker interface."""
import secrets
from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import String, case, cast, delete, func, select
from sqlalchemy.orm import Session

from .api import camera_filters, database, filters, get_camera, visible
from .auth import Principal, authenticate, bearer, digest, require
from .health import aware, health_summary, next_state, probe_target, target_revision
from .models import Camera, CameraHealthRecord, HealthMeasurement, Source, Vendor, utcnow
from .schemas import HealthObservation

router = APIRouter(prefix="/api/v1")


def health_worker(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    configured = request.app.state.settings.health_worker_token
    if not configured or credentials is None or not secrets.compare_digest(digest(credentials.credentials), digest(configured)):
        raise HTTPException(401, "health_worker_authentication_required")


@router.get("/internal/health/targets", dependencies=[Depends(health_worker)], tags=["health worker"])
def targets(request: Request, db: Session = Depends(database), after: UUID | None = None,
            limit: int = Query(100, ge=1, le=500)):
    query = select(Camera, Source).join(Source).join(Vendor).where(
        Camera.enabled.is_(True), Source.state == "approved", Vendor.active.is_(True))
    if after:
        query = query.where(Camera.id > str(after))
    rows = db.execute(query.order_by(Camera.id).limit(limit + 1)).all()
    return {"data": [{"camera_id": c.id, "target_revision": target_revision(c, s), **probe_target(c, s)}
                     for c, s in rows[:limit]],
            "next_cursor": rows[limit - 1][0].id if len(rows) > limit else None,
            "interval_seconds": request.app.state.settings.health_interval_seconds,
            "stale_seconds": request.app.state.settings.health_stale_seconds}


@router.post("/internal/health/observations", dependencies=[Depends(health_worker)], tags=["health worker"])
def ingest(body: HealthObservation, request: Request, db: Session = Depends(database)):
    settings = request.app.state.settings
    now = utcnow()
    payload = body.model_dump(mode="json")
    existing = db.get(HealthMeasurement, str(body.id))
    if existing:
        if existing.details != payload:
            raise HTTPException(409, "observation_id_reused")
        return {"accepted": True, "duplicate": True}
    if body.checked_at > now + timedelta(seconds=5) or body.checked_at < now - timedelta(seconds=settings.health_stale_seconds):
        raise HTTPException(422, "observation_outside_freshness_window")
    row = db.execute(select(Camera, Source).join(Source).join(Vendor).where(
        Camera.id == str(body.camera_id), Camera.enabled.is_(True), Source.state == "approved", Vendor.active.is_(True))).first()
    if row is None:
        raise HTTPException(404, "active_camera_not_found")
    camera, source = row
    if body.target_revision != target_revision(camera, source) or body.stream_key != probe_target(camera, source)["stream_key"]:
        raise HTTPException(409, "probe_target_changed")
    record = camera.health_record
    if record and body.checked_at <= aware(record.checked_at):
        raise HTTPException(409, "out_of_order_observation")
    # Gaps and target changes reset persistence counters; old evidence cannot confirm a new fault.
    prior = record if record and record.target_revision == body.target_revision and aware(record.expires_at) > body.checked_at else None
    status, candidate, count = next_state(prior, body, settings)
    previous = prior.status if prior else None
    if record is None:
        record = CameraHealthRecord(camera_id=camera.id)
        db.add(record)
    record.stream_key = body.stream_key
    record.target_revision = body.target_revision
    record.status, record.candidate, record.consecutive_count = status, candidate, count
    record.checked_at = body.checked_at
    record.expires_at = body.checked_at + timedelta(seconds=settings.health_stale_seconds)
    if prior is None:
        record.last_frame_at = None
    if body.connectivity == "reachable":
        record.last_frame_at = body.checked_at
    record.details = payload
    db.add(HealthMeasurement(id=str(body.id), camera_id=camera.id, stream_key=body.stream_key,
                            target_revision=body.target_revision, checked_at=body.checked_at,
                            connectivity=body.connectivity, previous_status=previous, status=status, details=payload))
    db.commit()
    return {"accepted": True, "duplicate": False, "status": status}


@router.post("/internal/health/prune", dependencies=[Depends(health_worker)], tags=["health worker"])
def prune(request: Request, db: Session = Depends(database)):
    cutoff = utcnow() - timedelta(days=request.app.state.settings.health_retention_days)
    # Bound each transaction; the worker invokes this once per sweep.
    ids = select(HealthMeasurement.id).where(HealthMeasurement.checked_at < cutoff).limit(5000)
    result = db.execute(delete(HealthMeasurement).where(HealthMeasurement.id.in_(ids)))
    db.commit()
    return {"deleted": result.rowcount}


@router.get("/cameras/{camera_id}/health", tags=["cameras"])
def camera_health(camera_id: str, request: Request, db: Session = Depends(database),
                  principal: Principal = Depends(require("camera.health.read"))):
    camera, source = get_camera(db, camera_id, principal)
    now = utcnow()
    start = now - timedelta(hours=24)
    rows = db.execute(select(HealthMeasurement.checked_at, HealthMeasurement.connectivity).where(
        HealthMeasurement.camera_id == camera.id, HealthMeasurement.target_revision == target_revision(camera, source),
        HealthMeasurement.checked_at >= start, HealthMeasurement.checked_at <= now,
        HealthMeasurement.connectivity.in_(["reachable", "unreachable", "auth_failed", "decode_failed"]))).all()
    interval = request.app.state.settings.health_interval_seconds
    # Count at most one completed probe per scheduled bucket. Retries/duplicates
    # must not inflate coverage; use the latest result in each bucket.
    buckets = {}
    for checked_at, connectivity in sorted(rows, key=lambda row: row[0]):
        buckets[int(aware(checked_at).timestamp()) // interval] = connectivity
    expected = max(1, int((now - max(start, aware(camera.created_at))).total_seconds() // interval) + 1)
    completed = len(buckets)
    successes = sum(value == "reachable" for value in buckets.values())
    return {"camera_id": camera.id, **health_summary(camera, source, now),
            "catalogue_status": camera.catalogue_status,
            "reliability": {"window_start": start, "window_end": now, "interval_seconds": interval,
                            "completed_probes": completed, "successful_probes": successes,
                            "expected_probes": expected, "coverage_percent": min(100, round(100 * completed / expected, 2)),
                            "observed_availability_percent": round(100 * successes / completed, 2) if completed else None}}


@router.get("/cameras/{camera_id}/health/history", tags=["cameras"])
def history(camera_id: str, db: Session = Depends(database),
            principal: Principal = Depends(require("camera.health.read")),
            limit: int = Query(50, ge=1, le=200)):
    get_camera(db, camera_id, principal)
    rows = db.scalars(select(HealthMeasurement).where(HealthMeasurement.camera_id == camera_id)
                      .order_by(HealthMeasurement.checked_at.desc(), HealthMeasurement.id.desc()).limit(limit))
    return {"data": [{"id": r.id, "checked_at": aware(r.checked_at), "stream_key": r.stream_key,
                      "status": r.status, "previous_status": r.previous_status,
                      "transition": r.status != r.previous_status,
                      "connectivity": r.connectivity, "quality_flags": r.details["quality_flags"]} for r in rows]}


@router.get("/fleet/health", tags=["cameras"])
def fleet_health(db: Session = Depends(database), principal: Principal = Depends(require("camera.health.read")),
                 options: dict = Depends(filters)):
    now = utcnow()
    revision = cast(Camera.health_generation, String) + ":" + cast(Source.health_generation, String)
    state = case((Source.state != "approved", "disabled"),
                 (CameraHealthRecord.camera_id.is_(None), "unmonitored"),
                 (CameraHealthRecord.target_revision != revision, "stale"),
                 (CameraHealthRecord.expires_at <= now, "stale"), else_=CameraHealthRecord.status)
    query = select(state.label("status"), func.count()).select_from(Camera).join(Source).outerjoin(CameraHealthRecord).where(Camera.enabled.is_(True))
    query = camera_filters(visible(query, principal, camera_scope=True), postgis=db.bind.dialect.name == "postgresql", **options)
    counts = dict(db.execute(query.group_by(state)).all())
    return {"checked_at": now, "total": sum(counts.values()), "counts": counts}
