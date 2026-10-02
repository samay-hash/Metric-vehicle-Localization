<div align="center">
  <h1>Synetra</h1>
  <p>A unified CCTV registry and on-premise analytics platform for camera health monitoring, vehicle tracking and incident investigation.</p>
</div>

## Overview

Synetra brings camera networks from multiple vendors into a central registry with a consistent API. Its analytics layer is designed to turn camera feeds into searchable sightings, evidence and incident records.

The project has two parts:

- **Central Registry:** Vendor onboarding, camera discovery, metadata, access control and camera health.
- **Analytics and AI Watcher:** Detection, tracking, plate recognition, cross-camera association and investigation tools.

The registry is reported ready by the project team. Analytics, resilience and deployment capabilities below describe the intended design unless confirmed by implementation and test results. This README does not certify completion or benchmark performance.

## Central Registry

Vendors register their network APIs or supported protocol connections. Vendor adapters discover and synchronise camera inventories so onboarding does not depend on manually registering each camera.

Each camera record should include its Synetra ID, vendor ID, location when available, stream capabilities, access policy, last synchronisation time and health indicators. Missing or stale metadata must remain visible.

The adapter contract covers:

- Inventory discovery, pagination and incremental synchronisation.
- Authentication refresh and backend storage of credentials.
- Camera additions, updates and removals.
- Stream endpoint resolution, rate limits and connection failures.

A single API provides consistent access to camera records and authorised feeds. Video processing is assigned to workers; the registry does not need to relay every stream through one server.

**80,000 cameras is the registry design target. It is not a demonstrated capacity for simultaneous video analytics.** Registered cameras, connected streams and actively analysed streams must be reported separately.

See [registry setup and API documentation](docs/registry-api.md).

## Access Control

| Role | Intended access |
| :--- | :--- |
| Master Admin | Manage users, vendors, policies and system configuration |
| Investigator / Security | Search permitted sightings, inspect evidence and manage investigations |
| Maintenance | View camera inventory, health, faults and maintenance information |
| IT Operator | Manage authorised API access, integrations and operational configuration |
| Vendor | Register and manage its own network connections and camera inventory |

Permissions apply to APIs, streams, evidence, exports and shared investigations. A role alone does not grant access to every department or vendor. Shared investigations require authenticated, scoped access.

## Analytics and Investigation

The core workflow is:

1. Resolve authorised feeds from the registry.
2. Detect vehicles and persons and maintain tracks within each camera.
3. Locate vehicle plates and aggregate OCR readings across frames.
4. Store sightings with timestamps, evidence and model metadata.
5. Rank possible vehicle matches across cameras.
6. Display observed sightings, inferred connections and coverage gaps.
7. Generate configured alerts and query incident evidence through a local assistant.

Each sighting should retain the camera ID, source timestamp, known clock offset, track ID, bounding box, vehicle attributes, plate candidates, confidence, evidence reference and model version.

### Vehicle Journeys

Cross-camera association combines plate agreement, appearance, direction, road connectivity and feasible travel time. Appearance similarity is supporting evidence and does not establish identity by itself.

Confirmed sightings must remain separate from possible routes. When a camera is unavailable, Synetra should identify useful nearby cameras and expose the coverage gap. It must not create an observation where none exists.

Plate outcomes distinguish unreadable, occluded, outside view, possibly absent and possible format anomaly. An OCR failure alone does not establish a plate violation.

### Camera Health

Health monitoring should expose the reason for a reliability score rather than only a single number.

| Indicator | Intended check |
| :--- | :--- |
| Connectivity | Connection failures and no-frame timeouts |
| Freshness | Frame timestamps, clock drift and stale feeds |
| Frozen image | Repeated frames assessed with timing and scene history |
| Blur | Sustained loss of sharpness against a comparable baseline |
| Darkness or obstruction | Persistent changes in brightness, texture and visible scene |
| Analytics usefulness | Whether image quality supports the configured detection task |

