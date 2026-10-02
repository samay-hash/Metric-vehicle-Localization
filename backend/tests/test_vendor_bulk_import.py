from registry.models import Source
from test_registry import setup, source


def vendor_headers(client, vendor_id):
    token = client.post(f"/api/v1/vendors/{vendor_id}/api-keys", json={"label": "bulk-import"}).json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_vendor_bulk_json_preview_creates_no_source_then_applies_atomically(setup):
    client, _, _ = setup
    vendor = client.post("/api/v1/vendors", json={"slug": "bulk-vendor", "name": "Bulk Vendor"}).json()
    headers = vendor_headers(client, vendor["id"])
    rows = [{
        "external_id": "WEST-001", "name": "West gate",
        "department": "Traffic", "location": "West entrance",
        "streams": [{"label": "Main", "protocol": "rtsp", "url": "rtsp://camera.internal/west-001"}],
        "coordinates": {"latitude": 23.0225, "longitude": 72.5714, "provenance": "site survey"},
    }, {"external_id": "WEST-002", "name": "West lane"}]

    preview = client.post("/api/v1/camera-imports", headers=headers, json={"rows": rows}).json()
    assert preview == {
        "source_id": None, "dry_run": True, "created": 2, "skipped": 0,
        "rows": [
            {"row": 1, "external_id": "WEST-001", "action": "create"},
            {"row": 2, "external_id": "WEST-002", "action": "create"},
        ],
    }
    with client.app.state.sessions() as db:
        assert db.query(Source).filter(Source.vendor_id == vendor["id"]).count() == 0

    applied = client.post("/api/v1/camera-imports", headers=headers,
                          json={"rows": rows, "dry_run": False}).json()
    assert applied["source_id"]
    assert applied["created"] == 2
    inventory = client.get("/api/v1/cameras?limit=500", headers=headers).json()
    assert inventory["total"] == 2
    assert {camera["external_id"] for camera in inventory["data"]} == {"WEST-001", "WEST-002"}
    sources = client.get("/api/v1/sources", headers=headers).json()["data"]
    assert [(item["slug"], item["adapter"], item["state"]) for item in sources] == [
        ("vendor-cameras", "manual", "approved")]

    repeated = client.post("/api/v1/camera-imports", headers=headers,
                           json={"rows": rows, "dry_run": False}).json()
    assert repeated["created"] == 0
    assert repeated["skipped"] == 2


def test_vendor_bulk_json_rejects_duplicates_and_never_uses_another_vendor_source(setup):
    client, _, _ = setup
    one = client.post("/api/v1/vendors", json={"slug": "bulk-one", "name": "Bulk One"}).json()
    two = source(client, "bulk-two", adapter="manual")
    headers = vendor_headers(client, one["id"])
    duplicate_rows = [{"external_id": "DUP", "name": "One"}, {"external_id": "DUP", "name": "Two"}]
    assert client.post("/api/v1/camera-imports", headers=headers, json={"rows": duplicate_rows}).status_code == 422
    assert client.post("/api/v1/camera-imports", headers=headers,
                       json={"source_id": two["id"], "rows": [{"external_id": "NO", "name": "No"}]}).status_code == 404
    assert client.get("/api/v1/cameras", headers=headers).json()["total"] == 0


def test_admin_bulk_import_still_requires_an_explicit_source(setup):
    client, _, _ = setup
    response = client.post("/api/v1/camera-imports", json={
        "rows": [{"external_id": "ADMIN-001", "name": "Admin camera"}], "dry_run": False})
    assert response.status_code == 422
    assert response.json()["detail"] == "source_id_required_for_admin"
