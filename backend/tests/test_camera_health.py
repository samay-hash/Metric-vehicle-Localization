from datetime import timedelta
import subprocess
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import select

from registry.health_worker import FRAME_COUNT, HEIGHT, WIDTH, ProbeConfig, observe, probe_rtsp, submit, sweep
from registry.models import CameraHealthRecord, HealthMeasurement, utcnow
from test_registry import ADMIN, READER, cameras, setup, source, sync

WORKER = "health-worker-" + "w" * 32


@pytest.fixture
def health_setup(setup):
    client, _, settings = setup
    from dataclasses import replace
    client.app.state.settings = replace(settings, health_worker_token=WORKER)
    src = source(client)
    sync(client, src["id"])
    camera = cameras(client)[0]
    targets = client.get("/api/v1/internal/health/targets", headers={"Authorization": f"Bearer {WORKER}"}).json()["data"]
    target = next(t for t in targets if t["camera_id"] == camera["id"])
    return client, camera, target, src


def observation(target, status="reachable", checked_at=None, flags=None):
    return {"id": str(uuid4()), "camera_id": target["camera_id"], "target_revision": target["target_revision"],
            "stream_key": target["stream_key"], "checked_at": (checked_at or utcnow()).isoformat(),
            "connectivity": status, "quality_flags": flags or [], "quality_checks": flags or [],
            "metrics": {"frames_decoded": 3 if status == "reachable" else 0, "sample_seconds": 3},
            "detector_version": "rtsp-health-v1"}


def post(client, payload):
    return client.post("/api/v1/internal/health/observations", json=payload, headers={"Authorization": f"Bearer {WORKER}"})


def health(client, camera):
    return client.get(f'/api/v1/cameras/{camera["id"]}/health').json()


def test_failure_recovery_persistence_history_and_stale_monitor(health_setup):
    client, camera, target, _ = health_setup
    assert health(client, camera)["status"] == "unmonitored"
    assert health(client, camera)["reliability"]["observed_availability_percent"] is None
    first = utcnow() - timedelta(seconds=120)
    states = ["reachable", "unreachable", "unreachable", "unreachable", "reachable", "reachable"]
    expected = ["healthy", "pending", "pending", "unreachable", "unreachable", "healthy"]
    for index, (state, result) in enumerate(zip(states, expected)):
        response = post(client, observation(target, state, first + timedelta(seconds=index * 20)))
        assert response.status_code == 200, response.text
        assert health(client, camera)["status"] == result
    assert client.get(f'/api/v1/cameras/{camera["id"]}').json()["health"]["status"] == "healthy"
    assert client.get(f'/api/v1/cameras/{camera["id"]}').json()["revision"] == camera["revision"]
    assert client.get("/api/v1/fleet/health").json()["counts"] == {"healthy": 1, "unmonitored": 1}
    with client.app.state.sessions() as db:
        record = db.get(CameraHealthRecord, camera["id"])
        record.expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
    result = health(client, camera)
    assert result["status"] == "stale"
    assert result["connectivity"] == "unknown"
    assert result["last_frame_at"]
    assert client.get("/api/v1/fleet/health").json()["counts"] == {"stale": 1, "unmonitored": 1}
    history = client.get(f'/api/v1/cameras/{camera["id"]}/health/history').json()["data"]
    assert len(history) == 6
    assert history[0]["previous_status"] == "unreachable"
    assert history[0]["transition"] is True


def test_worker_token_is_separate_and_vendor_reads_stay_scoped(health_setup):
    client, camera, target, src = health_setup
    other = source(client, "other")
    key = client.post(f'/api/v1/vendors/{other["vendor_id"]}/api-keys', json={"label": "other"}).json()["token"]
    for token in (ADMIN, READER, key, "bad"):
        headers = {"Authorization": f"Bearer {token}"}
        assert client.get("/api/v1/internal/health/targets", headers=headers).status_code == 401
        assert client.post("/api/v1/internal/health/observations", json=observation(target), headers=headers).status_code == 401
    headers = {"Authorization": f"Bearer {key}"}
    assert client.get(f'/api/v1/cameras/{camera["id"]}/health', headers=headers).status_code == 404
    assert client.get(f'/api/v1/cameras/{camera["id"]}/health/history', headers=headers).status_code == 404
    assert client.get("/api/v1/fleet/health", headers=headers).json()["total"] == 0
    worker_headers = {"Authorization": f"Bearer {WORKER}"}
    assert client.get("/api/v1/cameras", headers=worker_headers).status_code == 401
    assert client.post("/api/v1/vendors", json={"slug": "no", "name": "No"}, headers=worker_headers).status_code == 401
    assert client.get("/health", headers={"Authorization": ""}).json()["status"] == "ok"


