import csv
import io
import math
import secrets
from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query, Request, Response
from pydantic import ValidationError
from sqlalchemy import and_, delete, func, or_, select, text
from sqlalchemy.orm import Session

from .adapters import AdapterError, fetch_sentinel, public_sentinel_endpoints
from .auth import (Principal, authenticate, digest, hash_password, normalize_email,
                   principal as build_principal, require, verify_password)
from .models import (ApiKey, Audit, Camera, CameraStream, DashboardRoleAssignment, DashboardSession,
                     DashboardUser, SecurityAudit, Source, Vendor, VendorSession, VendorUser, utcnow)
from .rbac import landing_path
from .sentinel_metadata import enrich_sentinel_camera, needs_sentinel_enrichment
from .health import health_summary
from .schemas import (CameraCreate, CameraImport, CameraPatch, CameraRead, DashboardAssignmentsReplace,
                      DashboardUserCreate, ImportRow, KeyCreate, Page, SourceCreate, SourcePatch,
                      SourceRead, SourceState, SyncRequest, VendorCreate, VendorLogin,
                      VendorLoginResponse, VendorRead)

router = APIRouter(prefix="/api/v1")


def database(request: Request):
    with request.app.state.sessions() as session:
        yield session


def visible(query, principal, *, camera_scope=False):
    if principal.vendor_id:
        return query.where(Source.vendor_id == principal.vendor_id)
    if any(scope.type == "global" for scope in principal.scopes):
        return query
    allowed = []
    vendor_ids = principal.scope_ids("vendor")
    departments = principal.scope_ids("department")
    if vendor_ids:
        allowed.append(Source.vendor_id.in_(vendor_ids))
    if departments:
        department_match = Source.department.in_(departments)
        if camera_scope:
            department_match = or_(Camera.department.in_(departments), department_match)
        allowed.append(department_match)
    return query.where(or_(*allowed)) if allowed else query.where(Source.id.is_(None))


def get_source(db, source_id, principal):
    source = db.scalar(visible(select(Source).where(Source.id == source_id), principal))
    if source is None:
        raise HTTPException(404, "source_not_found")
    return source


def vendor_allowed(principal, vendor_id):
    return (any(scope.type == "global" for scope in principal.scopes)
            or principal.vendor_id == vendor_id or vendor_id in principal.scope_ids("vendor"))


def get_camera(db, camera_id, principal):
    row = db.execute(visible(
        select(Camera, Source).join(Source).where(Camera.id == camera_id), principal, camera_scope=True
    )).first()
    if row is None:
        raise HTTPException(404, "camera_not_found")
    return row


def audit(db, principal, vendor_id, resource_id, action, changes):
    db.add(Audit(actor=principal.actor, vendor_id=vendor_id, resource_id=resource_id,
                 action=action, changes=changes))


def security_audit(db, principal, action, target_id=None, details=None):
    actor = principal.actor if isinstance(principal, Principal) else principal
    db.add(SecurityAudit(actor=actor, action=action, target_id=target_id, details=details or {}))


def dashboard_user_json(user, assignments):
    roles = list(dict.fromkeys(row.role for row in assignments))
    return {"id": user.id, "email": user.email, "display_name": user.display_name, "active": user.active,
            "roles": roles,
            "assignments": [{"id": row.id, "role": row.role, "scope_type": row.scope_type,
                             "scope_id": row.scope_id or None} for row in assignments],
            "created_at": serial_time(user.created_at)}


def serial_time(value):
    if value is None:
        return None
    from datetime import timezone
    return value.replace(tzinfo=timezone.utc).isoformat() if value.tzinfo is None else value.isoformat()


def vendor_json(vendor):
    return {"id": vendor.id, "name": vendor.name, "slug": vendor.slug, "active": vendor.active,
            "created_at": serial_time(vendor.created_at)}


def source_json(source):
    return {"id": source.id, "vendor_id": source.vendor_id, "slug": source.slug, "name": source.name,
            "adapter": source.adapter, "connector_profile": source.connector_profile,
            "department": source.department, "state": source.state,
            "last_sync_at": serial_time(source.last_sync_at), "last_sync_error": source.last_sync_error,
            "last_sync_count": source.last_sync_count, "revision": source.revision}


def stored_streams(camera):
    streams = [{"id": stream.id, "label": stream.label, "protocol": stream.protocol,
                "url": stream.url, "managed": False} for stream in camera.stream_endpoints]
    if not streams and camera.stream_url:
        streams.append({"id": None, "label": "Main stream", "protocol": camera.stream_protocol,
                        "url": camera.stream_url, "managed": False})
    return streams


