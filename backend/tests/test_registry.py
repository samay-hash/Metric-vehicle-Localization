import json
from pathlib import Path

import httpx
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from registry.adapters import AdapterError, fetch_sentinel, resolve_sentinel
from registry.auth import hash_password
from registry.app import create_app
from registry.config import Connector, Settings
from registry.models import VendorSession, VendorUser, utcnow
from registry.schemas import CatalogueEntry

ADMIN = "test-admin-" + "a" * 32
READER = "test-reader-" + "b" * 32
CONNECTOR = Connector(
    catalogue_url="https://provider.example/cameras.json", login_url="https://provider.example/auth/login",
    credentials_prefix="TEST_SENTINEL", rtsp_origin="rtsp://gateway.example:8554",
    hls_origin="https://provider.example", whep_origin="http://gateway.example:8889",
    rtsp_path_template="/stream/{camera_id}", hls_path_template="/live/stream/{camera_id}/index.m3u8",
    whep_path_template="/stream/{camera_id}/whep",
)


@pytest.fixture
def setup(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'registry.sqlite3'}"
    monkeypatch.setenv("REGISTRY_DATABASE_URL", url)
    config = Config(str(Path(__file__).resolve().parents[1] / "registry-alembic.ini"))
    command.upgrade(config, "head")
    entries = [CatalogueEntry(id="cam01", name="Camera One"), CatalogueEntry(id="cam02", name="Camera Two")]
    settings = Settings(database_url=url, admin_token=ADMIN, reader_token=READER, connectors={"sentinel": CONNECTOR})
    app = create_app(settings, catalogue_fetcher=lambda *args: list(entries))
    with TestClient(app, headers={"Authorization": f"Bearer {ADMIN}"}) as client:
        yield client, entries, settings


def source(client, slug="vendor", adapter="sentinel"):
    vendor = client.post("/api/v1/vendors", json={"slug": slug, "name": slug.title()})
    assert vendor.status_code == 201, vendor.text
    payload = {"vendor_id": vendor.json()["id"], "slug": "source", "name": "Source", "adapter": adapter}
    if adapter == "sentinel":
        payload["connector_profile"] = "sentinel"
    response = client.post("/api/v1/sources", json=payload)
    assert response.status_code == 201, response.text
    src = response.json()
    assert client.put(f'/api/v1/sources/{src["id"]}/state', json={"state": "approved"}).status_code == 200
    return src


def sync(client, source_id, **kwargs):
    return client.post(f"/api/v1/sources/{source_id}/sync", json={"dry_run": False, **kwargs})


def cameras(client, **kwargs):
    return client.get("/api/v1/cameras", params=kwargs).json()["data"]


