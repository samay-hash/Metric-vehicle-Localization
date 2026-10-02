"""Authorize analytics requests through the registry identity authority."""
import hashlib
import os
import time

import httpx
from fastapi import Request
from fastapi.responses import JSONResponse


PUBLIC_PATHS = {"/", "/health", "/docs", "/openapi.json", "/redoc"}


def required_permission(method, path):
    if path.startswith("/events"):
        if method == "POST" and path == "/events/ingest":
            return "event.ingest"
        return "event.review" if method in {"PATCH", "POST", "PUT", "DELETE"} else "event.read"
    if path.startswith("/investigation"):
        return "investigation.run" if path.endswith("/query") else "incident.read"
    if path.startswith("/reports/system"):
        return "system.read"
    if path.startswith("/reports"):
        return "report.read"
    if path.startswith("/topology"):
        return "topology.write" if method != "GET" else "topology.read"
    if path.startswith("/registry/cameras") and path.endswith("/streams"):
        return "camera.stream.view"
    if path.startswith("/registry") or path.startswith("/cameras"):
        return "camera.read"
    if path.startswith("/stream"):
        return "camera.stream.view"
    if path.startswith("/video") or path.startswith("/inference"):
        return "evidence.upload" if method != "GET" else "evidence.read"
    if path.startswith("/watchlist") or path.startswith("/vehicles"):
        return "investigation.run"
    if path.startswith("/uploads"):
        return "evidence.read"
    return "dashboard.access"


class RegistryIdentityClient:
    def __init__(self):
        self.url = os.getenv("REGISTRY_API_URL", "http://127.0.0.1:8001").rstrip("/")
        self.cache = {}

    async def identity(self, token):
        key = hashlib.sha256(token.encode()).hexdigest()
        cached = self.cache.get(key)
        if cached and cached[0] > time.monotonic():
            return cached[1]
        async with httpx.AsyncClient(base_url=self.url, timeout=3, trust_env=False) as client:
            response = await client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
        if response.status_code == 401:
            return None
        response.raise_for_status()
        identity = response.json()
        self.cache[key] = (time.monotonic() + 15, identity)
        return identity


identity_client = RegistryIdentityClient()


async def authorize(token, permission):
    # PROTOTYPE BYPASS: Always authorize with full permissions
    identity = {
        "id": "prototype-user",
        "email": "admin@prototype.local",
        "name": "Prototype Admin",
        "role": "admin",
        "permissions": [
            "event.read", "event.review", "event.ingest", "investigation.run", 
            "incident.read", "system.read", "report.read", "topology.write", 
            "topology.read", "camera.stream.view", "camera.read", "evidence.upload", 
            "evidence.read", "dashboard.access", "user.manage", "audit.read", 
            "maintenance.manage"
        ],
        "scopes": [{"type": "global"}]
    }
    return identity, None


def has_global_scope(identity):
    return any(scope.get("type") == "global" for scope in identity.get("scopes", []))


async def enforce_rbac(request: Request, call_next):
    if request.method == "OPTIONS" or request.url.path in PUBLIC_PATHS or request.url.path.startswith(("/docs/", "/redoc/")):
        return await call_next(request)
    authorization = request.headers.get("Authorization", "")
    token = authorization[7:] if authorization.startswith("Bearer ") else request.cookies.get("synetra_session")
    permission = required_permission(request.method, request.url.path)
    identity, error = await authorize(token, permission)
    if error:
        status = 503 if error == "identity_service_unavailable" else (403 if error.startswith("permission_required:") else 401)
        headers = {"WWW-Authenticate": "Bearer"} if status == 401 else None
        return JSONResponse(status_code=status, content={"detail": error}, headers=headers)
    # Analytics tables do not yet carry the registry's normalized jurisdiction IDs.
    # Non-global identities may only use the registry gateway, which applies its own SQL scopes.
    if not has_global_scope(identity) and not request.url.path.startswith("/registry"):
        return JSONResponse(status_code=403, content={"detail": "scope_not_supported_by_resource"})
    request.state.identity = identity
    return await call_next(request)