def camera_json(camera, source):
    streams = stored_streams(camera)
    managed_count = 3 if source.adapter == "sentinel" else 0
    stream_configured = managed_count > 0 or bool(streams)
    missing_metadata = [key for key, value in {
        "coordinates": camera.latitude, "department": camera.department or source.department,
        "camera_type": camera.camera_type, "ownership": camera.ownership, "location": camera.location,
    }.items() if value is None]
    if not stream_configured:
        missing_metadata.append("stream")
    return {
        "id": camera.id, "external_id": camera.external_id, "source_id": camera.source_id,
        "vendor_id": source.vendor_id, "department": camera.department or source.department,
        "name": camera.name_override or camera.discovered_name, "vendor_name": camera.discovered_name,
        "location": camera.location,
        "coordinates": None if camera.latitude is None else {
            "latitude": camera.latitude, "longitude": camera.longitude, "provenance": camera.location_provenance},
        "geometry": None if camera.latitude is None else {"type": "Point", "coordinates": [camera.longitude, camera.latitude]},
        "camera_type": camera.camera_type, "ownership": camera.ownership,
        "infrastructure": camera.infrastructure, "enabled": camera.enabled,
        "catalogue_status": camera.catalogue_status, "source_state": source.state,
        "health": health_summary(camera, source),
        "capabilities": {"source_protocols": ["rtsp", "hls", "webrtc"] if source.adapter == "sentinel" else [],
                         "managed_playback": stream_configured, "snapshots": False, "crops": False},
        "streams": streams,
        "stream": {"configured": stream_configured, "count": managed_count + len(streams),
                   "protocols": (["rtsp", "hls", "whep"] if source.adapter == "sentinel" else []) + [item["protocol"] for item in streams],
                   "protocol": streams[0]["protocol"] if streams else ("rtsp" if source.adapter == "sentinel" else None),
                   "url": streams[0]["url"] if streams else None,
                   "endpoint": f"/api/v1/cameras/{camera.id}/streams"},
        "missing_metadata": missing_metadata,
        "last_seen_in_catalogue_at": serial_time(camera.last_seen_in_catalogue_at),
        "created_at": serial_time(camera.created_at), "updated_at": serial_time(camera.updated_at),
        "revision": camera.revision,
    }


def apply_metadata(camera, fields):
    media_changed = any(key in fields and fields[key] != getattr(camera, key)
                        for key in ("enabled", "stream_url", "stream_protocol"))
    for key, value in fields.items():
        if key == "name":
            camera.name_override = value
        elif key == "coordinates":
            camera.latitude = value["latitude"] if value else None
            camera.longitude = value["longitude"] if value else None
            camera.location_provenance = value["provenance"] if value else None
        elif key == "infrastructure":
            camera.infrastructure = value or {}
        elif key == "streams":
            existing = [{"label": s.label, "protocol": s.protocol, "url": s.url} for s in camera.stream_endpoints]
            if existing == (value or []):
                continue
            media_changed = True
            # Delete old positions before inserting replacements with the same unique positions.
            from sqlalchemy.orm import object_session
            session = object_session(camera)
            camera.stream_endpoints.clear()
            if session:
                session.flush()
            camera.stream_endpoints = [CameraStream(label=item["label"], protocol=item["protocol"],
                                                     url=item["url"], position=index)
                                       for index, item in enumerate(value or [])]
            camera.stream_url = value[0]["url"] if value else None
            camera.stream_protocol = value[0]["protocol"] if value else None
        else:
            setattr(camera, key, value)
    if media_changed:
        camera.health_generation = (camera.health_generation or 1) + 1


def etag(camera, if_match):
    if if_match is None:
        raise HTTPException(428, "if_match_required")
    if if_match != f'"{camera.revision}"':
        raise HTTPException(412, "camera_revision_conflict")


def vendor_camera_source(db, principal, *, create):
    if not principal.vendor_id:
        raise HTTPException(422, "source_id_required_for_admin")
    source = db.scalar(select(Source).where(
        Source.vendor_id == principal.vendor_id, Source.slug == "vendor-cameras"))
    if source is None and create:
        source = Source(vendor_id=principal.vendor_id, slug="vendor-cameras", name="Vendor camera registry",
                        adapter="manual", state="approved")
        db.add(source)
        db.flush()
        audit(db, principal, source.vendor_id, source.id, "source.created_implicitly", {"adapter": "manual"})
    return source


@router.get("/me", tags=["identity"])
def me(principal: Principal = Depends(authenticate)):
    return {"actor": principal.actor, "role": principal.role, "vendor_id": principal.vendor_id,
            "user_id": principal.user_id, "email": principal.email, "display_name": principal.display_name,
            "roles": list(principal.roles),
            "permissions": sorted(principal.permissions),
            "scopes": [scope.as_dict() for scope in principal.scopes],
            "landing_path": landing_path(principal.roles)}


@router.post("/auth/login", tags=["identity"])
def dashboard_login(body: VendorLogin, request: Request, response: Response, db: Session = Depends(database)):
    user = db.scalar(select(DashboardUser).where(
        DashboardUser.email == normalize_email(body.email), DashboardUser.active.is_(True)))
    fallback = "scrypt$16384$8$1$00000000000000000000000000000000$18da842cc377e206743c165bf12bf2d7333c3f124e74d01c8089013d0653aa07"
    valid = verify_password(body.password, user.password_hash if user else fallback)
    if not user or not valid:
        security_audit(db, f"login:{normalize_email(body.email)}", "dashboard.login_failed")
        db.commit()
        raise HTTPException(401, "invalid_email_or_password", headers={"WWW-Authenticate": "Bearer"})
    assignments = db.scalars(select(DashboardRoleAssignment).where(
        DashboardRoleAssignment.user_id == user.id).order_by(DashboardRoleAssignment.role)).all()
    if not assignments:
        raise HTTPException(403, "no_active_role_assignments")
    token = "dsh_" + secrets.token_urlsafe(32)
    expires_at = utcnow() + timedelta(hours=request.app.state.settings.vendor_session_hours)
    session = DashboardSession(user_id=user.id, token_digest=digest(token), expires_at=expires_at)
    db.add(session)
    db.flush()
    roles = tuple(dict.fromkeys(row.role for row in assignments))
    security_audit(db, f"dashboard-user:{user.id}", "dashboard.login", user.id,
                   {"session_id": session.id, "roles": list(roles)})
    db.commit()
    response.headers["Cache-Control"] = "no-store"
    response.set_cookie("synetra_session", token, max_age=request.app.state.settings.vendor_session_hours * 3600,
                        httponly=True, secure=request.url.scheme == "https", samesite="lax", path="/")
    return {"access_token": token, "token_type": "bearer", "expires_at": expires_at,
            "account": {"id": user.id, "email": user.email, "display_name": user.display_name,
                        "roles": list(roles), "permissions": sorted(build_principal(
                            f"dashboard-user:{user.id}", roles[0], roles=roles).permissions),
                        "scopes": [{"type": row.scope_type, "id": row.scope_id or None} for row in assignments],
                        "landing_path": landing_path(roles)}}


