"""Dashboard gateway to the registry; registry credentials remain server-side."""
from fastapi import APIRouter, HTTPException, Query

from services.registry_client import RegistryClientError, camera_streams, registry_get

router = APIRouter(prefix="/registry", tags=["registry gateway"])


def unavailable(exc: RegistryClientError):
    code = str(exc)
    status = 404 if code == "registry_camera_not_found" else 503
    raise HTTPException(status, code) from None


@router.get("/cameras")
def cameras(limit: int = Query(100, ge=1, le=500), after: str | None = None):
    try:
        return registry_get("/api/v1/cameras", {"limit": limit, **({"after": after} if after else {})})
    except RegistryClientError as exc:
        unavailable(exc)


@router.get("/cameras/{camera_id}/streams")
def streams(camera_id: str):
    try:
        return camera_streams(camera_id)
    except RegistryClientError as exc:
        unavailable(exc)