def test_idempotency_ordering_future_dates_and_changed_targets(health_setup):
    client, camera, target, _ = health_setup
    payload = observation(target, checked_at=utcnow() - timedelta(seconds=10))
    assert post(client, payload).status_code == 200
    assert post(client, payload).json()["duplicate"] is True
    reused = {**payload, "connectivity": "auth_failed", "metrics": {"frames_decoded": 0, "sample_seconds": 1}}
    assert post(client, reused).status_code == 409
    assert post(client, observation(target, checked_at=utcnow() - timedelta(seconds=20))).status_code == 409
    assert post(client, observation(target, checked_at=utcnow() + timedelta(minutes=1))).status_code == 422
    assert post(client, observation(target, checked_at=utcnow() - timedelta(minutes=31))).status_code == 422
    client.patch(f'/api/v1/cameras/{camera["id"]}', json={"stream_url": "rtsp://changed.test/live", "stream_protocol": "rtsp"}, headers={"If-Match": f'"{camera["revision"]}"'})
    assert health(client, camera)["status"] == "stale"
    assert health(client, camera)["reasons"] == ["target_changed"]
    assert client.get("/api/v1/fleet/health").json()["counts"]["stale"] == 1
    assert post(client, observation(target)).status_code == 409


def test_catalogue_sync_and_rename_preserve_health(health_setup):
    client, camera, target, src = health_setup
    assert post(client, observation(target)).status_code == 200
    assert sync(client, src["id"]).status_code == 200
    current = client.get(f'/api/v1/cameras/{camera["id"]}').json()
    assert client.patch(f'/api/v1/cameras/{camera["id"]}', json={"name": "Renamed"},
                        headers={"If-Match": f'"{current["revision"]}"'}).status_code == 200
    assert health(client, camera)["status"] == "healthy"
    assert health(client, camera)["reliability"]["completed_probes"] == 1


def test_confirmed_quality_fault_and_gap_reset(health_setup):
    client, camera, target, _ = health_setup
    start = utcnow() - timedelta(seconds=50)
    for i in range(3):
        result = post(client, observation(target, checked_at=start + timedelta(seconds=i * 10), flags=["darkness_suspected"]))
        assert result.status_code == 200
    assert health(client, camera)["status"] == "degraded"
    with client.app.state.sessions() as db:
        record = db.get(CameraHealthRecord, camera["id"])
        record.expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
    assert post(client, observation(target, "unreachable")).json()["status"] == "pending"
    assert health(client, camera)["consecutive_count"] == 1


def test_disabled_camera_and_source_are_not_probed(health_setup):
    client, camera, target, src = health_setup
    assert post(client, observation(target)).status_code == 200
    assert client.put(f'/api/v1/sources/{src["id"]}/state', json={"state": "disabled"}).status_code == 200
    assert health(client, camera)["status"] == "disabled"
    assert client.get("/api/v1/internal/health/targets", headers={"Authorization": f"Bearer {WORKER}"}).json()["data"] == []
    assert post(client, observation(target)).status_code == 404


def test_prune_retains_current_state_and_availability_ignores_monitor_errors(health_setup):
    client, camera, target, _ = health_setup
    assert post(client, observation(target, "probe_error")).status_code == 200
    assert health(client, camera)["reliability"]["completed_probes"] == 0
    with client.app.state.sessions() as db:
        row = db.scalar(select(HealthMeasurement).where(HealthMeasurement.camera_id == camera["id"]))
        row.checked_at = utcnow() - timedelta(days=8)
        db.commit()
    response = client.post("/api/v1/internal/health/prune", headers={"Authorization": f"Bearer {WORKER}"})
    assert response.json()["deleted"] == 1
    assert health(client, camera)["status"] == "probe_error"


def test_probe_is_bounded_reports_auth_and_handles_partial_decode():
    def unauthorized(command, **kwargs):
        assert kwargs["timeout"] == 12
        assert "-rtsp_transport" in command
        return subprocess.CompletedProcess(command, 1, b"", b"method DESCRIBE failed: 401 Unauthorized secret")
    status, flags, metrics = probe_rtsp("rtsp://camera.test/live", ProbeConfig(), unauthorized)
    assert status == "auth_failed" and metrics["frames_decoded"] == 0
    assert "secret" not in str(metrics)
    def partial(command, **kwargs):
        raise subprocess.TimeoutExpired(command, 12, output=bytes([80]) * (WIDTH * HEIGHT))
    status, flags, metrics = probe_rtsp("rtsp://camera.test/live", ProbeConfig(), partial)
    assert status == "reachable" and metrics["frames_decoded"] == 1 and flags == []


