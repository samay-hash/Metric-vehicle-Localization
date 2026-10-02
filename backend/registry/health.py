"""Camera health projections. Never perform network or media work on API reads."""
from datetime import timezone

from .models import utcnow


def aware(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def target_revision(camera, source):
    # Catalogue syncs and cosmetic edits don't invalidate measured availability.
    return f"{camera.health_generation}:{source.health_generation}"


def probe_target(camera, source):
    if source.adapter == "sentinel":
        return {"stream_key": "sentinel-rtsp", "protocol": "rtsp", "connector_profile": source.connector_profile,
                "external_id": camera.external_id, "url": None}
    streams = list(camera.stream_endpoints)
    chosen = next((s for s in streams if s.protocol in ("rtsp", "rtsps")), streams[0] if streams else None)
    if chosen:
        return {"stream_key": chosen.id, "protocol": chosen.protocol, "url": chosen.url}
    return {"stream_key": "legacy" if camera.stream_url else "unconfigured",
            "protocol": camera.stream_protocol, "url": camera.stream_url}


def health_summary(camera, source, now=None):
    now = now or utcnow()
    record = camera.health_record
    result = {"status": "unmonitored", "freshness": "never_checked", "connectivity": "unknown",
              "video_quality": "unknown", "analytics": "not_configured", "checked_at": None,
              "expires_at": None, "last_frame_at": None, "stream_key": None,
              "reasons": ["never_checked"], "metrics": {}, "consecutive_count": 0}
    if not camera.enabled or source.state != "approved":
        result.update(status="disabled", reasons=["camera_disabled" if not camera.enabled else "source_not_approved"])
        return result
    if record is None:
        return result
    result.update(checked_at=aware(record.checked_at), expires_at=aware(record.expires_at),
                  last_frame_at=aware(record.last_frame_at) if record.last_frame_at else None,
                  stream_key=record.stream_key)
    if record.target_revision != target_revision(camera, source) or aware(record.expires_at) <= now:
        result.update(status="stale", freshness="stale", reasons=[
            "target_changed" if record.target_revision != target_revision(camera, source) else "measurement_expired"])
        return result
    data = record.details
    flags = data.get("quality_flags", [])
    result.update(status=record.status, freshness="fresh", connectivity=data["connectivity"],
                  video_quality=("suspected_degradation" if flags else "no_fault_detected")
                  if data["connectivity"] == "reachable" and data.get("quality_checks") else "unknown",
                  reasons=flags or ([] if data["connectivity"] == "reachable" else [data["connectivity"]]),
                  metrics=data["metrics"], consecutive_count=record.consecutive_count)
    if record.candidate != record.status:
        result["reasons"] = result["reasons"] + ["awaiting_confirmation"]
    return result


def next_state(record, observation, settings):
    flags = sorted(set(observation.quality_flags))
    candidate = "degraded" if observation.connectivity == "reachable" and flags else (
        "healthy" if observation.connectivity == "reachable" else observation.connectivity)
    previous = record.status if record else None
    same = (record and record.candidate == candidate and
            sorted(record.details.get("quality_flags", [])) == flags)
    count = record.consecutive_count + 1 if same else 1
    if candidate in ("unsupported", "not_configured", "probe_error", "auth_failed"):
        return candidate, candidate, count
    threshold = settings.health_recovery_threshold if candidate == "healthy" else settings.health_failure_threshold
    # The first successful observation establishes availability; recovery from a
    # confirmed fault needs multiple successes. Any new failure leaves healthy immediately.
    if candidate == "healthy" and previous in (None, "healthy", "pending"):
        threshold = 1
    if count >= threshold:
        return candidate, candidate, count
    return (previous if previous not in (None, "healthy") else "pending"), candidate, count