@router.post("/auth/logout", status_code=204, tags=["identity"])
def dashboard_logout(response: Response, db: Session = Depends(database), principal: Principal = Depends(authenticate)):
    if not principal.session_id or not principal.actor.startswith("dashboard-user:"):
        raise HTTPException(403, "dashboard_session_required")
    session = db.get(DashboardSession, principal.session_id)
    if session and session.revoked_at is None:
        session.revoked_at = utcnow()
        security_audit(db, principal, "dashboard.logout", principal.user_id, {"session_id": session.id})
        db.commit()
    response.delete_cookie("synetra_session", path="/", httponly=True, samesite="lax")


@router.get("/access/users", tags=["access"])
def dashboard_users(db: Session = Depends(database), principal: Principal = Depends(require("user.manage"))):
    users = db.scalars(select(DashboardUser).order_by(DashboardUser.email)).all()
    assignments = db.scalars(select(DashboardRoleAssignment).order_by(DashboardRoleAssignment.role)).all()
    by_user = {}
    for assignment in assignments:
        by_user.setdefault(assignment.user_id, []).append(assignment)
    return {"data": [dashboard_user_json(user, by_user.get(user.id, [])) for user in users]}


@router.post("/access/users", status_code=201, tags=["access"])
def create_dashboard_user(body: DashboardUserCreate, db: Session = Depends(database),
                          principal: Principal = Depends(require("user.manage"))):
    email = normalize_email(body.email)
    if db.scalar(select(DashboardUser).where(DashboardUser.email == email)):
        raise HTTPException(409, "dashboard_user_email_exists")
    user = DashboardUser(email=email, display_name=body.display_name, password_hash=hash_password(body.password))
    db.add(user)
    db.flush()
    assignments = [DashboardRoleAssignment(
        user_id=user.id, role=item.role, scope_type=item.scope_type, scope_id=item.scope_id or "",
        created_by=principal.actor) for item in body.assignments]
    db.add_all(assignments)
    security_audit(db, principal, "dashboard_user.created", user.id,
                   {"email": email, "assignments": [item.model_dump() for item in body.assignments]})
    db.commit()
    return dashboard_user_json(user, assignments)


@router.put("/access/users/{user_id}/assignments", tags=["access"])
def replace_dashboard_assignments(user_id: str, body: DashboardAssignmentsReplace,
                                  db: Session = Depends(database),
                                  principal: Principal = Depends(require("role.assign"))):
    user = db.get(DashboardUser, user_id)
    if user is None:
        raise HTTPException(404, "dashboard_user_not_found")
    db.execute(delete(DashboardRoleAssignment).where(DashboardRoleAssignment.user_id == user.id))
    assignments = [DashboardRoleAssignment(
        user_id=user.id, role=item.role, scope_type=item.scope_type, scope_id=item.scope_id or "",
        created_by=principal.actor) for item in body.assignments]
    db.add_all(assignments)
    db.execute(DashboardSession.__table__.update().where(
        DashboardSession.user_id == user.id, DashboardSession.revoked_at.is_(None)).values(revoked_at=utcnow()))
    security_audit(db, principal, "dashboard_user.assignments_replaced", user.id,
                   {"assignments": [item.model_dump() for item in body.assignments], "sessions_revoked": True})
    db.commit()
    return dashboard_user_json(user, assignments)


@router.get("/access/audit", tags=["access"])
def security_audit_log(db: Session = Depends(database), principal: Principal = Depends(require("audit.read")),
                       limit: int = Query(100, ge=1, le=500), before: UUID | None = None):
    query = select(SecurityAudit)
    if before:
        cursor = db.get(SecurityAudit, str(before))
        if cursor is None:
            raise HTTPException(404, "audit_cursor_not_found")
        query = query.where(or_(SecurityAudit.created_at < cursor.created_at,
                                and_(SecurityAudit.created_at == cursor.created_at,
                                     SecurityAudit.id < cursor.id)))
    rows = db.scalars(query.order_by(SecurityAudit.created_at.desc(), SecurityAudit.id.desc()).limit(limit + 1)).all()
    return {
        "data": [{"id": row.id, "actor": row.actor, "action": row.action,
                  "target_id": row.target_id, "details": row.details,
                  "created_at": serial_time(row.created_at)} for row in rows[:limit]],
        "next_cursor": rows[limit - 1].id if len(rows) > limit else None,
    }


