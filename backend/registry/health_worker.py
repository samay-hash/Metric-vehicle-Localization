"""Standalone, bounded RTSP sampler. Run: python -m registry.health_worker.

FFmpeg is required on the worker host; no inference models or browser are needed.
Only operator-approved destinations are contacted. Never log URLs or decoder stderr.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import time
from urllib.parse import urlsplit
from uuid import uuid4

from dotenv import load_dotenv
import httpx

from .adapters import AdapterError, resolve_sentinel
from .config import Connector

LOG = logging.getLogger("registry-health")
WIDTH, HEIGHT, FRAME_COUNT = 160, 90, 3


@dataclass(frozen=True)
class ProbeConfig:
    ffmpeg: str = "ffmpeg"
    timeout: float = 12
    # Quality metrics always run; alert thresholds are opt-in until calibrated.
    dark_ratio_threshold: float = 0
    blur_threshold: float = 0
    freeze_alerts: bool = False


def frame_metrics(raw, width=WIDTH, height=HEIGHT):
    size = width * height
    frames = [raw[i:i + size] for i in range(0, len(raw) - size + 1, size)]
    if not frames:
        return {"frames_decoded": 0}
    sharpness = []
    for frame in frames:
        laplacian = [4 * frame[i] - frame[i - 1] - frame[i + 1] - frame[i - width] - frame[i + width]
                     for y in range(1, height - 1) for x in range(1, width - 1) for i in [y * width + x]]
        sharpness.append(statistics.pvariance(laplacian))
    return {"frames_decoded": len(frames),
            "dark_ratio": sum(pixel < 16 for frame in frames for pixel in frame) / (size * len(frames)),
            "sharpness": statistics.mean(sharpness),
            "repeated_frame_ratio": sum(a == b for a, b in zip(frames, frames[1:])) / (len(frames) - 1) if len(frames) > 1 else None}


def probe_rtsp(url, config, runner=subprocess.run):
    parsed = urlsplit(url)
    if parsed.scheme not in ("rtsp", "rtsps"):
        return "unsupported", [], {"frames_decoded": 0, "sample_seconds": 0}
    command = [config.ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error",
               "-threads", "1", "-rtsp_transport", "tcp", "-allowed_media_types", "video",
               "-timeout", str(int(config.timeout * 1_000_000)),
               "-protocol_whitelist", "tcp,udp,rtp,rtsp,tls,crypto"]
    if parsed.scheme == "rtsps":
        command += ["-tls_verify", "1"]
    command += ["-i", url, "-an", "-sn", "-dn", "-vf", f"fps=1,scale={WIDTH}:{HEIGHT}",
                "-frames:v", str(FRAME_COUNT), "-threads", "1", "-pix_fmt", "gray", "-f", "rawvideo", "pipe:1"]
    start = time.monotonic()
    try:
        result = runner(command, capture_output=True, timeout=config.timeout, check=False)
        raw, error = result.stdout, result.stderr
    except subprocess.TimeoutExpired as exc:
        raw, error = exc.stdout or b"", exc.stderr or b""
    except OSError:
        return "probe_error", [], {"frames_decoded": 0, "sample_seconds": round(time.monotonic() - start, 3)}
    metrics = frame_metrics(raw[:WIDTH * HEIGHT * FRAME_COUNT])
    metrics["sample_seconds"] = round(time.monotonic() - start, 3)
    if metrics["frames_decoded"]:
        flags = []
        # A single decoded frame proves reachability, but cannot establish persistent quality.
        if metrics["frames_decoded"] >= FRAME_COUNT:
            if config.dark_ratio_threshold and metrics["dark_ratio"] >= config.dark_ratio_threshold:
                flags.append("darkness_suspected")
            elif config.blur_threshold and metrics["sharpness"] < config.blur_threshold:
                flags.append("blur_suspected")
            if config.freeze_alerts and metrics["repeated_frame_ratio"] == 1:
                flags.append("freeze_suspected")
        return "reachable", flags, metrics
    error = error.lower()
    if any(code in error for code in (b"operation not permitted", b"permission denied", b"option not found", b"unrecognized option")):
        status = "probe_error"
    elif any(code in error for code in (b"401 unauthorized", b"403 forbidden")):
        status = "auth_failed"
    elif any(code in error for code in (b"decod", b"codec", b"invalid data")):
        status = "decode_failed"
    else:
        status = "unreachable"
    return status, [], metrics


def resolve_target(target, connectors, allowed_hosts):
    profile = target.get("connector_profile")
    if profile:
        config = connectors.get(profile)
        if config is None:
            raise AdapterError("connector_profile_not_configured")
        return resolve_sentinel(config, target["external_id"])["rtsp_url"]
    url = target.get("url")
    if not url:
        return None
    parsed = urlsplit(url)
    if parsed.scheme not in ("rtsp", "rtsps"):
        return url
    if not parsed.hostname or parsed.hostname.casefold() not in allowed_hosts:
        raise AdapterError("media_destination_not_approved")
    return url


def observe(target, connectors, allowed_hosts, config):
    try:
        url = resolve_target(target, connectors, allowed_hosts)
        if url:
            connectivity, flags, metrics = probe_rtsp(url, config)
        else:
            connectivity, flags, metrics = "not_configured", [], {"frames_decoded": 0, "sample_seconds": 0}
    except (AdapterError, ValueError):
        # Local config/allowlist failures are monitor failures, not camera outages.
        connectivity, flags, metrics = "probe_error", [], {"frames_decoded": 0, "sample_seconds": 0}
    checks = []
    if metrics["frames_decoded"] >= FRAME_COUNT:
        checks = [name for name, enabled in (("darkness_suspected", config.dark_ratio_threshold),
                  ("blur_suspected", config.blur_threshold), ("freeze_suspected", config.freeze_alerts)) if enabled]
    return {"id": str(uuid4()), "camera_id": target["camera_id"], "stream_key": target["stream_key"],
            "target_revision": target["target_revision"], "checked_at": datetime.now(timezone.utc).isoformat(),
            "connectivity": connectivity, "quality_flags": flags, "quality_checks": checks,
            "metrics": metrics, "detector_version": "rtsp-health-v1"}


def submit(client, observation):
    # An uncertain write is retried with exactly the same observation ID and body.
    for attempt in range(3):
        try:
            response = client.post("/api/v1/internal/health/observations", json=observation)
            if response.status_code < 500:
                return response.status_code == 200
        except httpx.TransportError:
            pass
        if attempt < 2:
            time.sleep(0.5 * (attempt + 1))
    return False


def sweep(client, connectors, allowed_hosts, config, concurrency, due):
    started = time.monotonic()
    after = None
    observed = accepted = 0
    interval = 60
    seen = set()
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        while True:
            response = client.get("/api/v1/internal/health/targets", params={"limit": 100, **({"after": after} if after else {})})
            response.raise_for_status()
            page = response.json()
            interval = page["interval_seconds"]
            seen.update(t["camera_id"] for t in page["data"])
            targets = [t for t in page["data"] if due.get(t["camera_id"], (0, None))[0] <= time.monotonic()
                       or due.get(t["camera_id"], (0, None))[1] != t["target_revision"]]
            # At most one bounded page is queued; no 80k future/connection fan-out.
            for observation in executor.map(lambda t: observe(t, connectors, allowed_hosts, config), targets):
                observed += 1
                saved = submit(client, observation)
                accepted += saved
                backoff = 2 if observation["connectivity"] != "reachable" and page["stale_seconds"] >= interval * 3 else 1
                due[observation["camera_id"]] = (started + interval * backoff, observation["target_revision"])
            after = page["next_cursor"]
            if not after:
                break
    for camera_id in set(due) - seen:
        del due[camera_id]
    client.post("/api/v1/internal/health/prune").raise_for_status()
    return interval, observed, accepted


def main():
    load_dotenv(Path(__file__).resolve().parents[1] / ".env.registry")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="Complete one paginated sweep and exit")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    token = os.getenv("REGISTRY_HEALTH_WORKER_TOKEN", "")
    url = os.getenv("REGISTRY_API_URL", "http://127.0.0.1:8001").rstrip("/")
    parsed = urlsplit(url)
    if parsed.username or parsed.password or parsed.query or parsed.fragment or (parsed.scheme != "https" and not (
            parsed.scheme == "http" and parsed.hostname in ("localhost", "127.0.0.1", "::1"))):
        parser.error("Use HTTPS for the registry API, or HTTP on loopback only")
    if len(token) < 32:
        parser.error("Configure REGISTRY_HEALTH_WORKER_TOKEN (at least 32 characters)")
    binary = shutil.which(os.getenv("REGISTRY_HEALTH_FFMPEG", "ffmpeg"))
    if not binary:
        parser.error("Install FFmpeg on the health worker host")
    concurrency = int(os.getenv("REGISTRY_HEALTH_CONCURRENCY", "4"))
    config = ProbeConfig(binary, float(os.getenv("REGISTRY_HEALTH_PROBE_TIMEOUT", "12")),
                         float(os.getenv("REGISTRY_HEALTH_DARK_RATIO", "0")),
                         float(os.getenv("REGISTRY_HEALTH_BLUR_THRESHOLD", "0")),
                         os.getenv("REGISTRY_HEALTH_FREEZE_ALERTS", "0") == "1")
    if not 1 <= concurrency <= 32 or not 3 <= config.timeout <= 60 or not 0 <= config.dark_ratio_threshold <= 1 or not 0 <= config.blur_threshold <= 1_000_000:
        parser.error("Invalid health worker concurrency, timeout, or quality threshold")
    connectors = {key: Connector(**value) for key, value in json.loads(os.getenv("REGISTRY_CONNECTORS_JSON", "{}")).items()}
    allowed_hosts = {s.strip().casefold() for s in os.getenv("REGISTRY_HEALTH_ALLOWED_HOSTS", "").split(",") if s.strip()}
    due = {}
    try:
        with httpx.Client(base_url=url, headers={"Authorization": f"Bearer {token}"}, timeout=15, trust_env=False,
                          follow_redirects=False) as client:
            while True:
                start = time.monotonic()
                try:
                    interval, observed, accepted = sweep(client, connectors, allowed_hosts, config, concurrency, due)
                    elapsed = time.monotonic() - start
                    LOG.info("Sweep: observed=%d accepted=%d duration=%.1fs target_interval=%ds", observed, accepted, elapsed, interval)
                    if args.once:
                        return 0 if observed == accepted else 1
                    if elapsed > interval:
                        LOG.warning("Sweep exceeded the target interval; monitoring coverage will fall")
                except (httpx.HTTPError, ValueError, KeyError):
                    LOG.error("Registry health request failed; existing measurements will expire")
                    if args.once:
                        return 1
                    interval = 10
                time.sleep(max(1, interval - (time.monotonic() - start)))
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