def test_health_auth_and_openapi(setup):
    client, _, _ = setup
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/api/v1/cameras", headers={"Authorization": ""}).status_code == 401
    assert client.get("/api/v1/cameras", headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert "/api/v1/map/cameras" in client.get("/openapi.json").json()["paths"]


def test_sync_is_idempotent_and_preserves_manual_metadata(setup):
    client, entries, _ = setup
    src = source(client)
    preview = client.post(f'/api/v1/sources/{src["id"]}/sync', json={}).json()
    assert preview["created"] == 2
    assert cameras(client) == []
    assert sync(client, src["id"]).json()["created"] == 2
    before = {c["external_id"]: c for c in cameras(client)}
    camera = before["cam01"]
    update = client.patch(f'/api/v1/cameras/{camera["id"]}', headers={"If-Match": f'"{camera["revision"]}"'}, json={
        "name": "Operator name", "coordinates": {"latitude": 23.01, "longitude": 72.57, "provenance": "site survey"}})
    assert update.status_code == 200, update.text
    entries[0] = CatalogueEntry(id="cam01", name="Renamed upstream")
    assert sync(client, src["id"]).status_code == 200
    after = {c["external_id"]: c for c in cameras(client)}
    assert after["cam01"]["id"] == camera["id"]
    assert after["cam01"]["name"] == "Operator name"
    assert after["cam01"]["vendor_name"] == "Renamed upstream"
    assert after["cam01"]["geometry"]["coordinates"] == [72.57, 23.01]
    assert after["cam02"]["coordinates"] is None
    assert after["cam02"]["health"]["connectivity"] == "unknown"
    assert sync(client, src["id"]).json()["created"] == 0


def test_missing_camera_and_empty_catalogue_guard(setup):
    client, entries, _ = setup
    src = source(client)
    sync(client, src["id"])
    entries.pop()
    assert sync(client, src["id"]).json()["missing"] == 1
    assert len(cameras(client, catalogue_status="missing_from_source")) == 1
    entries.clear()
    assert sync(client, src["id"]).status_code == 409
    assert len(cameras(client, catalogue_status="present")) == 1
    assert sync(client, src["id"], allow_empty=True).status_code == 200
    assert len(cameras(client)) == 2
    assert len(cameras(client, catalogue_status="missing_from_source")) == 2


def test_failed_sync_never_marks_cameras_missing(setup):
    client, _, _ = setup
    src = source(client)
    sync(client, src["id"])
    def broken(*args):
        raise AdapterError("catalogue_not_json")
    client.app.state.catalogue_fetcher = broken
    assert sync(client, src["id"]).status_code == 502
    assert len(cameras(client, catalogue_status="present")) == 2
    assert client.get(f'/api/v1/sources/{src["id"]}').json()["last_sync_error"] == "catalogue_not_json"


def test_vendor_scope_and_revocation(setup):
    client, _, _ = setup
    one, two = source(client, "one"), source(client, "two")
    sync(client, one["id"])
    sync(client, two["id"])
    other = cameras(client, source_id=two["id"])[0]
    key = client.post(f'/api/v1/vendors/{one["vendor_id"]}/api-keys', json={"label": "ingestor"}).json()
    headers = {"Authorization": f'Bearer {key["token"]}'}
    response = client.get("/api/v1/cameras", headers=headers)
    assert response.json()["total"] == 2
    assert {c["vendor_id"] for c in response.json()["data"]} == {one["vendor_id"]}
    assert client.get(f'/api/v1/cameras/{other["id"]}', headers=headers).status_code == 404
    assert client.get(f'/api/v1/cameras/{other["id"]}/audit', headers=headers).status_code == 404
    assert client.post(f'/api/v1/sources/{two["id"]}/sync', json={}, headers=headers).status_code == 404
    assert client.put(f'/api/v1/sources/{one["id"]}/state', json={"state": "disabled"}, headers=headers).status_code == 403
    assert client.post("/api/v1/vendors", json={"slug": "evil", "name": "Evil"}, headers=headers).status_code == 403
    assert client.delete(f'/api/v1/vendors/{one["vendor_id"]}/api-keys/{key["id"]}').status_code == 204
    assert client.get("/api/v1/cameras", headers=headers).status_code == 401


def test_reader_cannot_write(setup):
    client, _, _ = setup
    src = source(client)
    headers = {"Authorization": f"Bearer {READER}"}
    assert client.get("/api/v1/cameras", headers=headers).status_code == 200
    assert client.post(f'/api/v1/sources/{src["id"]}/sync', json={}, headers=headers).status_code == 403


def test_optimistic_concurrency_audit_and_gis(setup):
    client, _, _ = setup
    src = source(client)
    sync(client, src["id"])
    camera = cameras(client)[0]
    url = f'/api/v1/cameras/{camera["id"]}'
    assert client.patch(url, json={"location": "junction"}).status_code == 428
    headers = {"If-Match": f'"{camera["revision"]}"'}
    patched = client.patch(url, headers=headers, json={"coordinates": {"latitude": 23, "longitude": 72, "provenance": "survey"}})
    assert patched.status_code == 200
    assert client.patch(url, headers=headers, json={"location": "stale overwrite"}).status_code == 412
    assert len(cameras(client, mapped=True)) == 1
    assert len(cameras(client, mapped=False)) == 1
    geo = client.get("/api/v1/map/cameras", params={"bbox": "71,22,73,24"}).json()
    assert geo["features"][0]["geometry"]["coordinates"] == [72, 23]
    assert client.get("/api/v1/map/cameras", params={"bbox": "0,0,1,1"}).json()["features"] == []
    assert client.get("/api/v1/map/cameras", params={"bbox": "nan,0,1,1"}).status_code == 422
    assert client.get(url + "/audit").json()["data"][0]["action"] == "camera.updated"


def test_import_validation_pagination_and_csv_injection(setup):
    client, _, _ = setup
    src = source(client, adapter="manual")
    body = {"source_id": src["id"], "rows": [{"external_id": "a", "name": "=FORMULA()"}, {"external_id": "b", "name": "Second"}]}
    assert client.post("/api/v1/camera-imports", json=body).json()["created"] == 2
    assert cameras(client) == []
    body["dry_run"] = False
    assert client.post("/api/v1/camera-imports", json=body).status_code == 200
    assert client.post("/api/v1/camera-imports", json=body).json()["skipped"] == 2
    first = client.get("/api/v1/cameras", params={"limit": 1}).json()
    second = client.get("/api/v1/cameras", params={"limit": 1, "after": first["next_cursor"]}).json()
    assert first["data"][0]["id"] != second["data"][0]["id"]
    assert second["next_cursor"] is None
    assert "'=FORMULA()" in client.get("/api/v1/camera-export").text
    body["rows"][0]["coordinates"] = {"latitude": 200, "longitude": 0, "provenance": "bad"}
    assert client.post("/api/v1/camera-imports", json=body).status_code == 422


def test_sources_are_approved_and_destinations_are_server_controlled(setup):
    client, _, _ = setup
    src = source(client)
    client.put(f'/api/v1/sources/{src["id"]}/state', json={"state": "disabled"})
    assert sync(client, src["id"]).status_code == 409
    assert client.post(f'/api/v1/sources/{src["id"]}/test').status_code == 409
    payload = {"vendor_id": src["vendor_id"], "slug": "evil", "name": "Evil", "adapter": "sentinel", "connector_profile": "missing"}
    assert client.post("/api/v1/sources", json=payload).status_code == 422
    payload["password"] = "do-not-echo-secret"
    response = client.post("/api/v1/sources", json=payload)
    assert "do-not-echo-secret" not in response.text


def test_no_secret_or_invented_playback_in_read_responses(setup):
    client, _, _ = setup
    src = source(client)
    sync(client, src["id"])
    camera = cameras(client)[0]
    for path in ("/api/v1/cameras", "/api/v1/sources", f'/api/v1/cameras/{camera["id"]}/streams'):
        response = client.get(path)
        assert "password" not in response.text and "rtsp://" not in response.text
        assert response.headers["cache-control"] == "no-store"
    streams = client.get(f'/api/v1/cameras/{camera["id"]}/streams').json()
    assert streams["playback_available"] is True
    assert streams["endpoints"]["rtsp"] == "server_managed"


@pytest.mark.parametrize("scenario,code", [
    ("html", "catalogue_not_json"), ("redirect", "source_authentication_failed"),
    ("invalid", "catalogue_invalid"), ("duplicate", "catalogue_duplicate_ids"),
    ("oversize", "catalogue_too_large"), ("unsafe_id", "catalogue_invalid"),
])
def test_adapter_rejects_bad_catalogues(monkeypatch, scenario, code):
    monkeypatch.setenv("TEST_SENTINEL_EMAIL", "user@example.com")
    monkeypatch.setenv("TEST_SENTINEL_PASSWORD", "private-value")
    settings = Settings("sqlite:///:memory:", ADMIN, max_catalogue_bytes=200)
    def handler(request):
        if request.method == "POST":
            return httpx.Response(303, headers={"set-cookie": "session=ok; Path=/", "location": "/"})
        assert request.headers["cookie"] == "session=ok"
        if scenario == "html": return httpx.Response(200, text="login form")
        if scenario == "redirect": return httpx.Response(302, headers={"location": "https://unapproved.example"})
        if scenario == "invalid": return httpx.Response(200, json={"cameras": []})
        if scenario == "duplicate": return httpx.Response(200, json=[{"id": "cam01", "name": "One"}] * 2)
        if scenario == "oversize": return httpx.Response(200, content=b" " * 201, headers={"content-type": "application/json"})
        return httpx.Response(200, json=[{"id": "../admin", "name": "Unsafe"}])
    with pytest.raises(AdapterError) as caught:
        fetch_sentinel(CONNECTOR, settings, transport=httpx.MockTransport(handler))
    assert caught.value.code == code


def test_adapter_authenticates_and_encodes_worker_credentials(monkeypatch):
    monkeypatch.setenv("TEST_SENTINEL_EMAIL", "user@example.com")
    monkeypatch.setenv("TEST_SENTINEL_PASSWORD", "a:b@c/?")
    def handler(request):
        if request.method == "POST":
            return httpx.Response(303, headers={"set-cookie": "session=ok; Path=/"})
        return httpx.Response(200, json=[{"id": "cam01", "name": "One"}])
    entries = fetch_sentinel(CONNECTOR, Settings("sqlite:///:memory:", ADMIN), httpx.MockTransport(handler))
    assert entries[0].id == "cam01"
    connection = resolve_sentinel(CONNECTOR, entries[0].id)
    assert "user%40example.com:a%3Ab%40c%2F%3F@" in connection["rtsp_url"]
    assert connection["rtsp_transport"] == "tcp"


def test_config_rejects_credential_redirects():
    with pytest.raises(ValueError):
        Connector(catalogue_url="https://elsewhere.example/cameras.json", login_url=CONNECTOR.login_url,
                  credentials_prefix="TEST_SENTINEL", rtsp_origin=CONNECTOR.rtsp_origin,
                  hls_origin=CONNECTOR.hls_origin, whep_origin=CONNECTOR.whep_origin,
                  rtsp_path_template=CONNECTOR.rtsp_path_template, hls_path_template=CONNECTOR.hls_path_template,
                  whep_path_template=CONNECTOR.whep_path_template)


def test_csv_import_is_atomic_and_has_row_errors(setup):
    client, _, _ = setup
    src = source(client, adapter="manual")
    path = f'/api/v1/sources/{src["id"]}/camera-imports/csv'
    headers = {"Content-Type": "text/csv"}
    invalid = "external_id,name,latitude,longitude,location_provenance\na,First,23,72,survey\nb,Invalid,123,72,survey\n"
    response = client.post(path + "?dry_run=false", content=invalid, headers=headers)
    assert response.status_code == 422, response.text
    assert response.json()["detail"]["rows"][0]["row"] == 2
    assert cameras(client) == []
    valid = "external_id,name,latitude,longitude,location_provenance\na,First,23,72,survey\nb,Second,,,\n"
    assert client.post(path, content=valid, headers=headers).json()["created"] == 2
    assert cameras(client) == []
    assert client.post(path + "?dry_run=false", content=valid, headers=headers).status_code == 200
    assert len(cameras(client, mapped=True)) == 1
    assert len(cameras(client, mapped=False)) == 1


def test_manual_creation_uniqueness_and_null_clear(setup):
    client, _, _ = setup
    src = source(client, adapter="manual")
    payload = {"source_id": src["id"], "external_id": "x", "name": "Physical camera",
               "coordinates": {"latitude": 0, "longitude": 0, "provenance": "survey"}}
    response = client.post("/api/v1/cameras", json=payload)
    assert response.status_code == 201
    assert "coordinates" not in response.json()["missing_metadata"]
    assert client.post("/api/v1/cameras", json=payload).status_code == 409
    camera = response.json()
    cleared = client.patch(f'/api/v1/cameras/{camera["id"]}', headers={"If-Match": response.headers["etag"]}, json={"coordinates": None})
    assert cleared.status_code == 200 and cleared.json()["geometry"] is None


def test_source_approval_change_during_fetch_is_not_overwritten(setup):
    client, entries, _ = setup
    src = source(client)
    from registry.models import Source
    def changed_during_fetch(*args):
        with client.app.state.sessions() as db:
            row = db.get(Source, src["id"])
            row.state = "disabled"
            db.commit()
        return list(entries)
    client.app.state.catalogue_fetcher = changed_during_fetch
    response = sync(client, src["id"])
    assert response.status_code == 409
    assert cameras(client) == []


def test_mixed_departments_within_one_catalogue(setup):
    client, _, _ = setup
    src = source(client)
    sync(client, src["id"])
    current = client.get(f'/api/v1/sources/{src["id"]}').json()
    response = client.patch(f'/api/v1/sources/{src["id"]}', headers={"If-Match": f'"{current["revision"]}"'}, json={"department": "Municipal"})
    assert response.status_code == 200
    camera = cameras(client)[0]
    response = client.patch(f'/api/v1/cameras/{camera["id"]}', headers={"If-Match": f'"{camera["revision"]}"'}, json={"department": "Transport"})
    assert response.status_code == 200
    assert len(cameras(client, department="Municipal")) == 1
    assert len(cameras(client, department="Transport")) == 1


def test_vendor_password_login_is_scoped_and_logout_revokes_session(setup):
    client, _, _ = setup
    one, two = source(client, "login-one"), source(client, "login-two")
    sync(client, one["id"])
    sync(client, two["id"])
    with client.app.state.sessions() as db:
        db.add(VendorUser(vendor_id=one["vendor_id"], email="operator@vendor.test",
                          display_name="Vendor Operator", password_hash=hash_password("SharedDemoPassword!")))
        db.commit()
    bad = client.post("/api/v1/auth/vendor/login", json={"email": "operator@vendor.test", "password": "WrongPassword!"})
    missing = client.post("/api/v1/auth/vendor/login", json={"email": "missing@vendor.test", "password": "WrongPassword!"})
    assert bad.status_code == missing.status_code == 401
    assert bad.json() == missing.json() == {"detail": "invalid_email_or_password"}
    login = client.post("/api/v1/auth/vendor/login", json={"email": "OPERATOR@VENDOR.TEST", "password": "SharedDemoPassword!"})
    assert login.status_code == 200, login.text
    assert login.headers["cache-control"] == "no-store"
    assert "password" not in login.text and "hash" not in login.text
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/v1/me", headers=headers).json()["email"] == "operator@vendor.test"
    result = client.get("/api/v1/cameras", headers=headers).json()
    assert result["total"] == 2
    assert {camera["vendor_id"] for camera in result["data"]} == {one["vendor_id"]}
    assert client.post("/api/v1/vendors", headers=headers, json={"slug": "forbidden", "name": "Forbidden"}).status_code == 403
    assert client.post("/api/v1/auth/vendor/logout", headers=headers).status_code == 204
    assert client.get("/api/v1/cameras", headers=headers).status_code == 401


def test_vendor_direct_camera_registration_stream_and_removal(setup):
    client, _, _ = setup
    src = source(client, "direct-camera-owner")
    with client.app.state.sessions() as db:
        db.add(VendorUser(vendor_id=src["vendor_id"], email="camera-owner@vendor.test",
                          display_name="Camera Owner", password_hash=hash_password("SharedDemoPassword!")))
        db.commit()
    token = client.post("/api/v1/auth/vendor/login", json={
        "email": "camera-owner@vendor.test", "password": "SharedDemoPassword!"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    created = client.post("/api/v1/cameras", headers=headers, json={
        "external_id": "gate-001", "name": "Main gate", "location": "Gate 1",
        "stream_url": "rtsp://camera.example/live/gate-001", "stream_protocol": "rtsp"})
    assert created.status_code == 201, created.text
    camera = created.json()
    assert camera["stream"]["configured"] is True
    assert camera["stream"]["url"] == "rtsp://camera.example/live/gate-001"
    stream = client.get(f'/api/v1/cameras/{camera["id"]}/streams', headers=headers).json()
    assert stream["endpoints"]["primary_url"] == "rtsp://camera.example/live/gate-001"
    assert client.delete(f'/api/v1/cameras/{camera["id"]}', headers=headers).status_code == 204
    assert client.get("/api/v1/cameras", headers=headers).json()["total"] == 0


def test_expired_vendor_session_and_non_session_logout(setup):
    client, _, _ = setup
    src = source(client, "expiry")
    with client.app.state.sessions() as db:
        user = VendorUser(vendor_id=src["vendor_id"], email="expiry@vendor.test",
                          display_name="Expiry", password_hash=hash_password("SharedDemoPassword!"))
        db.add(user)
        db.commit()
    login = client.post("/api/v1/auth/vendor/login", json={"email": "expiry@vendor.test", "password": "SharedDemoPassword!"}).json()
    token = login["access_token"]
    with client.app.state.sessions() as db:
        session = db.query(VendorSession).filter(VendorSession.token_digest.is_not(None)).one()
        from datetime import timedelta
        session.expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
    assert client.get("/api/v1/cameras", headers={"Authorization": f"Bearer {token}"}).status_code == 401
    assert client.post("/api/v1/auth/vendor/logout").status_code == 403
