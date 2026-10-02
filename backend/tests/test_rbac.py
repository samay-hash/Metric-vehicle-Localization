from sqlalchemy import select

from registry.models import SecurityAudit
from test_registry import cameras, setup, source, sync


PASSWORD = "RoleBasedDemo@2026!"


def create_user(client, email, role, scope_type="global", scope_id=None):
    response = client.post("/api/v1/access/users", json={
        "email": email,
        "display_name": role.replace("_", " ").title(),
        "password": PASSWORD,
        "assignments": [{"role": role, "scope_type": scope_type, "scope_id": scope_id}],
    })
    assert response.status_code == 201, response.text
    return response.json()


def login(client, email):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return response.json()


def auth(result):
    return {"Authorization": f'Bearer {result["access_token"]}'}


def test_role_permissions_vendor_scope_and_session_revocation(setup):
    client, _, _ = setup
    one, two = source(client, "rbac-one"), source(client, "rbac-two")
    sync(client, one["id"])
    sync(client, two["id"])
    other_camera = cameras(client, source_id=two["id"])[0]

    investigator = create_user(client, "investigator-rbac@synetra.local", "investigator",
                               "vendor", one["vendor_id"])
    maintenance = create_user(client, "maintenance-rbac@synetra.local", "maintenance")
    it_user = create_user(client, "it-rbac@synetra.local", "it_operator")

    investigator_login = login(client, investigator["email"])
    investigator_headers = auth(investigator_login)
    identity = client.get("/api/v1/me", headers=investigator_headers).json()
    assert identity["roles"] == ["investigator"]
    assert identity["scopes"] == [{"type": "vendor", "id": one["vendor_id"]}]
    assert "investigation.run" in identity["permissions"]
    assert "camera.metadata.write" not in identity["permissions"]
    page = client.get("/api/v1/cameras", headers=investigator_headers).json()
    assert page["total"] == 2
    assert {row["vendor_id"] for row in page["data"]} == {one["vendor_id"]}
    assert client.get(f'/api/v1/cameras/{other_camera["id"]}', headers=investigator_headers).status_code == 404
    own_camera = page["data"][0]
    assert client.patch(f'/api/v1/cameras/{own_camera["id"]}', headers={
        **investigator_headers, "If-Match": f'"{own_camera["revision"]}"'}, json={"location": "changed"}).status_code == 403

    maintenance_headers = auth(login(client, maintenance["email"]))
    assert client.get(f'/api/v1/cameras/{own_camera["id"]}/health', headers=maintenance_headers).status_code == 200
    assert client.get(f'/api/v1/cameras/{own_camera["id"]}/streams', headers=maintenance_headers).status_code == 403
    assert client.post(f'/api/v1/sources/{one["id"]}/sync', headers=maintenance_headers, json={}).status_code == 200
    assert client.put(f'/api/v1/sources/{one["id"]}/state', headers=maintenance_headers,
                      json={"state": "disabled"}).status_code == 403

    it_headers = auth(login(client, it_user["email"]))
    assert client.put(f'/api/v1/sources/{one["id"]}/state', headers=it_headers,
                      json={"state": "disabled"}).status_code == 200
    audit_page = client.get("/api/v1/access/audit", headers=it_headers)
    assert audit_page.status_code == 200
    assert any(row["action"] == "dashboard.login" for row in audit_page.json()["data"])
    assert client.get("/api/v1/access/audit", headers=investigator_headers).status_code == 403

    replacement = client.put(f'/api/v1/access/users/{investigator["id"]}/assignments', json={
        "assignments": [{"role": "maintenance", "scope_type": "global", "scope_id": None}]})
    assert replacement.status_code == 200, replacement.text
    assert client.get("/api/v1/me", headers=investigator_headers).status_code == 401
    replacement_login = login(client, investigator["email"])
    assert replacement_login["account"]["roles"] == ["maintenance"]

    with client.app.state.sessions() as db:
        audits = db.scalars(select(SecurityAudit)).all()
        assert any(row.action == "dashboard_user.assignments_replaced" for row in audits)
        assert PASSWORD not in str([row.details for row in audits])


def test_dashboard_login_rejects_invalid_credentials_without_enumeration_detail(setup):
    client, _, _ = setup
    create_user(client, "admin-rbac@synetra.local", "master_admin")
    wrong = client.post("/api/v1/auth/login", json={
        "email": "admin-rbac@synetra.local", "password": "WrongPassword!"})
    missing = client.post("/api/v1/auth/login", json={
        "email": "missing-rbac@synetra.local", "password": "WrongPassword!"})
    assert wrong.status_code == missing.status_code == 401
    assert wrong.json() == missing.json() == {"detail": "invalid_email_or_password"}


def test_department_scope_uses_camera_override(setup):
    client, _, _ = setup
    src = source(client, "department-scope")
    sync(client, src["id"])
    rows = cameras(client)
    for camera, department in zip(rows, ("Ahmedabad City", "Surat City")):
        response = client.patch(f'/api/v1/cameras/{camera["id"]}',
                                headers={"If-Match": f'"{camera["revision"]}"'},
                                json={"department": department})
        assert response.status_code == 200, response.text
    user = create_user(client, "ahmedabad-maintenance@synetra.local", "maintenance",
                       "department", "Ahmedabad City")
    headers = auth(login(client, user["email"]))
    page = client.get("/api/v1/cameras", headers=headers).json()
    assert page["total"] == 1
    assert page["data"][0]["department"] == "Ahmedabad City"
    fleet = client.get("/api/v1/fleet/health", headers=headers).json()
    assert fleet["total"] == 1