Use camera-specific baselines, persistence windows and separate alert and recovery thresholds. Darkness at night must not automatically be labelled obstruction.

### Alerts and Evidence

Candidate rules include restricted-zone entry, wrong-way movement, prolonged stopping and congestion. Each supported rule needs a defined input, threshold, evidence requirement and false-alert evaluation.

Zones, schedules, thresholds and severity belong in versioned configuration. Evidence APIs should support authorised retrieval of frames, clips and crops while preserving links to the original media. Incident records should retain timestamps, model versions and evidence checksums.

## Models and Processing

The following is the intended baseline. Exact checkpoints, OCR selection and runtime compatibility require validation against the deployment footage and hardware.

| Component | Role | Selection or constraint |
| :--- | :--- | :--- |
| YOLO11 | Vehicle and person detection | Select checkpoint and resolution using measured recall and throughput |
| Within-camera tracker | Link detections across frames | ByteTrack is a candidate; preserve source timestamps |
| Plate detector and OCR | Locate and read number plates | ANPR is the complete pipeline; detector and OCR checkpoints remain to be validated |
| Multi-frame plate aggregation | Combine readings from one track | Retain ambiguity instead of forcing a plate string |
| Cross-camera association | Rank links between sightings | Plate, time, direction, road connectivity and appearance |
| Vehicle ReID | Compare vehicle appearance | Evaluate vehicle-trained TransReID or a suitable vehicle model through FastReID |
| Qwen3-1.7B, 4-bit | Answer questions and summarise retrieved incident records | Local inference; evaluate factual accuracy, abstention, latency and memory |
| NVIDIA DeepStream | Stream processing, decoding and inference orchestration | NVIDIA deployment profile; not an AI model |

The assistant does not decide whether an incident occurred or independently raise, suppress or resolve critical alerts. Search, evidence access and deterministic rules must remain operational when the assistant is unavailable.

No VLM is selected in this baseline. Specific YOLO variants, OCR packages, quantisation formats and inference runtimes should only be documented as deployed after integration is verified.

## Application Stack

The supplied setup describes the following application stack. Versions and dependencies should be checked against the repository manifests before deployment.

| Layer | Technologies |
| :--- | :--- |
| Dashboard | React, Vite, Tailwind CSS |
| Backend | Python, FastAPI, Uvicorn |
| Database access | SQLAlchemy |
| Camera and geographic data | PostgreSQL, PostGIS |
| Maps | Leaflet |
| Detection and frame processing | PyTorch, Ultralytics YOLO11, OpenCV |
| Local deployment | Docker Compose and Nginx |

Durable event delivery, evidence storage, local routing and multi-worker orchestration are architectural requirements. Kafka, Redis, pgvector, OSRM, Kubernetes and Helm are not asserted here as implemented dependencies.

## Scalability and Validation

Capacity must be measured with the full pipeline enabled, including decoding, detection, tracking, OCR, evidence capture and alert delivery. FLOPs alone are insufficient for sizing.

| Area | Required evidence |
| :--- | :--- |
| Registry | Camera count, concurrent clients, API p95/p99 latency and errors |
| Processing | Hardware, codec, resolution, analysed FPS, active streams and dropped frames |
| Quality | Detection recall, plate exact-match rate and cross-camera association precision/recall |
| Alerts | Capture-to-alert p95/p99 latency and false alerts per camera-hour |
| Resources | CPU, GPU, memory, decoding, network and storage utilisation |
| Replicas | Throughput and queue growth with 1, 2 and 4 workers |
| Recovery | Recovery time, missing events, duplicate events and stream reassignment |

Use measured sustainable throughput for initial compute planning:

```text
required workers = ceil(
  total required analysed frames per second
  / sustainable analysed frames per second per worker
)
```

Sustainable throughput must meet the latency and accuracy targets with operating headroom. Network, decoding, CPU, memory and storage limits require separate checks. Replica counts alone do not prove linear scaling.

