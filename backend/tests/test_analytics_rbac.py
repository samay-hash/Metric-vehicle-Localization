from fastapi import FastAPI
import asyncio

from fastapi.testclient import TestClient

import rbac_middleware


def test_analytics_middleware_enforces_permission_and_accepts_session_cookie(monkeypatch):
    async def identity(token):
        if token == "valid-reader":
            return {"permissions": ["event.read"], "scopes": [{"type": "global", "id": None}]}
        if token == "valid-reviewer":
            return {"permissions": ["event.read", "event.review"], "scopes": [{"type": "global", "id": None}]}
        if token == "scoped-reader":
            return {"permissions": ["event.read", "camera.read"],
                    "scopes": [{"type": "department", "id": "Ahmedabad City"}]}
        return None

    monkeypatch.setattr(rbac_middleware.identity_client, "identity", identity)
    app = FastAPI()
    app.middleware("http")(rbac_middleware.enforce_rbac)

    @app.get("/health")
    def health():
        return {"ok": True}

    @app.get("/events")
    def events():
        return {"data": []}

    @app.patch("/events/one")
    def update_event():
        return {"updated": True}

    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/events").status_code == 401
        assert client.get("/events", headers={"Authorization": "Bearer invalid"}).status_code == 401
        assert client.get("/events", headers={"Authorization": "Bearer valid-reader"}).status_code == 200
        assert client.patch("/events/one", headers={"Authorization": "Bearer valid-reader"}).status_code == 403
        assert client.patch("/events/one", headers={"Authorization": "Bearer valid-reviewer"}).status_code == 200
        assert client.get("/events", headers={"Authorization": "Bearer scoped-reader"}).status_code == 403
        assert client.get("/registry/cameras", headers={"Authorization": "Bearer scoped-reader"}).status_code == 404
        client.cookies.set("synetra_session", "valid-reader")
        assert client.get("/events").status_code == 200


def test_permission_map_covers_sensitive_routes():
    assert rbac_middleware.required_permission("GET", "/stream/camera") == "camera.stream.view"
    assert rbac_middleware.required_permission("POST", "/video/upload") == "evidence.upload"
    assert rbac_middleware.required_permission("POST", "/topology/") == "topology.write"
    assert rbac_middleware.required_permission("GET", "/reports/system/stats") == "system.read"


def test_shared_authorizer_protects_websocket_handshakes(monkeypatch):
    async def identity(token):
        return {"permissions": ["event.read"], "scopes": [{"type": "global", "id": None}]} if token == "event-token" else None

    monkeypatch.setattr(rbac_middleware.identity_client, "identity", identity)
    allowed, error = asyncio.run(rbac_middleware.authorize("event-token", "event.read"))
    assert error is None
    assert allowed["permissions"] == ["event.read"]
    denied, error = asyncio.run(rbac_middleware.authorize("event-token", "system.manage"))
    assert denied is None
    assert error == "permission_required:system.manage"
    missing, error = asyncio.run(rbac_middleware.authorize(None, "event.read"))
    assert missing is None
    assert error == "authentication_required"
