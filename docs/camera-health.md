# Camera health — first implementation

The registry stores observations; a standalone CPU worker opens RTSP streams and samples decoded frames. Monitoring continues when all dashboard viewers close. `/health` remains the registry/database readiness check.

The default probe interval is 10 minutes (`REGISTRY_HEALTH_INTERVAL_SECONDS=600`). A reading remains fresh for 30 minutes (`REGISTRY_HEALTH_STALE_SECONDS=1800`) so a delayed sweep does not immediately mark the camera stale.

## Run locally

1. Install FFmpeg on the worker host. The worker uses the existing registry Python dependencies and needs no YOLO, OCR, GPU or cloud inference service.
2. Add a distinct, random `REGISTRY_HEALTH_WORKER_TOKEN` (at least 32 characters) to `backend/.env.registry`. Use the same token on the API and worker. Generate it locally with `python3 -c 'import secrets; print(secrets.token_urlsafe(32))'`. Do not use an admin/reader/vendor token.
3. Run `make registry-migrate`, then restart the registry with `make registry`.
4. Run `make registry-health-worker` in another terminal. For one sweep: `cd backend && .venv/bin/python -m registry.health_worker --once`.
5. Open the vendor inventory. The **Camera health** and **Image quality** columns refresh every 30 seconds and expire old readings locally even if API polling fails. Image quality shows a five-level relative clarity rating when at least five fresh sharpness samples are available, plus the underlying Laplacian-variance measurement.

Sentinel resolution uses the configured connector and its credential prefix. Manually registered RTSP hosts must appear in the worker's comma-separated `REGISTRY_HEALTH_ALLOWED_HOSTS`. This is a trusted destination allowlist, including private camera hosts where appropriate. Deploy the media worker with network egress limited to approved media destinations; FFmpeg may follow media-server redirects. Decoder stderr and URLs are never included in observations or logs. FFmpeg receives its URL as a process argument, so the worker host must be restricted to trusted operators.

The worker only accepts HTTPS registry URLs, except HTTP on loopback. For a registry running in Docker with its published loopback port, run this worker on the host. An FFmpeg binary is not added to the metadata API image.

## API contract

All public camera routes require existing registry authentication and enforce vendor scope. Department/operator RBAC remains separate work.

| Route | Result |
| --- | --- |
| `GET /health` | Registry/database readiness; no media probe |
| `GET /api/v1/cameras/{id}/health` | Current health, measured stream, freshness, reasons, metrics and 24-hour observed availability |
| `GET /api/v1/cameras/{id}/health/history?limit=50` | Most recent measurements and fault/recovery transitions; at most 200 |
| `GET /api/v1/fleet/health` | SQL-aggregated counts, with existing camera filters and vendor scope; removed cameras excluded |
| `GET /api/v1/cameras` | Includes current health in every camera; no per-camera network probes |

Worker-only routes use the dedicated token and cannot be accessed using admin, reader or vendor credentials:

- `GET /api/v1/internal/health/targets`: cursor-paginated enabled cameras from approved, active vendors. Sentinel targets contain profile references rather than credentials. Manual targets can contain their registered stream URL and must stay private to the worker.
- `POST /api/v1/internal/health/observations`: typed observation, UUID idempotency key, camera/stream identity, target generation, UTC timestamp, decoded-frame count, connectivity and quality metrics. A retry must reuse the same body and ID.
- `POST /api/v1/internal/health/prune`: deletes at most 5,000 measurements older than configured retention; latest camera state remains.

The worker token cannot use normal camera/admin mutation routes. Ingestion rejects future/expired measurements, old target generations, out-of-order observations, and reused IDs with different content. Optimistic database revisions reject concurrent overwrites. No health update changes the camera metadata ETag.

## State semantics

- **Unmonitored:** no observation exists. No availability percentage is invented.
- **Healthy:** at least one frame decoded. This establishes sampled stream availability, not analytics accuracy or continuous uptime.
- **Pending:** a fault was observed but persistence is not established. A failing observation immediately removes the healthy label.
- **Unreachable / decode failed:** three consecutive matching failures by default.
- **Authentication failed:** explicit 401/403; shown immediately, retried with backoff.
- **Degraded:** a calibrated quality check produces the same suspect flags on three consecutive probes.
- **Recovery:** a confirmed fault requires two consecutive successful, unflagged probes by default.
- **Stale:** the observation has expired or the media configuration changed. Connectivity/quality become unknown, with the last measurement/frame times retained.
- **Monitor error / unsupported / not configured:** local configuration or capability issue, rather than an asserted camera outage.
- **Disabled:** camera disabled or source not approved; not probed. Removed cameras remain excluded from fleet/list views.