The capacity dashboard should separate measured results, load-test results and projections. Use real labelled footage for accuracy, labelled replay for processing tests and synthetic inventory for registry load tests. Do not present simulated activity as live operational evidence.

## Failure Handling

| Failure | Required behaviour |
| :--- | :--- |
| Vendor API unavailable | Retain inventory, mark freshness and retry with backoff |
| Analytics worker crashes | Reassign streams and record processing gaps |
| Processing overload | Apply configured priorities and expose reduced coverage |
| Event delivery fails | Buffer durably, retry and prevent duplicate incidents |
| Database unavailable | Report degraded operation and do not claim unsaved incidents were saved |
| Assistant unavailable | Keep search, evidence and rule-based alerts available |

Recovery of missed footage depends on vendor or NVR retention and retrieval support. Live stream reconnection alone cannot recover missing video.

## Local Development

The commands and ports below are retained from the supplied setup instructions. They have not been verified against the repository in this revision.

| Service | Local port |
| :--- | :--- |
| Registry API | 8001 |
| Analytics backend | 8000 |
| Dashboard | 5173 |

```bash
git clone https://github.com/InferiaAI/Synetra.git
cd Synetra

make install-backend
make install-registry
make install-frontend
make registry-env
```

Configure the registry database connection, then apply migrations:

```bash
make registry-migrate
```

Run each service in a separate terminal from the repository root:

```bash
make backend
```

```bash
make registry
```

```bash
make frontend
```

Registry commands are documented in the supplied setup as using `backend/Makefile.registry`.

### Development Accounts

Set `REGISTRY_DASHBOARD_DEFAULT_PASSWORD` and `REGISTRY_VENDOR_DEFAULT_PASSWORD` before seeding accounts. Use deployment-specific credentials.

```bash
make registry-seed-rbac
```

| Role | Development account |
| :--- | :--- |
| Master Admin | `admin@synetra.local` |
| Investigator | `investigator@synetra.local` |
| Maintenance | `maintenance@synetra.local` |
| IT Operator | `it@synetra.local` |

Operations login: <http://127.0.0.1:5173/login>

Vendor login: <http://127.0.0.1:5173/vendor/login>

The supplied setup states that seeding creates missing accounts without resetting existing passwords. Changing seed environment variables does not rotate existing credentials.

## Deployment and Data Handling

The required deployment keeps intelligence local, with no cloud AI API dependency. The earlier README described a Groq-backed assistant; that conflicts with this requirement. Removing it from documentation does not prove the code has been migrated. Any remaining external assistant calls must be replaced and tested before claiming local-only operation.

Configure service environments, local model weights, database access, evidence storage and credentials before starting the Compose deployment:

```bash
docker compose up -d --build
```

Deployment support should be defined through tested hardware profiles. DeepStream requires a compatible NVIDIA environment; a different runtime requires its own validation. Resource requirements depend on active streams, codecs, resolution, processing rate and model configuration.

Offline validation must cover inference, map tiles, routing, model assets and application dependencies. Keep vendor credentials on the backend, audit evidence access and apply retention policies to original media, clips, crops, exports and shared investigations.

## Model Improvement

Retraining is a later-stage capability. The intended process is:

1. Collect failure cases under the applicable retention policy.
2. Review and label examples.
3. Train a versioned candidate model.
4. Evaluate on a separate held-out dataset, including difficult conditions.
5. Run shadow evaluation against reviewed ground truth.
6. Require authorised IT approval for promotion and retain rollback support.

Production predictions must not automatically become training labels. New models must not be promoted solely because they perform better on aggregate while regressing on important conditions.

## Project Tracking

Track delivery in the [repository's Projects tab](https://github.com/InferiaAI/Synetra/projects). Each work item should include one accountable owner, priority, dependencies, acceptance criteria and a proof link.

The immediate priority is a complete, tested workflow: vendor onboarding, camera health, vehicle sightings, plate recognition, evidence-backed journeys, capacity measurement and failure recovery. Broader traffic optimisation, GenUI and retraining interfaces follow the core workflow.