@router.post("/auth/vendor/login", tags=["identity"], response_model=VendorLoginResponse)
def vendor_login(body: VendorLogin, request: Request, response: Response, db: Session = Depends(database)):
    row = db.execute(select(VendorUser, Vendor).join(Vendor).where(
        VendorUser.email == normalize_email(body.email), VendorUser.active.is_(True), Vendor.active.is_(True))).first()
    # Invalid accounts still perform the expensive password operation to reduce account enumeration timing differences.
    fallback = "scrypt$16384$8$1$00000000000000000000000000000000$18da842cc377e206743c165bf12bf2d7333c3f124e74d01c8089013d0653aa07"
    valid = verify_password(body.password, row[0].password_hash if row else fallback)
    if not row or not valid:
        raise HTTPException(401, "invalid_email_or_password", headers={"WWW-Authenticate": "Bearer"})
    user, vendor = row
    token = "vnd_" + secrets.token_urlsafe(32)
    expires_at = utcnow() + timedelta(hours=request.app.state.settings.vendor_session_hours)
    session = VendorSession(user_id=user.id, token_digest=digest(token), expires_at=expires_at)
    db.add(session)
    db.flush()
    audit(db, Principal(f"vendor-user:{user.id}", "vendor", vendor.id, user.id, user.email, session.id),
          vendor.id, user.id, "vendor.login", {"session_id": session.id})
    db.commit()
    response.headers["Cache-Control"] = "no-store"
    return {"access_token": token, "token_type": "bearer", "expires_at": expires_at,
            "account": {"id": user.id, "vendor_id": vendor.id, "vendor_name": vendor.name,
                        "email": user.email, "display_name": user.display_name}}


@router.post("/auth/vendor/logout", status_code=204, tags=["identity"])
def vendor_logout(db: Session = Depends(database), principal: Principal = Depends(authenticate)):
    if not principal.session_id:
        raise HTTPException(403, "vendor_session_required")
    session = db.get(VendorSession, principal.session_id)
    if session and session.revoked_at is None:
        session.revoked_at = utcnow()
        audit(db, principal, principal.vendor_id, principal.user_id, "vendor.logout", {"session_id": session.id})
        db.commit()


@router.post("/vendors", status_code=201, tags=["vendors"], response_model=VendorRead)
def create_vendor(body: VendorCreate, db: Session = Depends(database),
                  principal: Principal = Depends(require("vendor.manage"))):
    vendor = Vendor(**body.model_dump())
    db.add(vendor)
    db.flush()
    audit(db, principal, vendor.id, vendor.id, "vendor.created", body.model_dump())
    db.commit()
    return vendor_json(vendor)


@router.get("/vendors", tags=["vendors"], response_model=Page[VendorRead])
def vendors(db: Session = Depends(database), principal: Principal = Depends(require("vendor.read")),
            limit: int = Query(100, ge=1, le=500), after: UUID | None = None):
    query = select(Vendor)
    if not any(scope.type == "global" for scope in principal.scopes):
        allowed = {principal.vendor_id} if principal.vendor_id else set()
        allowed.update(principal.scope_ids("vendor"))
        query = query.where(Vendor.id.in_(allowed))
    if after:
        query = query.where(Vendor.id > str(after))
    rows = db.scalars(query.order_by(Vendor.id).limit(limit + 1)).all()
    return {"data": [vendor_json(row) for row in rows[:limit]], "next_cursor": rows[limit-1].id if len(rows) > limit else None}


@router.post("/vendors/{vendor_id}/api-keys", status_code=201, tags=["vendors"])
def create_key(vendor_id: str, body: KeyCreate, response: Response,
               db: Session = Depends(database), principal: Principal = Depends(require("api_key.manage"))):
    if not vendor_allowed(principal, vendor_id):
        raise HTTPException(404, "vendor_not_found")
    if not db.get(Vendor, vendor_id):
        raise HTTPException(404, "vendor_not_found")
    token = "syn_" + secrets.token_urlsafe(32)
    key = ApiKey(vendor_id=vendor_id, label=body.label, digest=digest(token))
    db.add(key)
    db.flush()
    audit(db, principal, vendor_id, key.id, "key.created", {"label": body.label})
    db.commit()
    response.headers["Cache-Control"] = "no-store"
    return {"id": key.id, "token": token, "label": key.label, "vendor_id": vendor_id}


@router.delete("/vendors/{vendor_id}/api-keys/{key_id}", status_code=204, tags=["vendors"])
def revoke_key(vendor_id: str, key_id: str, db: Session = Depends(database),
               principal: Principal = Depends(require("api_key.manage"))):
    if not vendor_allowed(principal, vendor_id):
        raise HTTPException(404, "vendor_not_found")
    key = db.get(ApiKey, key_id)
    if not key or key.vendor_id != vendor_id:
        raise HTTPException(404, "key_not_found")
    key.revoked = True
    audit(db, principal, vendor_id, key_id, "key.revoked", {})
    db.commit()


