# CCTV Registry API — implemented backend

The registry runs independently of the analytics backend on port **8001**. It imports no ML models, emits no simulated events, and makes no cloud intelligence calls. The `/sentinel` dashboard reads its camera inventory and stream definitions through the analytics backend's registry gateway.

## Available now

- Persistent vendors, internal connector configuration and stable camera UUIDs.
- Simple database-backed vendor email/password login with hashed passwords and revocable 12-hour sessions.
- Real Sentinel catalogue authentication/discovery and repeatable dry-run/apply synchronization.
- Admin, read-only dashboard service, and vendor-scoped API authentication. Vendor keys are generated randomly, stored as hashes, returned once, and revocable.
- Direct vendor camera creation with stream URLs, create-only JSON/CSV bulk imports, metadata updates with optimistic concurrency, soft removal, and CSV export.
- Per-camera name/location/department/ownership/type, coordinates and provenance, installation/maintenance/storage/retention metadata.
- Cursor-paginated search with vendor/source/department/type/catalogue status/mapped/bounding-box filters.
- GeoJSON map API; indexed PostGIS geometry on PostgreSQL and coordinate filtering on local SQLite.
- Camera metadata audit history, source-sync status and documented API schemas.

The dashboard includes `/vendor/login` and `/vendor/onboarding` for vendor sign-in and direct camera management. Vendors add cameras, stream endpoints, metadata and GIS positions without seeing the internal source abstraction. The Sentinel account refreshes its configured catalogue after sign-in and presents those cameras in the same inventory. Current reader credentials remain a trusted **service account with registry-wide read access**, not an end-user department role. Do not embed admin or global reader tokens into a public frontend bundle. Connector binding, source approval and key issuance remain administrative operations.

## Run locally

The root Makefile is the supported local workflow. Create configuration once, then start each service in its own terminal:

```bash
make registry-env
make registry-migrate
make registry
make backend
make frontend
```

If `.env.registry` already exists, preserve it rather than copying over it. Set a randomly generated `REGISTRY_ADMIN_TOKEN` of at least 32 characters, a distinct optional `REGISTRY_READER_TOKEN`, and the Sentinel credentials. Example token generator:

```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(32))'
```

`.env.registry` and files under `backend/registry-data/` are gitignored. No keys or source passwords are committed. After the API is running, use `make registry-bootstrap` to import the configured catalogue, `make registry-seed` to create the local vendor accounts, and `make registry-enrich` to backfill missing Sentinel location metadata.

