import hashlib
import secrets
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

from .models import (ApiKey, DashboardRoleAssignment, DashboardSession, DashboardUser,
                     Vendor, VendorSession, VendorUser, utcnow)
from .rbac import Scope, permissions_for_roles

bearer = HTTPBearer(auto_error=False)


def digest(token: str):
    return hashlib.sha256(token.encode()).hexdigest()


def normalize_email(email: str):
    return email.strip().casefold()


def hash_password(password: str):
    salt = secrets.token_bytes(16)
    derived = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1, dklen=32)
    return f"scrypt$16384$8$1${salt.hex()}${derived.hex()}"


def verify_password(password: str, encoded: str):
    try:
        algorithm, n, r, p, salt, expected = encoded.split("$")
        if algorithm != "scrypt":
            return False
        actual = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p), dklen=len(bytes.fromhex(expected)))
        return secrets.compare_digest(actual, bytes.fromhex(expected))
    except (ValueError, TypeError):
        return False


@dataclass(frozen=True)
class Principal:
    actor: str
    role: str
    vendor_id: str | None = None
    user_id: str | None = None
    email: str | None = None
    session_id: str | None = None
    roles: tuple[str, ...] = ()
    permissions: frozenset[str] = frozenset()
    scopes: tuple[Scope, ...] = ()
    display_name: str | None = None

    def has(self, permission: str):
        return permission in self.permissions

    def scope_ids(self, scope_type: str):
        return {scope.id for scope in self.scopes if scope.type == scope_type and scope.id}


def principal(actor, role, vendor_id=None, user_id=None, email=None, session_id=None, roles=None, scopes=None,
              display_name=None):
    roles = tuple(roles or (role,))
    scopes = tuple(scopes or ((Scope("vendor", vendor_id),) if vendor_id else (Scope("global"),)))
    return Principal(actor, role, vendor_id, user_id, email, session_id, roles,
                     permissions_for_roles(roles), scopes, display_name)


def authenticate(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    token = credentials.credentials if credentials else request.cookies.get("synetra_session")
    if not token:
        raise HTTPException(401, "authentication_required", headers={"WWW-Authenticate": "Bearer"})
    settings = request.app.state.settings
    if secrets.compare_digest(digest(token), digest(settings.admin_token)):
        return principal("admin", "master_admin")
    if settings.reader_token and secrets.compare_digest(digest(token), digest(settings.reader_token)):
        return principal("dashboard-reader", "service_reader")
    with request.app.state.sessions() as db:
        key = db.scalar(select(ApiKey).join(Vendor).where(
            ApiKey.digest == digest(token), ApiKey.revoked.is_(False), Vendor.active.is_(True)))
        if key:
            return principal(f"key:{key.id}", "vendor", key.vendor_id)
        row = db.execute(select(VendorSession, VendorUser).join(VendorUser).join(Vendor).where(
            VendorSession.token_digest == digest(token), VendorSession.revoked_at.is_(None),
            VendorSession.expires_at > utcnow(), VendorUser.active.is_(True), Vendor.active.is_(True))).first()
        if row:
            session, user = row
            return principal(f"vendor-user:{user.id}", "vendor", user.vendor_id, user.id, user.email, session.id,
                             display_name=user.display_name)
        dashboard_row = db.execute(select(DashboardSession, DashboardUser).join(DashboardUser).where(
            DashboardSession.token_digest == digest(token), DashboardSession.revoked_at.is_(None),
            DashboardSession.expires_at > utcnow(), DashboardUser.active.is_(True))).first()
        if dashboard_row:
            session, user = dashboard_row
            assignments = db.scalars(select(DashboardRoleAssignment).where(
                DashboardRoleAssignment.user_id == user.id).order_by(DashboardRoleAssignment.role)).all()
            roles = tuple(dict.fromkeys(assignment.role for assignment in assignments))
            scopes = tuple(Scope(assignment.scope_type, assignment.scope_id or None) for assignment in assignments)
            if roles:
                return principal(f"dashboard-user:{user.id}", roles[0], None, user.id, user.email,
                                 session.id, roles, scopes, user.display_name)
    raise HTTPException(401, "invalid_credentials", headers={"WWW-Authenticate": "Bearer"})


def admin(principal: Principal = Depends(authenticate)):
    if not principal.has("user.manage"):
        raise HTTPException(403, "admin_required")
    return principal


def writer(principal: Principal = Depends(authenticate)):
    if not ({"camera.metadata.write", "camera.technical.write", "camera.import", "source.write"} & principal.permissions):
        raise HTTPException(403, "write_permission_required")
    return principal


def require(permission: str):
    def dependency(current: Principal = Depends(authenticate)):
        if not current.has(permission):
            raise HTTPException(403, f"permission_required:{permission}")
        return current
    return dependency