@router.post("/sources", status_code=201, tags=["sources"], response_model=SourceRead)
def create_source(body: SourceCreate, request: Request, db: Session = Depends(database),
                  principal: Principal = Depends(require("source.write"))):
    if not vendor_allowed(principal, body.vendor_id):
        raise HTTPException(404, "vendor_not_found")
    if not db.get(Vendor, body.vendor_id):
        raise HTTPException(404, "vendor_not_found")
    if body.adapter == "sentinel" and body.connector_profile not in request.app.state.settings.connectors:
        raise HTTPException(422, "connector_profile_not_configured")
    source = Source(**body.model_dump())
    db.add(source)
    db.flush()
    audit(db, principal, source.vendor_id, source.id, "source.created", body.model_dump())
    db.commit()
    return source_json(source)


@router.get("/sources", tags=["sources"], response_model=Page[SourceRead])
def sources(db: Session = Depends(database), principal: Principal = Depends(require("source.read")),
            limit: int = Query(100, ge=1, le=500), after: UUID | None = None):
    query = visible(select(Source), principal)
    if after:
        query = query.where(Source.id > str(after))
    rows = db.scalars(query.order_by(Source.id).limit(limit + 1)).all()
    return {"data": [source_json(row) for row in rows[:limit]], "next_cursor": rows[limit-1].id if len(rows) > limit else None}


@router.get("/sources/{source_id}", tags=["sources"], response_model=SourceRead)
def source_detail(source_id: str, db: Session = Depends(database), principal: Principal = Depends(require("source.read"))):
    return source_json(get_source(db, source_id, principal))


@router.patch("/sources/{source_id}", tags=["sources"], response_model=SourceRead)
def update_source(source_id: str, body: SourcePatch, if_match: str | None = Header(None),
                  db: Session = Depends(database), principal: Principal = Depends(require("source.write"))):
    source = get_source(db, source_id, principal)
    if if_match is None:
        raise HTTPException(428, "if_match_required")
    if if_match != f'"{source.revision}"':
        raise HTTPException(412, "source_revision_conflict")
    changes = body.model_dump(exclude_unset=True)
    before = source_json(source)
    for key, value in changes.items():
        setattr(source, key, value)
    audit(db, principal, source.vendor_id, source.id, "source.updated",
          {key: {"before": before[key], "after": value} for key, value in changes.items()})
    db.commit()
    return source_json(source)


@router.put("/sources/{source_id}/state", tags=["sources"], response_model=SourceRead)
def source_state(source_id: str, body: SourceState, db: Session = Depends(database),
                 principal: Principal = Depends(require("source.approve"))):
    source = get_source(db, source_id, principal)
    if source.state != body.state:
        source.health_generation += 1
    source.state = body.state
    audit(db, principal, source.vendor_id, source.id, "source.state_changed", {"state": body.state})
    db.commit()
    return source_json(source)


def discover(source, request):
    if source.state == "disabled":
        raise HTTPException(409, "source_disabled")
    if source.adapter != "sentinel":
        raise HTTPException(422, "source_has_no_catalogue")
    config = request.app.state.settings.connectors.get(source.connector_profile)
    if config is None:
        raise HTTPException(503, "connector_profile_not_configured")
    return request.app.state.catalogue_fetcher(config, request.app.state.settings)


@router.post("/sources/{source_id}/test", tags=["sources"])
def test_source(source_id: str, request: Request, db: Session = Depends(database),
                principal: Principal = Depends(require("source.test"))):
    source = get_source(db, source_id, principal)
    try:
        entries = discover(source, request)
    except AdapterError as exc:
        raise HTTPException(502, exc.code) from None
    return {"source_id": source.id, "catalogue_accessible": True, "camera_count": len(entries),
            "media_tested": False, "sample": [entry.model_dump() for entry in entries[:3]]}


@router.post("/sources/{source_id}/sync", tags=["sources"])
def sync_source(source_id: str, body: SyncRequest, request: Request,
                db: Session = Depends(database), principal: Principal = Depends(require("source.sync"))):
    source = get_source(db, source_id, principal)
    if not body.dry_run and source.state != "approved":
        raise HTTPException(409, "source_approval_required")
    revision = source.revision
    try:
        entries = discover(source, request)
    except AdapterError as exc:
        if not body.dry_run:
            source.last_sync_error = exc.code
            audit(db, principal, source.vendor_id, source.id, "source.sync_failed", {"error": exc.code})
            db.commit()
        raise HTTPException(502, exc.code) from None
    if not entries and not body.allow_empty:
        raise HTTPException(409, "empty_catalogue_requires_allow_empty")
    # Conditional update serializes competing synchronizations across API replicas.
    # Fetching is outside the write lock; a stale fetch cannot overwrite a newer sync.
    if not body.dry_run:
        result = db.execute(Source.__table__.update().where(
            Source.id == source_id, Source.revision == revision, Source.state == "approved"
        ).values(revision=revision + 1, last_sync_at=utcnow(), last_sync_error=None, last_sync_count=len(entries)))
        if result.rowcount != 1:
            raise HTTPException(409, "source_changed_retry_sync")
    existing = {camera.external_id: camera for camera in db.scalars(select(Camera).where(Camera.source_id == source.id))}
    now = utcnow()
    ids = {entry.id for entry in entries}
    enrichment_count = sum(
        1 for entry in entries
        if entry.id not in existing or needs_sentinel_enrichment(existing[entry.id], entry.name)
    )
    result = {"source_id": source.id, "dry_run": body.dry_run, "discovered": len(entries),
              "created": sum(entry.id not in existing for entry in entries),
              "updated": sum(entry.id in existing and (existing[entry.id].discovered_name != entry.name or existing[entry.id].catalogue_status != "present") for entry in entries),
              "missing": sum(key not in ids for key in existing), "metadata_enriched": enrichment_count}
    if body.dry_run:
        return result
    for entry in entries:
        camera = existing.get(entry.id)
        if camera is None:
            camera = Camera(source_id=source.id, external_id=entry.id, discovered_name=entry.name)
            db.add(camera)
            db.flush()
        camera.discovered_name = entry.name
        camera.catalogue_status = "present"
        camera.last_seen_in_catalogue_at = now
        changes = enrich_sentinel_camera(camera, entry.name)
        if changes:
            audit(db, principal, source.vendor_id, camera.id, "camera.metadata_enriched", changes)
    for external_id, camera in existing.items():
        if external_id not in ids:
            camera.catalogue_status = "missing_from_source"
    audit(db, principal, source.vendor_id, source.id, "source.synced", result)
    db.commit()
    return result


