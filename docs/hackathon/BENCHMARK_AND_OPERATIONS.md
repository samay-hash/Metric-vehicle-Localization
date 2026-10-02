# SYNETRA — benchmark, capacity, failover and deployment plan

All thresholds below are **proposed release targets**, not achieved results or official judging thresholds. All capacity examples are **assumption-based arithmetic**, not hardware benchmarks. Use the accompanying calculator to reproduce them. Keep real-camera measurements, replay load tests, synthetic metadata tests and statewide projections in separate report sections.

## 1. Laptop first, AWS next

The confirmed hardware plan is a local laptop now and AWS later. Read-only inspection found an **Apple M2 with 8 GB unified RAM, eight CPU cores and eight GPU cores**. Begin with one native inference worker and one stream, then increase only while measured memory and lag permit it. CPU inference is a correctness baseline; native MPS/Metal may be evaluated where the library supports it. Docker on this laptop must not be assumed to expose Apple GPU acceleration. DeepStream/TensorRT CUDA is not the laptop path.

With 8 GB shared by macOS, development tools and inference, do not start the old all-services Compose stack plus an LLM/VLM and expect stable performance. Run API/UI and one CV worker first; keep infrastructure containers minimal and monitor memory pressure/swap. Test the small assistant separately, and leave VLM/ReID disabled by default. Laptop tests prove correctness and a measured small operating point. The AWS transition is a core dependency for validating the approximately 50-feed workload, unless an actual laptop benchmark unexpectedly demonstrates adequate capacity.