def test_static_and_night_samples_are_metrics_only_without_calibration():
    for pixel in (0, 25, 120):
        raw = bytes([pixel]) * (WIDTH * HEIGHT * FRAME_COUNT)
        runner = lambda cmd, **kwargs: subprocess.CompletedProcess(cmd, 0, raw, b"")
        status, flags, metrics = probe_rtsp("rtsp://camera.test/live", ProbeConfig(), runner)
        assert status == "reachable" and flags == []
        assert metrics["repeated_frame_ratio"] == 1
    raw = bytes(WIDTH * HEIGHT * FRAME_COUNT)
    runner = lambda cmd, **kwargs: subprocess.CompletedProcess(cmd, 0, raw, b"")
    assert probe_rtsp("rtsp://camera.test/live", ProbeConfig(dark_ratio_threshold=.98), runner)[1] == ["darkness_suspected"]


def test_unapproved_manual_destinations_are_monitor_errors():
    target = {"camera_id": str(uuid4()), "stream_key": "x", "target_revision": "1:1",
              "url": "rtsp://169.254.169.254/metadata"}
    result = observe(target, {}, set(), ProbeConfig())
    assert result["connectivity"] == "probe_error"
    target["url"] = "https://provider.test/stream.m3u8"
    assert observe(target, {}, set(), ProbeConfig())["connectivity"] == "unsupported"


def test_uncertain_submission_reuses_observation_id(monkeypatch):
    monkeypatch.setattr("registry.health_worker.time.sleep", lambda _: None)
    requests = []
    def handler(request):
        requests.append(request.content)
        if len(requests) == 1:
            raise httpx.ReadTimeout("lost reply")
        return httpx.Response(200, json={"accepted": True, "duplicate": True})
    with httpx.Client(base_url="http://localhost", transport=httpx.MockTransport(handler)) as client:
        assert submit(client, {"id": str(uuid4())})
    assert requests[0] == requests[1]


def test_sweep_paginates_and_skips_targets_until_due(monkeypatch):
    targets = [{"camera_id": str(uuid4()), "target_revision": "1:1", "stream_key": "test"} for _ in range(2)]
    requests = []
    submitted = []
    def handler(request):
        requests.append(request)
        if request.url.path.endswith("/targets"):
            page = 1 if request.url.params.get("after") else 0
            return httpx.Response(200, json={"data": [targets[page]], "next_cursor": "next" if page == 0 else None,
                                           "interval_seconds": 60, "stale_seconds": 180})
        if request.url.path.endswith("/observations"):
            submitted.append(request.content)
        return httpx.Response(200, json={"accepted": True})
    monkeypatch.setattr("registry.health_worker.observe", lambda t, *args: observation(t))
    due = {}
    with httpx.Client(base_url="http://localhost", transport=httpx.MockTransport(handler)) as client:
        assert sweep(client, {}, set(), ProbeConfig(), 2, due) == (60, 2, 2)
        assert sweep(client, {}, set(), ProbeConfig(), 2, due) == (60, 0, 0)
    assert len(submitted) == 2
    assert len([r for r in requests if r.url.path.endswith("/targets")]) == 4


def test_manual_stream_replacement_invalidates_measurement_without_position_conflict(health_setup):
    client, _, _, _ = health_setup
    src = source(client, "manual", adapter="manual")
    camera = client.post("/api/v1/cameras", json={"source_id": src["id"], "external_id": "manual-cam", "name": "Manual",
        "streams": [{"label": "Main", "protocol": "rtsp", "url": "rtsp://approved.test/one"}]}).json()
    targets = client.get("/api/v1/internal/health/targets", headers={"Authorization": f"Bearer {WORKER}"}).json()["data"]
    target = next(t for t in targets if t["camera_id"] == camera["id"])
    assert post(client, observation(target)).status_code == 200
    updated = client.patch(f'/api/v1/cameras/{camera["id"]}', headers={"If-Match": f'"{camera["revision"]}"'}, json={
        "streams": [{"label": "Main", "protocol": "rtsp", "url": "rtsp://approved.test/two"}]})
    assert updated.status_code == 200, updated.text
    assert health(client, camera)["status"] == "stale"
    assert post(client, observation(target)).status_code == 409


def test_invalid_measurements_never_mark_camera_healthy(health_setup):
    client, camera, target, _ = health_setup
    payload = observation(target)
    payload["metrics"]["frames_decoded"] = 0
    assert post(client, payload).status_code == 422
    payload = observation(target)
    payload["checked_at"] = "2026-09-19T12:00:00"  # Missing timezone.
    assert post(client, payload).status_code == 422
    payload = observation(target)
    payload["metrics"]["dark_ratio"] = 2
    assert post(client, payload).status_code == 422
    assert health(client, camera)["status"] == "unmonitored"