@router.post("/cameras", status_code=201, tags=["cameras"], response_model=CameraRead)
def create_camera(body: CameraCreate, response: Response, db: Session = Depends(database),
                  principal: Principal = Depends(require("camera.metadata.write"))):
    if body.source_id:
        source = get_source(db, body.source_id, principal)
    else:
        source = vendor_camera_source(db, principal, create=True)
    if source.state == "disabled":
        raise HTTPException(409, "source_disabled")
    camera = Camera(source_id=source.id, external_id=body.external_id, discovered_name=body.name)
    apply_metadata(camera, body.model_dump(mode="json", exclude_unset=True, exclude={"source_id", "external_id"}))
    db.add(camera)
    db.flush()
    audit(db, principal, source.vendor_id, camera.id, "camera.created", body.model_dump(mode="json"))
    db.commit()
    response.headers["ETag"] = f'"{camera.revision}"'
    return camera_json(camera, source)


def camera_filters(query, source_id=None, vendor_id=None, department=None, q=None, mapped=None, bbox=None, catalogue_status=None, camera_type=None, postgis=False):
    if source_id:
        query = query.where(Camera.source_id == source_id)
    if vendor_id:
        query = query.where(Source.vendor_id == vendor_id)
    if department:
        query = query.where(func.coalesce(Camera.department, Source.department) == department)
    if catalogue_status:
        query = query.where(Camera.catalogue_status == catalogue_status)
    if camera_type:
        query = query.where(Camera.camera_type == camera_type)
    if q:
        escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(or_(func.coalesce(Camera.name_override, Camera.discovered_name).ilike(f"%{escaped}%", escape="\\"), Camera.external_id.ilike(f"%{escaped}%", escape="\\")))
    if mapped is not None:
        query = query.where(Camera.latitude.is_not(None) if mapped else Camera.latitude.is_(None))
    if bbox:
        try:
            west, south, east, north = [float(item) for item in bbox.split(",")]
            if not all(math.isfinite(v) for v in (west, south, east, north)) or not (-180 <= west <= east <= 180 and -90 <= south <= north <= 90):
                raise ValueError()
        except ValueError:
            raise HTTPException(422, "bbox_must_be_west_south_east_north_without_antimeridian_crossing") from None
        if postgis:
            query = query.where(text("registry_cameras.geom && ST_MakeEnvelope(:west,:south,:east,:north,4326)").bindparams(west=west, south=south, east=east, north=north))
        else:
            query = query.where(Camera.longitude.between(west, east), Camera.latitude.between(south, north))
    return query


def filters(source_id: str | None = None, vendor_id: str | None = None, department: str | None = None,
            q: str | None = Query(None, max_length=200), mapped: bool | None = None,
            bbox: str | None = None, catalogue_status: str | None = Query(None, pattern="^(present|missing_from_source)$"),
            camera_type: str | None = None):
    return dict(source_id=source_id, vendor_id=vendor_id, department=department, q=q, mapped=mapped,
                bbox=bbox, catalogue_status=catalogue_status, camera_type=camera_type)


@router.get("/cameras", tags=["cameras"], response_model=Page[CameraRead])
def cameras(db: Session = Depends(database), principal: Principal = Depends(require("camera.read")),
            options: dict = Depends(filters), limit: int = Query(100, ge=1, le=500), after: UUID | None = None):
    query = camera_filters(visible(select(Camera, Source).join(Source), principal, camera_scope=True).where(Camera.enabled.is_(True)), postgis=db.bind.dialect.name == "postgresql", **options)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    if after:
        query = query.where(Camera.id > str(after))
    rows = db.execute(query.order_by(Camera.id).limit(limit + 1)).all()
    return {"data": [camera_json(*row) for row in rows[:limit]], "total": total,
            "next_cursor": rows[limit-1][0].id if len(rows) > limit else None}


@router.get("/cameras/{camera_id}", tags=["cameras"], response_model=CameraRead)
def camera_detail(camera_id: str, response: Response, db: Session = Depends(database),
                  principal: Principal = Depends(require("camera.read"))):
    camera, source = get_camera(db, camera_id, principal)
    response.headers["ETag"] = f'"{camera.revision}"'
    return camera_json(camera, source)