Open [interactive API docs](http://127.0.0.1:8001/docs). Use **Authorize** with the admin token from local configuration. The OpenAPI document is at `/openapi.json`. `GET /health` is public; all `/api/v1` routes require bearer authentication.

`make registry-bootstrap` uses the API to register one `sentinel` vendor and one `sentinel-government` source, dry-run the real catalogue, approve a draft source and apply the import. Repeat runs reuse these records and camera IDs. It will not re-enable a disabled source. It never prints source credentials or API keys.

Create the five hackathon vendor accounts after bootstrapping Sentinel with `make registry-seed`. The seed is idempotent: it creates missing vendors/accounts and does not reset existing passwords. The plaintext password comes from `REGISTRY_VENDOR_DEFAULT_PASSWORD` and is never stored or printed.

| Login | Initial camera scope |
|---|---:|
| `sentinel.vendor@synetra.local` | 30 |
| `vendor2@synetra.local` | 0 |
| `vendor3@synetra.local` | 0 |
| `vendor4@synetra.local` | 0 |
| `vendor5@synetra.local` | 0 |

The catalogue count is always discovered. Camera names and IDs are provider data. The current Sentinel enrichment supplies approximate location coordinates with provenance; exact camera positions and department/storage information can be corrected through vendor onboarding. Catalogue presence does not prove that a camera is streaming.

## API workflow

All paths below are relative to `/api/v1`. Authentication is `Authorization: Bearer <token>`.

| Method and path | Access | Behavior |
|---|---|---|
| `POST /auth/vendor/login` | Public | Validate vendor email/password and return a 12-hour bearer session |
| `POST /auth/vendor/logout` | Vendor login session | Revoke the current session immediately |
| `GET /me` | Any authenticated principal | Effective service role and vendor scope |
| `POST /vendors` | Admin | Create vendor; unique slug |
| `GET /vendors` | Scoped read | Cursor-paginated vendors |
| `POST /vendors/{id}/api-keys` | Admin | Issue vendor key; secret shown once |
| `DELETE /vendors/{id}/api-keys/{key}` | Admin | Immediately revoke future API requests |
| `POST /sources` | Admin | Bind a vendor to an operator-configured connector; starts draft |
| `GET /sources`, `GET /sources/{id}` | Scoped read | Source state and last sync outcome |
| `PATCH /sources/{id}` | Admin | Edit name/default department; requires `If-Match` revision |
| `PUT /sources/{id}/state` | Admin | Approve or disable a source |
| `POST /sources/{id}/test` | Admin/own vendor | Validate catalogue access and schema; does not test media |
| `POST /sources/{id}/sync` | Admin/own vendor | Dry-run by default; approved source required to apply |
| `POST /cameras` | Admin/own vendor | Vendor creates a camera directly; an internal collection is created automatically when needed |
| `GET /cameras`, `GET /cameras/{id}` | Scoped read | Standard camera responses with stream readiness and vendor-supplied endpoint for manual cameras |
| `PATCH /cameras/{id}` | Admin/own vendor | Update metadata with `If-Match`; audited |
| `DELETE /cameras/{id}` | Admin/own vendor | Soft-remove a camera from normal list/map/export responses; audited |
| `GET /cameras/{id}/health` | Scoped read | Measured stream health, freshness, reasons and observed availability; unknown until monitored |
| `GET /cameras/{id}/health/history` | Scoped read | Bounded measurement and fault/recovery history |
| `GET /fleet/health` | Scoped read | Camera-health counts with existing inventory filters |
| `GET /cameras/{id}/streams` | Scoped read | Normalized protocol capabilities; media gateway readiness |
| `GET /cameras/{id}/audit` | Scoped read | Paginated manual metadata audit records |
| `POST /camera-imports` | Admin/own vendor | JSON bulk create; dry-run by default, existing IDs skipped. Vendors may omit `source_id` to use their automatically managed camera collection; admins must supply it. |
| `POST /sources/{id}/camera-imports/csv` | Admin/own vendor | Validated CSV import; dry-run query flag defaults true |
| `GET /camera-export` | Scoped read | CSV export capped at 10,000 rows; narrow filters for larger sets |
| `GET /map/cameras` | Scoped read | GeoJSON points for mapped cameras only, with pagination |

Direct vendor camera registration example:

```json
{
  "external_id": "CAM-WEST-001",
  "name": "West gate camera",
  "streams": [
    {"label": "Main stream", "protocol": "rtsp", "url": "rtsp://camera-host/live/CAM-WEST-001"},
    {"label": "Browser stream", "protocol": "hls", "url": "https://camera-host/live/CAM-WEST-001/index.m3u8"}
  ],
  "location": "West entrance",
  "department": "Owning department",
  "camera_type": "fixed"
}
```

`source_id` is omitted in the vendor workflow. The API creates and reuses an internal `vendor-cameras` collection for that account. Administrators can still supply `source_id` for controlled imports and catalogue integrations. Remote connector origins, stream path templates and credential bindings live in operator-controlled `REGISTRY_CONNECTORS_JSON`; vendors cannot redirect server-held credentials.

Vendor login request:

```json
{
  "email": "sentinel.vendor@synetra.local",
  "password": "<configured local default>"
}
```

The response contains `access_token`, `token_type`, `expires_at` and the vendor account summary. Send the token as `Authorization: Bearer <access_token>`. Sessions are stored by SHA-256 token digest; passwords use salted scrypt hashes. Login failures deliberately return one generic error for missing emails and incorrect passwords. Logout requires a login session, not an admin token or API key.

For synchronization, send `{"dry_run": true}` to preview, then `{"dry_run": false}` to apply. An empty catalogue requires explicit `allow_empty: true`; an HTML login page, invalid schema, duplicate external IDs or failed fetch aborts without marking existing cameras missing. Missing entries in a successful catalogue are retained with `missing_from_source`. Cameras which reappear retain their original Synetra UUID. Sync preserves manually entered names and metadata.

Sync requests are currently bounded synchronous operations. The response describes completed work; there is no pretend background job. Scheduling, per-vendor rate limits and asynchronous bulk jobs are future work for larger catalogues. Concurrent source synchronization/approval changes are detected with a revision condition; callers receive `409` and must fetch current state before retrying.

Camera update example (illustrative coordinates, not a real Sentinel camera location):

```http
PATCH /api/v1/cameras/<camera UUID>
Authorization: Bearer <admin or own-vendor token>
If-Match: "<revision from GET>"
Content-Type: application/json
```

```json
{
  "location": "Location supplied by the department",
  "coordinates": {
    "latitude": 23.0,
    "longitude": 72.0,
    "provenance": "Example only — replace with actual survey reference"
  },
  "department": "Owning department",
  "camera_type": "fixed",
  "infrastructure": {
    "storage_type": "nvr",
    "retention_days": 15,
    "maintenance_status": "unknown"
  }
}
```

Omitted fields are unchanged. `streams` replaces the camera's complete ordered stream list and accepts up to 12 named entries. RTSP/RTSPS and HTTP/HTTPS endpoints are accepted, with HLS and WHEP represented by their protocol type. The earlier `stream_url` and `stream_protocol` pair remains accepted for compatibility. Setting nullable fields to null clears them; clearing a camera name override restores the upstream name, and clearing a department override restores the internal collection default. Coordinates are updated/cleared as a pair. `infrastructure` is a replacement object, not a recursive patch.

Lists return `{data, next_cursor, total}`; `total` is populated for cameras. Pass `after=<next_cursor>` to continue. UUID cursors provide stable ID ordering, not creation-time ordering. `limit` defaults to 100 and is capped at 500. Map requests are capped at 2,000 points. Filters: `q`, `source_id`, `vendor_id`, `department`, `camera_type`, `catalogue_status`, `mapped`, `bbox=west,south,east,north`. Antimeridian-spanning boxes must be split into two requests. GeoJSON uses **longitude, latitude** order.

CSV import requires `Content-Type: text/csv`. Columns:

```text
external_id,name,location,latitude,longitude,location_provenance,camera_type,ownership,department
```

Only `external_id` and `name` are mandatory. Leave unknowns blank; all three coordinate/provenance fields are required when mapping a camera. Validate up to 1,000 rows per request. Invalid rows return row numbers and field errors, and **nothing is committed**. Apply with `?dry_run=false`. Existing IDs are skipped rather than overwritten; use camera PATCH for corrections. Use authorized exports as data extracts; export columns are not identical to the import schema.

Errors use a `detail` code: `401` invalid/missing authentication, `403` insufficient permission, `404` missing or inaccessible record, `409` duplicate/concurrent update/approval conflict, `412` stale revision, `422` invalid data, `428` missing `If-Match`, `502` upstream catalogue failure, `503` database/configuration unavailable. Key material, vendor passwords and raw provider exceptions are not echoed.

## Stream boundary

The adapter standardizes Sentinel's protocol capability and resolves credentials internally in `registry/adapters.py`. Ordinary clients never see credential-bearing URLs. `/streams` returns a normalized list containing the configured RTSP, HLS and WHEP URLs for Sentinel; its RTSP URL carries an authentication marker while the credential is retained server-side. Manually registered cameras return every vendor-supplied stream. Stream paths come from connector configuration rather than code-level URL assumptions.

The registry API does not relay, transcode, decode, or analyze video. A separate [camera-health worker](camera-health.md) samples RTSP streams and reports measurements through dedicated authenticated ingestion routes. Run it with `make registry-health-worker` after migration and worker-token configuration. The analytics backend's `/registry` gateway uses the server-held reader token to supply the `/sentinel` dashboard with registry data, while its `/stream/{registry_camera_id}` worker resolves the selected registered endpoint and performs the existing MJPEG/YOLO pipeline. Crop APIs, dedicated gateway replicas, and playback-session management remain future integrations.

## PostgreSQL/PostGIS deployment

`REGISTRY_DATABASE_URL` supports PostgreSQL through `postgresql+psycopg://...`. The migrations create only registry-prefixed tables and a separate version table. PostGIS adds a generated SRID-4326 point and GiST index used for bounding-box queries. Migration credentials need permission to create the extension, or a DBA can install it beforehand. The runtime account should be restricted after migrations in a departmental deployment.

From the repository root, set a URL-safe random `REGISTRY_DB_PASSWORD` in the shell and prepare `backend/.env.registry`, then:

```bash
docker compose -f compose.registry.yml up --build -d
```

The database is internal to the Compose network; the API binds to loopback. The selected PostGIS image uses amd64 emulation on Apple Silicon. SQLite is the lightweight native local profile, not the statewide concurrent-write database. Database replication, TLS ingress, identity federation, rate limits, scheduled sync, operator-level departmental authorization, advanced gap reports and media processing are not configured by this initial Compose stack.

## Verification

From the repository root, with pytest installed in the selected Python environment:

```bash
PYTHONPATH=backend python3 -m pytest backend/tests/test_registry.py -q
```

The separate `test_registry_postgres.py` runs when `REGISTRY_TEST_DATABASE_URL` points to a disposable PostGIS database whose name ends in `_test`. It performs migrations and rollback and must not target a real registry database.