For the first AWS benchmark, evaluate **g6.2xlarge** (one NVIDIA L4, 24 GB GPU memory, 8 vCPU, 32 GiB RAM) or **g6.4xlarge** (same GPU, 16 vCPU, 64 GiB RAM) if decode, OCR or services need more CPU/RAM. These specifications are from [AWS G6](https://aws.amazon.com/ec2/instance-types/g6/). They are benchmark candidates, not a claim that one instance processes 50 feeds. If G6 is unavailable in the approved region/quota, a G5/A10G candidate can be tested with the same protocol. [AWS G5](https://aws.amazon.com/ec2/instance-types/g5/)

Deploy the exact validated model/config release to AWS by G2. Check GPU quota, instance availability, source allowlisting, credentials, bandwidth and government-feed hosting permissions before depending on it. Price the actual region, instance, disk and network usage at deployment time. No AWS resources are provisioned by this plan. A one-host deployment proves only process recovery, not host/AZ high availability.

Laptop and AWS workers emit the same schema. Build platform-specific images, use local model volumes and preserve DB/evidence references. All intelligence runs inside our own processes; no Groq, Gemini, Bedrock or hosted OCR calls. For departmental rollout the same service boundaries move to approved regional/on-premises hosts.

## 2. Instrument the complete pipeline

Each observation carries `trace_id`, `camera_id`, `session_id`, model/config revisions and these timestamps:

`source_observed_at → frame_received_at → detection_done_at → ocr_done_at → observation_committed_at → alert_committed_at → alert_received_by_ui_at`.

Measure stage duration with a monotonic clock. Cross-machine latency requires synchronised UTC and a measured clock-offset bound. If the source capture time is unknown, report receive-to-alert latency separately; do not claim true glass-to-glass latency.

Record per-camera source FPS, decoded FPS, analysed FPS, packet/decode errors, frame age, dropped analysis frames, reconnect count and downtime. Record worker CPU, RSS, GPU utilisation/VRAM, decoder load, disk throughput, temperatures if available, and network ingress/egress. Record queue depth, oldest-item age, redelivery count, DB commit latency, query p95/p99, SSE delivery latency and evidence availability.

**Alert timing:** publish the alert once sufficient real recognition evidence exists. A clip can finish asynchronously. Report latency from both first eligible visible plate frame and final confirming frame; this prevents a long OCR confirmation window from disappearing from the metric.

## 3. Proposed acceptance targets

| Metric | Initial target | Exact interpretation |
|---|---|---|
| Core alert latency | p95 ≤ 5 s from first eligible frame received; p95 ≤ 1 s from confirmed observation to alert delivery | Measure at the planned concurrent load; separately list source/network delay. |
| Plate precision | ≥ 99% among accepted exact-plate outputs on the held-out test | A high abstention rate cannot hide weak recall. Report numerator/denominator and confidence interval. |
| Readable-plate encounter recall | ≥ 90%; stretch 95% | Of manually labelled readable vehicle encounters, fraction with at least one correct full plate. |
| Overall encounter coverage | Report separately with no exclusion | Counts include unreadable/occluded/no-plate vehicles and missed detections. |
| Controlled designated-vehicle route | All labelled readable checkpoints recovered; zero unrelated confirmed encounters in the demonstration | Also report checkpoint precision/recall over the wider held-out routes. |
| Matcher correctness | 100% in deterministic tests for normalisation, active/expired scope, duplicate/replay and negatives | This tests database/rules correctness; it is not CV accuracy. |
| Plate journey query | p95 ≤ 1 s for a bounded 24-hour query at a declared DB size/load | Benchmark 1 million observations locally/hosted first; report actual size and indexes. |
| Registry list/search | p95 ≤ 300 ms at 80,000 camera records under a declared request mix | Registry scale only, not video processing capacity. |
| API errors | < 1% unexpected 5xx during steady-state load | Expected invalid requests counted separately. |
| Camera failure detection | Offline ≤ 15 s; blur/blackout/freeze within a configured 15–30 s window | Measure false alerts on night/static scenes; clocks and packet loss affect the result. |
| Soak | 60 min at full admitted evaluation load; longer 2–4 h if time permits | No growing queue/RSS trend; no unreported stopped streams. |
| Offline intelligence | Core detection, matching, history and alerts pass with AI egress blocked | Camera connectivity is allowed; weights/assets are already local. |

If these targets fail, report the result and change architecture, model or hardware. Never rewrite acceptance after seeing the results just to claim a pass. A few hundred plates cannot substantiate a very tight population guarantee; show confidence intervals. Zero false matches among 300 negatives still only supports an approximate upper 95% error bound of 1%, not proof of zero risk.

## 4. Accuracy and model selection protocol

1. Assemble a manifest of authorised clips with SHA-256, camera/source, codec, resolution, native FPS, capture/replay time basis, day/night and plate-pixel distribution. Use actual government feed captures when permitted plus an own-feed dataset.
2. Aim for at least 300 labelled readable encounters across camera conditions and at least 50 deliberately difficult/unreadable encounters. Label full plate, vehicle box, plate box, first/last appearance and cross-camera identity where known. If the accessible sample is smaller, publish its exact size and limitation.
3. Split by entire track/clip/camera/time block, never random adjacent frames; otherwise train/validation leakage makes scores misleading. Shreyas holds the evaluation subset and ground truth apart from tuning.
4. Compare YOLO11n/s, chosen plate detector and PP-OCRv5/EasyOCR using identical inputs and policy. Measure exact full-string accuracy, character error, readable encounter recall, false accepts, unknown rate and per-stage latency. Include glare, two-line/tilted plates, low light and several similar vehicles.
5. Calibrate thresholds on validation data, freeze, then evaluate once on the held-out set. Do not use the watchlist to coerce OCR towards a known answer. Track confidence/vote fraction and calibrated correctness probability are different quantities.
6. Test track-ID collisions between cameras, reconnect ID resets, repeat passes through the same camera, delayed/out-of-order events, overlapping views and conflicting plates. For ReID report pair precision/recall and identity switches; it cannot silently repair a failed exact-plate result.
7. Retain mistakes and unknowns in the report with actual crops. Record why each release model was selected, including its licence/revision/preprocessing and actual memory footprint.

## 5. Four distinct scaling experiments

| Experiment | Workload | What it proves | What it does not prove |
|---|---|---|---|
| A — live integration | All supplied camera systems; real credentials/protocols | Connectivity, interoperability and operational observations | Statewide throughput from only ~50 sources |
| B — video replay load | Recorded authorised clips republished as 1, 5, 10, 25, 50 streams; more only if resources allow | Decode/CV/OCR/evidence throughput under stated footage/codec conditions | Real network diversity or 50 independent identities if clips are repeated |
| C — metadata/control-plane | Isolated generated 80,000 camera records; event rates at 1k, 5k, 10k and burst load | API/bus/DB/alert-engine capacity and replica behaviour | Any plate-recognition or video decoding capacity |
| D — failure/restore | Worker/broker/API/DB process loss, network cut, delayed media | Recovery and loss/duplicate accounting | Physical-host/AZ resilience when everything runs on one host |

For B, run 5 min warmup + 15 min steady state per stage, then a 60 min soak at the selected final operating point. Use the same predeclared clip mix; each logical replay stream gets its own session ID but retains `test_run_id` and original media hash. Increase concurrency until the first SLO or resource limit fails. Record the highest passing point and the first failing point. Repeated clips are useful load, not new accuracy samples.

For C, use k6/Locust or an equivalent reproducible harness with a published seed, event-size distribution and burst pattern. Isolate the test tenant/database from live operations. Sweep 1/2/4 API replicas and 1/2/4 consumers with a fixed DB and equal total resources for one test; separately add actual hosts/GPUs for scale-out. Use multiple independent runs and report variance. Adding processes on one GPU does not multiply GPU throughput.

Calculate `speedup_k = throughput_k / throughput_1` and `efficiency_k = speedup_k / k`. Example interpretation: an actual measured 1.6× speedup on two replicas has 80% efficiency; the numbers must come from the run, not this example. Monitor DB contention, connection count, source connection limits, GPU utilisation and queue age to explain nonlinearity.

The proof-simulation system to implement is an isolated replay publisher plus controlled impairment (delay, jitter, dropped connection, clock jump, slow DB and burst events), expected-event manifest, benchmark runner and results collector. It must produce `run.json`, raw metric samples, per-camera results, expected/observed event IDs, latency distribution and a machine-generated report. A mathematical capacity calculator is not a substitute for this executable experiment.

## 6. Capacity arithmetic: explicit assumptions

Use decimal units for bandwidth/storage here: Mbps = 10^6 bits/s; TB = 10^12 bytes. Assume **2 Mbps, 1080p, 15 source FPS and 5 analysed FPS per camera** for these examples. The actual feed manifest overrides them. Five FPS is an initial capacity scenario, not a universal sufficient ANPR rate: short dwell/high-speed approaches may require 10–15+ analysed FPS. Validate capture coverage before reducing sampling.

| Quantity | 50 cameras | 80,000 cameras |
|---|---:|---:|
| Video ingress at 2 Mbps | 100 Mbps | 160 Gbps |
| Full recording per day | 1.08 TB | 1.728 PB |
| Full recording for 15 days, one copy | 16.2 TB | 25.92 PB |
| Analysed frames at 5 FPS | 250/s | 400,000/s |
| Source frames at 15 FPS | 750/s | 1,200,000/s |
| Encoded 30 s ring buffer | 375 MB | 600 GB, distributed |

Those storage figures exclude redundancy, filesystem overhead, indexes and extra evidence. Existing VMS recording can remain local; the central service need not duplicate all footage. At an illustrative 50 KB metadata/s per site or an event-based rate, compute actual central bandwidth from the manifest rather than assuming every frame produces a record.

For an event-based example, assume **0.1 persisted encounters/camera/s, 2 KB metadata/encounter, 20% encounters retaining a 100 KB crop**. Then 80,000 cameras yield 8,000 encounters/s, 16 MB/s metadata and 1.3824 TB/day raw metadata; selected crops add 13.824 TB/day. Indexes, WAL, replication and clips increase this. These intentionally visible assumptions explain why event deduplication/retention matter. They are not observed traffic rates. For 50 cameras the same scenario gives 5 encounters/s, 0.864 GB/day metadata and 8.64 GB/day selected crops.

### GPU sizing without misusing published FPS

Let `C_test` be the maximum concurrent streams per GPU host passing the complete SLO at the actual codec/FPS/model/OCR workload. If measured near saturation, use `C_safe = floor(0.7 × C_test)` as an initial planning reserve. If the measurement already includes that reserve, do not subtract it twice. For a region with `N` cameras, active hosts = `ceil(N / C_safe)`; add failover capacity sufficient for the chosen host/AZ-loss scenario. Fragmentation means round up per region, not only statewide.

| Hypothetical measured C_test | Planned C_safe at 70% | Active hosts for 50 | Active hosts for 80k before regional rounding |
|---:|---:|---:|---:|
| 20 streams/host | 14 | 4 | 5,715 |
| 50 streams/host | 35 | 2 | 2,286 |
| 100 streams/host | 70 | 1 | 1,143 |

**This is sensitivity analysis, not an estimate that any named GPU achieves these stream counts.** The supplied discussion cites 617 FPS on L40S. NVIDIA does list that value for a specific RT-DETR + C-RADIO-B/NvDCF configuration, with performance tuning conditions. It is not our plate detection, OCR, crop storage and notification workload. Do not convert it directly to a Synetra GPU purchase count. [DeepStream 8 performance and configuration](https://docs.nvidia.com/metropolis/deepstream/8.0/text/DS_Performance.html)

Measure the bottleneck as a pipeline: decode capacity, detector batches, average new vehicles/frame, plate crops/vehicle, OCR attempts/track, CPU preprocessing, memory copies, evidence encoding and storage. Report both average and crowded-scene peak. A long-term GPU-ms budget can use `N×analysis_FPS×detector_ms + new_tracks_per_second×(plate_ms + OCR_attempts×OCR_ms + ReID_ms)`; divide by usable GPU-ms/s only after validating batching and shared-resource contention.

For a selected VLM pool: if 80,000 cameras generate one candidate every 10 minutes on average, that is 133.3 jobs/s. At an **assumed** 2 s serial service time, 70% utilisation needs `ceil(133.3×2/0.7)=381` concurrent serial-equivalent service slots. A slot is not a GPU; measure actual batched model capacity. This is why candidate budgets, deduplication, priorities and operator-triggered analysis matter. VLM overload must never hold up plate alerts.

### Hardware and cost evidence

For every tested node, publish CPU model/cores, RAM, GPU/count/VRAM, driver/CUDA, decode backend, disk class, network limit and model precision. Model weights alone do not equal runtime memory; include tensors, decoder surfaces, OCR buffers, KV cache and concurrency. Monitor peak VRAM/RSS and leave measured headroom.

For on-premises planning, measure or clearly label assumed whole-host wall power. `monthly_energy_kWh = hosts × average_host_kW × 24 × days × PUE`. Show GPU-only power separately from whole-host power. AWS cost uses region-specific instance-hours, storage, snapshots, requests, data transfer, load balancer and monitoring; it does not bill the team's electricity as a separate line item. Do not invent a rupee quote without actual region/vendor prices.

TCO worksheet: `compute + durable storage + redundancy/backups + network + software/model licences + operations + replacement reserve`. Compare central full-video ingestion/storage with regional inference and selected evidence using the same retention and service-level assumptions. Reusing VMS recording reduces central cost but does not remove regional compute, management or departmental storage cost.

## 7. Recovery design and fault-injection gates

RPO describes tolerated data loss; RTO describes time to restore service. All values below are targets that require a measured fault drill.

| Failure | Required behaviour | Test / initial target |
|---|---|---|
| Camera link loss | Mark stale/offline, exponential retry with jitter, keep other cameras active | Detect ≤15 s; reconnect ≤30 s after source restoration, subject to source keyframe/auth delay. |
| Worker process crash | Lease expires; fenced standby claims camera; new session; replay durable spool | Recovery ≤30 s; zero loss of already durably acknowledged observations. Unprocessed video during the gap is unknown unless recording permits backfill. |
| WAN to central loss | Regional spool and evidence persist; cached authorised watchlist can generate local alerts if implemented | 5 min injected cut; all retained IDs delivered after reconnect, no duplicate alert. Central delivery delay disclosed. |
| API replica loss | Load balancer removes unhealthy replica; UI reconnects/resumes cursor | ≤10 s observed disruption target; no loss of committed records. |
| Broker process/node loss | Worker spools; unacked messages redeliver; idempotent consumers | Process restart test for demo. Three-node separate-host HA profile must survive one broker node loss before claiming HA. |
| PostgreSQL unavailable | Do not ACK uncommitted observations; stop central mutation, spool and show degraded mode | Restart/replay test. No fabricated success; central matching delayed unless regional matcher exists. |
| Evidence store unavailable/full | Retain quota-bound local evidence, publish metadata with `evidence_pending` | Alert still delivered; repair/upload succeeds after restore; never attach unrelated footage. |
| GPU OOM/overload | Isolate affected worker, shed optional VLM/ReID first, preserve bounded queues | Admission limits and visible degraded sampling; record dropped-frame counts. |
| LLM/VLM outage | Deterministic incident view/report remains usable | Core recognition and alerts unchanged; no synthetic fallback intelligence. |
| Whole host/disk loss | Restore from backup or fail over to separate host | Demo target RTO ≤30 min and backup RPO ≤15 min only if configured and tested; single-host local spool can be lost with its disk. |

A replicated broker/database may target zero acknowledged-record loss within its configured synchronous failure domain; an asynchronous replica or periodic backup cannot promise the same. PostgreSQL replication choices trade performance and consistency, so document the selected mode. [PostgreSQL HA/replication](https://www.postgresql.org/docs/current/high-availability.html)

Production: quorum across independent hosts, DB primary/standby plus documented promotion/fencing, object-store redundancy, encrypted off-host backups and periodic restore. Avoid two active owners for a camera or split-brain DB writes. Snapshot alone is not a tested recovery plan. Keep watchlist/rule versions in regional caches and expose staleness; cached matching must never imply a freshly updated central watchlist during a partition.

**Graceful degradation order:** stop optional VLM jobs → pause ReID enrichment → reduce noncritical preview quality → apply preapproved per-camera analysis policy/admission limits. Preserve critical-zone priority without silently starving other cameras. If core SLO cannot be met, declare degraded service and quantify the gap.

## 8. Deployment deliverable and rollout

Provide a release bundle with pinned image digests/dependencies, local model hashes, migrations, example config, secret-loading instructions, health/readiness probes and rollback instructions. A preflight command should check CPU architecture, GPU/runtime, memory/disk, clock sync, approved source reachability and required model files. It must fail clearly on unsupported hardware rather than auto-downloading a different model.

Profiles: `laptop` (portable native worker, small measured feed count), `gpu` (Linux/NVIDIA workers, Compose), `ha-test` (multiple actual hosts where available), and later `department` (regional deployment). The profile names are proposed; commands are not claimed to exist today. Keep the API schema and test suite identical.

Clean-host drill: install documented prerequisites, load images/models, supply secrets, run migrations, import authorised camera config, start services, detect a real plate, create a watchlist hit, restart and re-query persisted history. Shreyas performs it without relying on Samay's shell history. Save timing and missing-step notes.

Statewide rollout is staged: approximately 50 evaluation cameras → 500-camera multi-department pilot → 5,000-camera regional rollout → 80,000 after capacity/operations/security acceptance. These are planning cohorts, not achieved deployment counts. Validate each vendor capability, local retention requirement and connectivity limit before expansion.

## 9. Evidence package and report skeleton

Each benchmark run should contain:

```text
run.json                 # git SHA, config/model/media hashes, hardware, scenario, seed
metrics.jsonl            # timestamped raw samples and trace-stage timings
cameras.csv              # source/codec/FPS/lag/errors and success/failure per camera
accuracy.json            # confusion/abstention counts, denominators, interval estimates
events.jsonl             # expected and observed IDs for loss/duplicate accounting
faults.jsonl             # injected failure, detected time, recovered time, impact
summary.md               # measured results, plots, limitations, reproduction steps
```

Results table starts empty: tested camera count; source/analysis FPS; hardware; plate precision/recall/unknown rate; p50/p95/p99 alert latency; sustained throughput; query latency; CPU/GPU/VRAM/RAM; dropped frames; duplicate/lost observations; failover/restore times; test duration. Populate from collected artifacts only.

The judge-facing sentence should be specific: “On hardware H and footage mix M, we processed N streams at F analysed FPS, with p95 latency L and plate encounter recall R; doubling workers on separate hosts yielded speedup S. The 80k estimate assumes workload W and reserve U.” Never substitute model-vendor benchmark numbers for H/N/L/R/S.