@router.patch("/cameras/{camera_id}", tags=["cameras"], response_model=CameraRead)
def update_camera(camera_id: str, body: CameraPatch, response: Response,
                  if_match: str | None = Header(None), db: Session = Depends(database),
                  principal: Principal = Depends(authenticate)):
    camera, source = get_camera(db, camera_id, principal)
    etag(camera, if_match)
    before = camera_json(camera, source)
    changes = body.model_dump(mode="json", exclude_unset=True)
    technical = {"enabled", "stream_url", "stream_protocol", "streams", "infrastructure"}
    if technical.intersection(changes) and not principal.has("camera.technical.write"):
        raise HTTPException(403, "permission_required:camera.technical.write")
    if set(changes) - technical and not principal.has("camera.metadata.write"):
        raise HTTPException(403, "permission_required:camera.metadata.write")
    apply_metadata(camera, changes)
    db.flush()
    audit(db, principal, source.vendor_id, camera.id, "camera.updated",
          {key: {"before": before.get(key), "after": value} for key, value in changes.items()})
    db.commit()
    response.headers["ETag"] = f'"{camera.revision}"'
    return camera_json(camera, source)


@router.delete("/cameras/{camera_id}", status_code=204, tags=["cameras"])
def remove_camera(camera_id: str, db: Session = Depends(database),
                  principal: Principal = Depends(require("camera.technical.write"))):
    camera, source = get_camera(db, camera_id, principal)
    if not camera.enabled:
        return
    camera.enabled = False
    camera.health_generation += 1
    audit(db, principal, source.vendor_id, camera.id, "camera.removed", {"enabled": {"before": True, "after": False}})
    db.commit()


@router.get("/cameras/{camera_id}/streams", tags=["cameras"])
def camera_streams(camera_id: str, request: Request, db: Session = Depends(database),
                   principal: Principal = Depends(require("camera.stream.view"))):
    camera, source = get_camera(db, camera_id, principal)
    streams = stored_streams(camera)
    if source.adapter == "sentinel":
        config = request.app.state.settings.connectors.get(source.connector_profile)
        if config is None:
            raise HTTPException(503, "connector_profile_not_configured")
        endpoints = public_sentinel_endpoints(config, camera.external_id)
        managed = [
            {"id": "sentinel-rtsp", "label": "RTSP stream", "protocol": "rtsp", "url": endpoints["rtsp_url"], "managed": True,
             "auth": "server_credentials"},
            {"id": "sentinel-hls", "label": "HLS stream", "protocol": "hls", "url": endpoints["hls_url"], "managed": True,
             "auth": "portal_session"},
            {"id": "sentinel-whep", "label": "WebRTC stream", "protocol": "whep", "url": endpoints["whep_url"], "managed": True},
        ]
        all_streams = managed + streams
        return {"camera_id": camera.id, "source_state": source.state, "catalogue_status": camera.catalogue_status,
                "protocols": list(dict.fromkeys(item["protocol"] for item in all_streams)), "playback_available": True,
                "profile": "main", "streams": all_streams,
                "endpoints": {"primary_url": endpoints["hls_url"], "rtsp_url": endpoints["rtsp_url"],
                              "hls_url": endpoints["hls_url"], "whep_url": endpoints["whep_url"]}}
    return {"camera_id": camera.id, "source_state": source.state, "catalogue_status": camera.catalogue_status,
            "protocols": list(dict.fromkeys(item["protocol"] for item in streams)),
            "playback_available": bool(streams), "profile": "main", "streams": streams,
            "endpoints": {"primary_url": streams[0]["url"], "protocol": streams[0]["protocol"]} if streams else {}}


@router.get("/cameras/{camera_id}/audit", tags=["cameras"])
def camera_audit(camera_id: str, db: Session = Depends(database), principal: Principal = Depends(require("audit.read")),
                 limit: int = Query(100, ge=1, le=500), after: UUID | None = None):
    camera, source = get_camera(db, camera_id, principal)
    query = select(Audit).where(Audit.resource_id == camera.id, Audit.vendor_id == source.vendor_id)
    if after:
        query = query.where(Audit.id > str(after))
    rows = db.scalars(query.order_by(Audit.id).limit(limit + 1)).all()
    return {"data": [{"id": r.id, "actor": r.actor, "action": r.action, "changes": r.changes,
                       "created_at": serial_time(r.created_at)} for r in rows[:limit]],
            "next_cursor": rows[limit-1].id if len(rows) > limit else None}


@router.post("/camera-imports", tags=["imports"])
def import_cameras(body: CameraImport, db: Session = Depends(database),
                   principal: Principal = Depends(require("camera.import"))):
    source = get_source(db, body.source_id, principal) if body.source_id else vendor_camera_source(
        db, principal, create=not body.dry_run)
    if source and source.state == "disabled":
        raise HTTPException(409, "source_disabled")
    ids = [row.external_id for row in body.rows]
    if len(ids) != len(set(ids)):
        raise HTTPException(422, "duplicate_external_ids_in_import")
    existing = set(db.scalars(select(Camera.external_id).where(
        Camera.source_id == source.id, Camera.external_id.in_(ids)))) if source else set()
    # Create-only imports cannot overwrite existing manually curated metadata accidentally.
    result = {"source_id": source.id if source else None, "dry_run": body.dry_run,
              "created": len(ids) - len(existing), "skipped": len(existing),
              "rows": [{"row": i + 1, "external_id": row.external_id, "action": "skip_existing" if row.external_id in existing else "create"} for i, row in enumerate(body.rows)]}
    if body.dry_run:
        return result
    for row in body.rows:
        if row.external_id in existing:
            continue
        camera = Camera(source_id=source.id, external_id=row.external_id, discovered_name=row.name)
        apply_metadata(camera, row.model_dump(mode="json", exclude_unset=True, exclude={"external_id"}))
        db.add(camera)
        db.flush()
        audit(db, principal, source.vendor_id, camera.id, "camera.imported", row.model_dump(mode="json"))
    audit(db, principal, source.vendor_id, source.id, "source.metadata_imported", {"created": result["created"], "skipped": result["skipped"]})
    db.commit()
    return result