Persistence resets across expired observation gaps or media-generation changes. Catalogue refreshes and camera renames preserve health history. Stream edits and disable/re-enable operations invalidate the prior target. Changing connector configuration outside the database requires restarting the worker; readings expire normally unless a new probe arrives.

`last_frame_at` is the completion time of the probe containing a decoded frame, not a trusted camera capture timestamp. Stream health does not prove that a feed is live rather than replayed. `analytics` stays `not_configured` until a persistent analytics heartbeat is integrated.

## Quality checks and reliability

Each successful probe samples up to three grayscale frames at one frame/second, resized to 160×90. It records dark-pixel ratio, Laplacian variance (sharpness), identical-frame ratio and probe duration. Quality flags require three decoded frames.

Alert thresholds default to disabled. Metrics still appear, while `video_quality` remains `unknown`. Calibrate on representative daytime, night, static, blurred and obstructed footage before setting `REGISTRY_HEALTH_DARK_RATIO`, `REGISTRY_HEALTH_BLUR_THRESHOLD` or `REGISTRY_HEALTH_FREEZE_ALERTS=1`. These are worker-wide initial settings; per-camera/day-night baselines remain future work. Repeated pixels alone do not prove a frozen camera; darkness does not prove obstruction. Flags remain explicitly **suspected**.

The dashboard's 1–5 clarity rating ranks a camera's latest fresh sharpness measurement against the other measurable cameras in the vendor inventory. It is useful for finding relative outliers, but it is not an absolute blur verdict and can change as scenes or lighting change. A **Possible blur detected** warning appears only when the calibrated worker threshold emits `blur_suspected`.

The detail endpoint computes **observed availability = successful completed probe buckets / completed probe buckets** over the last 24 hours for the current media generation. It returns sample counts, interval and monitoring coverage separately. Buckets are anchored to UTC epoch at the configured interval, use their latest observation, and exclude monitor errors, unsupported and unconfigured results. Unobserved buckets lower coverage; they are not counted as offline. A stream change resets observations eligible for the percentage. Expected probes cover camera age up to 24 hours; they do not exclude maintenance/downtime or backoff, so this is monitoring coverage rather than a contractual uptime SLA. Changing the interval re-buckets the window.

## Bounds and deployment limits

Defaults: 60-second target sweep, four concurrent probes, 12-second hard subprocess timeout, three-minute freshness, seven-day history. Faulted cameras use up to a two-interval backoff when the freshness budget permits it. HTTP writes retry three times with the same observation ID. Workers paginate at 100 targets and never queue the entire fleet. The worker logs actual sweep duration and accepted observations; an overlong sweep warns that coverage is falling.

Run **one worker instance** initially. The current scheduler has no distributed leases/sharding and is not an 80k-camera capacity claim. Multiple worker replicas would duplicate probes. At scale, add leased assignments, ingest batching, partitioned retention, and passive measurements from existing analytics decoders. Pruning is bounded per sweep; monitor backlog before increasing fleet size. Only the chosen primary RTSP stream is checked; HLS/WHEP and alternate-path failover are not validated by it.

## Verification

`PYTHONPATH=backend python3 -m pytest backend/tests/test_camera_health.py` covers fault confirmation/recovery, stale-monitor behavior, unknown availability, unchanged camera revisions, stream-generation invalidation, catalogue/rename stability, scoped reads, worker isolation, idempotency, ordering, retention, decoder timeouts, explicit authentication errors, safe quality defaults and uncertain-write retries.

Apply migrations to a disposable database before deploying. A live-feed check and calibration are separate from fixture tests; never insert test observations into the operational registry.

On September 19, 2026, a read-only probe of one configured Sentinel camera decoded three frames in 6.23 seconds. No frames or health observations were saved to the operational registry. This verifies one real RTSP path, not fleet-wide capacity or quality calibration. SQLite upgrade/downgrade/re-upgrade and ORM/schema column parity were also checked.