@router.get("/map/cameras", tags=["GIS"])
def camera_map(options: dict = Depends(filters), db: Session = Depends(database),
               principal: Principal = Depends(require("topology.read")),
               limit: int = Query(500, ge=1, le=2000), after: UUID | None = None):
    query = camera_filters(visible(select(Camera, Source).join(Source), principal, camera_scope=True), postgis=db.bind.dialect.name == "postgresql", **options).where(
        Camera.latitude.is_not(None), Camera.enabled.is_(True))
    if after:
        query = query.where(Camera.id > str(after))
    rows = db.execute(query.order_by(Camera.id).limit(limit + 1)).all()
    features = []
    for camera, source in rows[:limit]:
        data = camera_json(camera, source)
        geometry = data.pop("geometry")
        features.append({"type": "Feature", "id": camera.id, "geometry": geometry, "properties": data})
    return {"type": "FeatureCollection", "features": features,
            "next_cursor": rows[limit-1][0].id if len(rows) > limit else None}


@router.get("/camera-export", tags=["imports"])
def export_cameras(options: dict = Depends(filters), db: Session = Depends(database),
                   principal: Principal = Depends(require("camera.export"))):
    query = camera_filters(visible(select(Camera, Source).join(Source), principal, camera_scope=True), postgis=db.bind.dialect.name == "postgresql", **options).where(
        Camera.enabled.is_(True)).order_by(Camera.id).limit(10001)
    rows = db.execute(query).all()
    if len(rows) > 10000:
        raise HTTPException(422, "export_too_large_narrow_filters")
    buffer = io.StringIO()
    output = csv.writer(buffer)
    fields = ["id", "external_id", "source_id", "name", "location", "latitude", "longitude", "department", "camera_type", "ownership"]
    output.writerow(fields)
    for camera, source in rows:
        data = camera_json(camera, source)
        data.update(latitude=camera.latitude, longitude=camera.longitude)
        values = []
        for field in fields:
            value = data.get(field)
            if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
                value = "'" + value
            values.append(value)
        output.writerow(values)
    for vendor_id in {source.vendor_id for _, source in rows}:
        audit(db, principal, vendor_id, vendor_id, "cameras.exported", {"rows": sum(s.vendor_id == vendor_id for _, s in rows)})
    db.commit()
    return Response(buffer.getvalue(), media_type="text/csv", headers={"Content-Disposition": 'attachment; filename="cameras.csv"'})


@router.post("/sources/{source_id}/camera-imports/csv", tags=["imports"])
def import_csv(source_id: str, content: str = Body(media_type="text/csv", max_length=2_000_000),
               dry_run: bool = True, db: Session = Depends(database),
               principal: Principal = Depends(require("camera.import"))):
    get_source(db, source_id, principal)
    reader = csv.DictReader(io.StringIO(content.lstrip("\ufeff")), strict=True)
    columns = {"external_id", "name", "location", "latitude", "longitude", "location_provenance", "camera_type", "ownership", "department"}
    if not reader.fieldnames or not {"external_id", "name"}.issubset(reader.fieldnames) or set(reader.fieldnames) - columns or len(set(reader.fieldnames)) != len(reader.fieldnames):
        raise HTTPException(422, "csv_invalid_columns")
    rows, errors = [], []
    try:
        for index, row in enumerate(reader, 1):
            if index > 1000:
                raise HTTPException(422, "csv_maximum_1000_rows")
            if None in row or any(value is None for value in row.values()):
                errors.append({"row": index, "error": "column_count_mismatch"})
                continue
            data = {key: value.strip() for key, value in row.items() if value.strip()}
            latitude, longitude, provenance = (data.pop(key, None) for key in ("latitude", "longitude", "location_provenance"))
            if any(value is not None for value in (latitude, longitude, provenance)):
                data["coordinates"] = {"latitude": latitude, "longitude": longitude, "provenance": provenance}
            try:
                rows.append(ImportRow.model_validate(data))
            except ValidationError as exc:
                errors.append({"row": index, "errors": [{"field": ".".join(map(str, e["loc"])), "type": e["type"]} for e in exc.errors()]})
    except csv.Error:
        raise HTTPException(422, "csv_malformed") from None
    if errors:
        raise HTTPException(422, {"code": "csv_validation_failed", "rows": errors[:100], "error_count": len(errors), "committed": False})
    if not rows:
        raise HTTPException(422, "csv_empty")
    return import_cameras(CameraImport(source_id=source_id, rows=rows, dry_run=dry_run), db, principal)
