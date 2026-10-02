# SYNETRA — execution backlog

Status: prepared; implementation is not marked complete. Existing dates are internal IST targets. New feature cards are dependency-gated and remain unscheduled.

Feature details: [Implementation plan](BONUS_FEATURE_IMPLEMENTATION_PLAN.md).

| ID | Priority | Owner | Due | Task | Depends on |
|---|---|---|---|---|---|
| SYN-00 | P0 | Meet | 2026-09-18 | Approve and track the final evaluation plan | — |
| SYN-01 | P0 | Meet | 2026-09-18 | Inventory supplied sources, clocks, coordinates and deployment hardware | — |
| SYN-02 | P0 | Samay | 2026-09-18 | Remove fabricated observations, evidence and cloud intelligence dependencies | — |
| SYN-03 | P0 | Meet | 2026-09-18 | Freeze observation, evidence and identity contracts | SYN-01 |
| SYN-04 | P0 | Samay | 2026-09-19 | Validate dedicated plate detection and OCR on held-out feed clips | SYN-01 |
| SYN-05 | P0 | Shreyas | 2026-09-19 | Build the labelled evaluation manifest and acceptance harness | SYN-01 |
| SYN-06 | P0 | Samay | 2026-09-19 | Run registry-driven persistent camera workers independently of viewers | SYN-03, SYN-04 |
| SYN-07 | P0 | Meet | 2026-09-19 | Persist observations and exact-plate watchlist alerts with retry safety | SYN-03 |
| SYN-08 | P0 | Meet | 2026-09-19 | Implement event-time journey reconstruction and genuine evidence retrieval | SYN-03, SYN-07 |
| SYN-09 | P0 | Shreyas | 2026-09-19 | Ship the operator plate-search, route, watchlist and alert workflow | SYN-07, SYN-08 |
| SYN-10 | P0 | Meet | 2026-09-19 | Enforce department RBAC across feeds, queries, evidence and notifications | SYN-03 |
| SYN-11 | P0 | Meet | 2026-09-19 | Package laptop and AWS GPU deployment with clean-host preflight | SYN-01, SYN-06, SYN-07 |
| SYN-12 | P0 | Samay | 2026-09-20 | Measure full-pipeline video load and hardware limits | SYN-05, SYN-06, SYN-07, SYN-11 |
| SYN-13 | P0 | Meet | 2026-09-20 | Prove metadata replica scaling and publish the 80k capacity model | SYN-07, SYN-11 |
| SYN-14 | P0 | Meet | 2026-09-20 | Execute worker/network/API/DB failure and backup restore drills | SYN-06, SYN-07, SYN-11 |
| SYN-15 | P0 | Shreyas | 2026-09-20 | Complete clean-machine validation and final submission evidence | SYN-09, SYN-10, SYN-11, SYN-12, SYN-13, SYN-14 |
| SYN-16 | P1 | Meet | 2026-09-20 | Add measured camera health and bounded evidence-crop API | SYN-08, SYN-10 |
| SYN-17 | P1 | Shreyas | 2026-09-20 | Add grounded local Qwen incident assistant and typed GenUI | SYN-09, SYN-10, SYN-21 |
| SYN-18 | P1 | Samay | 2026-09-20 | Evaluate vehicle-trained ReID and topology-gated candidate routes | SYN-05, SYN-08, SYN-12 |
| SYN-19 | P1 | Samay | 2026-09-20 | Prototype accelerated NVIDIA backend only if parity and speed gates pass | SYN-06, SYN-11 |
| SYN-20 | P2 | Meet | 2026-09-28 | Evaluate optional visual incident explanation after core delivery | SYN-15 |
| SYN-21 | P1 | Meet | Unscheduled | Build contextual incidents and named-recipient investigation sharing | SYN-07, SYN-08, SYN-10 |
| SYN-22 | P1 | Meet | Unscheduled | Implement sensitive-area geometry schedules and evidence rules | SYN-08, SYN-10, SYN-21 |
| SYN-23 | P1 | Meet | Unscheduled | Add topology and travel-time constrained route hypotheses | SYN-01, SYN-08, SYN-09 |
| SYN-24 | P2 | Samay | Unscheduled | Implement plate-anomaly evidence and review workflow | SYN-04, SYN-05, SYN-21 |
| SYN-25 | P2 | Samay | Unscheduled | Implement calibrated traffic density and congestion analytics | SYN-05, SYN-06, SYN-12, SYN-21 |

## SYN-00 — Approve and track the final evaluation plan

**P0 · Meet · due 2026-09-18 IST · G0**

Master plan, architecture, decision gates, benchmark protocol and linked execution cards in the repository Project.

- [ ] Preserve the team's Sep 20/21 internal targets and record the official Sep 28 extension.
- [ ] Record laptop/AWS assumptions and unresolved checkpoint/source permissions.
- [ ] Link each completed card to real test evidence; do not mark planned work Done.

## SYN-01 — Inventory supplied sources, clocks, coordinates and deployment hardware

**P0 · Meet · due 2026-09-18 IST · G0**

Credential-free source/capability manifest and hardware/network inventory; secrets remain in the secret store.

- [ ] Account for every supplied camera and at least two actual source systems.
- [ ] Probe auth, decode, protocol/codec/FPS/resolution, replay/live status and clock basis.
- [ ] Identify unknown/approximate coordinates and AWS quota/region/budget/source-access dependencies.
- [ ] Export metadata completeness and coverage-gap report; unknown field-of-view is not treated as verified street coverage.

## SYN-02 — Remove fabricated observations, evidence and cloud intelligence dependencies

**P0 · Samay · due 2026-09-18 IST · G0**

Truthful runtime paths and locally packaged models.

- [ ] No GJ01-XX/TRK plate substitution, seeded operational detections, stock clips or fixed confidence/speed.
- [ ] No simulated VLM threat fallback or stop-after-first-event behaviour.
- [ ] Block external intelligence/model-download endpoints and demonstrate core inference still runs.

## SYN-03 — Freeze observation, evidence and identity contracts

**P0 · Meet · due 2026-09-18 IST · G0**

Versioned schemas and migrations for observations, camera encounters, evidence, watchlists, alerts and audit.

- [ ] Use registry UUID plus stream-session/track identity; no cross-camera track collisions.
- [ ] Preserve observed/received timestamps, timing uncertainty, GPS provenance and model revision.
- [ ] Stable observation IDs and DB uniqueness constraints support safe redelivery.

## SYN-04 — Validate dedicated plate detection and OCR on held-out feed clips

**P0 · Samay · due 2026-09-19 IST · G1**

Pinned plate-trained YOLO checkpoint, YOLO11n/s comparison and PP-OCRv5/EasyOCR bake-off.

- [ ] First real source-frame to readable-plate result within G0's four-hour gate; checkpoint provenance is mandatory.
- [ ] Use original-resolution crops and track-level distinct-frame consensus; preserve unknowns and raw candidates.
- [ ] Report exact plate precision/recall, abstention, latency and failure crops with no adjacent-frame leakage.

## SYN-05 — Build the labelled evaluation manifest and acceptance harness

**P0 · Shreyas · due 2026-09-19 IST · G1**

Authorised footage manifest, held-out labels and real workflow checks.

- [ ] Label full plates, time windows and cross-camera appearances where known; document sample sizes.
- [ ] Include unreadable plates, similar vehicles, negative watchlist records, clock resets and repeated passes.
- [ ] Keep test fixtures isolated from live data; record clip hashes and sampling policy.

## SYN-06 — Run registry-driven persistent camera workers independently of viewers

**P0 · Samay · due 2026-09-19 IST · G1**

Persistent multi-camera worker with isolated tracker/OCR state, bounded queues and reconnects.

- [ ] Closing every browser does not stop analytics.
- [ ] Camera reconnect/PTS reset creates a new session and never contaminates another camera's state.
- [ ] Track actual decoded/analysed FPS and queue age; startup comes from registry assignments.

## SYN-07 — Persist observations and exact-plate watchlist alerts with retry safety

**P0 · Meet · due 2026-09-19 IST · G1**

One shared ingest/rules path with PostgreSQL persistence, durable spool/bus and alert outbox.

- [ ] Every confirmed plate from any worker uses the same matcher and journey path.
- [ ] Test active/expired/deactivated/scope rules and repeated redelivery without duplicate incidents.
- [ ] Restart API/consumer; re-query history and replay undelivered alerts with no loss of committed records.
- [ ] A durable HTTP batch-ingest path is the approved deadline fallback if JetStream integration threatens G1; record the actual tested transport.

## SYN-08 — Implement event-time journey reconstruction and genuine evidence retrieval

**P0 · Meet · due 2026-09-19 IST · G1**

Plate-search API, encounter grouping, late-event handling, location provenance and evidence links.

- [ ] Accept arbitrary input plate without a code change; sort observations by source/event time.
- [ ] Repeat visits remain distinct; missing coordinates/evidence get explicit states.
- [ ] No physical identity merge on contradictory plate or implausible travel without review.

## SYN-09 — Ship the operator plate-search, route, watchlist and alert workflow

**P0 · Shreyas · due 2026-09-19 IST · G2**

Real-data investigation map/timeline, evidence viewer, watchlist CRUD and reconnectable alerts.

- [ ] Each route step opens its actual frame/clip; remove stock footage and static overlays.
- [ ] Observed checkpoints and inferred gaps have distinct labels; map tolerates missing GPS.
- [ ] Show freshness/latency/error states; use deployment API config instead of hardcoded localhost.

## SYN-10 — Enforce department RBAC across feeds, queries, evidence and notifications

**P0 · Meet · due 2026-09-19 IST · G2**

Scoped operator/vendor roles, service credentials and access audit.

- [ ] Two department test principals cannot access each other's unauthorised media, events or evidence.
- [ ] SSE and model tools enforce the same scope as REST.
- [ ] Secrets remain server-side, logs are redacted, TLS verification is enabled and connector destinations approved.

## SYN-11 — Package laptop and AWS GPU deployment with clean-host preflight

**P0 · Meet · due 2026-09-19 IST · G2**

Pinned release bundle and laptop/Linux-NVIDIA profiles; approved AWS benchmark host when available.

- [ ] Models/assets run locally with no cloud inference call or automatic download.
- [ ] Preflight checks architecture, memory, runtime, clock, storage and source access; no unsupported capacity promise.
- [ ] Document actual AWS region/quota/price inputs and retention/backup; no credentials in repo.

## SYN-12 — Measure full-pipeline video load and hardware limits

**P0 · Samay · due 2026-09-20 IST · G3**

Live-source matrix and replay tests at increasing concurrency with raw latency/resource data.

- [ ] Separate real/live and repeated-clip tests; record actual source/analysis FPS and codec mix.
- [ ] Report highest passing and first failing load, p50/p95/p99, plate recall and dropped frames.
- [ ] Complete final-load soak and publish GPU/CPU/RAM/VRAM/decoder/disk/network measurements.

## SYN-13 — Prove metadata replica scaling and publish the 80k capacity model

**P0 · Meet · due 2026-09-20 IST · G3**

80k registry load test, event-rate sweep, 1/2/4 replica comparison and assumption-based hardware/network/storage sizing.

- [ ] Use an isolated synthetic namespace; never present it as 80k real video analytics.
- [ ] Record throughput, latency, errors and scaling efficiency with fixed-resource versus added-host tests distinguished.
- [ ] Populate GPU count from full-pipeline measurements only; include retention, reserve, fault domains and cost inputs.

## SYN-14 — Execute worker/network/API/DB failure and backup restore drills

**P0 · Meet · due 2026-09-20 IST · G3**

Fault log, loss/duplicate accounting, recovery timings and operator runbook.

- [ ] Kill a worker and cut network; durable queued observations replay without duplicate alerts.
- [ ] Report gaps in unprocessed video rather than claiming impossible lossless capture.
- [ ] Restore a backup on a separate instance; distinguish process restart from actual host failure/HA.

## SYN-15 — Complete clean-machine validation and final submission evidence

**P0 · Shreyas · due 2026-09-20 IST · G4**

Tested release, presentation/HLD, own-feed demo, government-feed demo, timestamped report and accessible link checklist.

- [ ] Own-feed video is at most 2–3 min and shows a working backend; government-feed output is separately evidenced.
- [ ] Reviewer can enter a plate, open true evidence, see a watchlist hit and verify persisted history.
- [ ] Freeze by Sep 20 18:00 IST; verify links/access before the Sep 21 internal submission; no unmeasured claims.

## SYN-16 — Add measured camera health and bounded evidence-crop API

**P1 · Meet · due 2026-09-20 IST · After G2 if P0 on track**

Offline/blackout/blur/freeze diagnosis, fleet health and traceable evidence crops.

- [ ] Test dark night/static scenes and actual outages; expose suspected obstruction with persistence windows.
- [ ] Crop by scoped evidence ID and bounded source coordinates with parent hash/provenance.
- [ ] If not complete by freeze, omit the demo feature rather than show placeholder results.

## SYN-17 — Add grounded local Qwen incident assistant and typed GenUI

**P1 · Shreyas · due 2026-09-20 IST · After P0 workflow passes**

Qwen3-1.7B Q4 local context answers and allowlisted structured views.

- [ ] Answers cite real event/evidence IDs, abstain on missing facts and cannot execute arbitrary code/SQL.
- [ ] Validate 50–100 grounded/unanswerable questions and test metadata prompt injection.
- [ ] Core operations work unchanged with the model unavailable; no cloud fallback.

## SYN-18 — Evaluate vehicle-trained ReID and topology-gated candidate routes

**P1 · Samay · due 2026-09-20 IST · After P0 model and load gates**

Vehicle-trained FastReID checkpoint validation, bounded per-encounter embeddings and topology-gated candidate associations; alternatives require their own validation.

- [ ] Measure false associations on lookalikes and contradictory plates.
- [ ] Time/direction/topology limits prune candidates; low-confidence matches require review.
- [ ] Never count appearance-only inference as a confirmed plate sighting; disable on failed validation.

## SYN-19 — Prototype accelerated NVIDIA backend only if parity and speed gates pass

**P1 · Samay · due 2026-09-20 IST · Four-hour spike after portable baseline**

Optional DeepStream/TensorRT FP16 backend with portable event contract.

- [ ] Match original crop coordinates, timestamps, detection output and watchlist semantics.
- [ ] Measure full pipeline, not vendor model FPS; retain validated portable backend as fallback.
- [ ] Stop the spike after four hours if parity is not proven; no late risky runtime migration.

## SYN-20 — Evaluate optional visual incident explanation after core delivery

**P2 · Meet · due 2026-09-28 IST · After submission; before event only if validated**

A separately validated local visual-model option for selected incident frames; plate decisions remain in the deterministic vision and rule workflow.

- [ ] Evaluate only selected retained evidence with labeled questions; preserve uncertainty and cite source frames.
- [ ] Measure resource and latency impact separately from core ANPR; retain operation with the visual model disabled.
- [ ] Zone rules, sharing, plate review and traffic analytics are tracked in their dedicated feature cards.

## SYN-21 — Build contextual incidents and named-recipient investigation sharing

**P1 · Meet · Unscheduled · After P0 investigation and access-control gates**

Incident context API, evidence-linked conversation records, recipient-specific shares and audited access.

- [ ] Link real alerts, encounters and evidence; normal investigation access remains usable without Qwen.
- [ ] Share a selected conversation snapshot by default; explicitly scope any live updates.
- [ ] Test unrelated recipients, expiry, revocation and changed department permissions on both context and attachments.

## SYN-22 — Implement sensitive-area geometry schedules and evidence rules

**P1 · Meet · Unscheduled · After shared incident context and observed-map gates**

PostGIS zones, scoped versioned rules, calibrated entry boundaries and incident-linked rule events.

- [ ] Distinguish a sighting at an associated camera from proven crossing of a calibrated zone boundary.
- [ ] Test inside/outside/boundary cases, schedule/timezone edges and uncertain location or timing.
- [ ] Retry and repeat frames without duplicate rule alerts; preserve rule version and evidence method.

## SYN-23 — Add topology and travel-time constrained route hypotheses

**P1 · Meet · Unscheduled · After observed journeys and location inventory are validated**

Versioned camera connectivity and route-candidate API with uncertainty-aware map presentation.

- [ ] Validate a known journey, repeated visits, missing GPS and impossible transitions.
- [ ] Distinguish observed checkpoints, appearance-based candidates and inferred road geometry.
- [ ] Missing road data produces an explicit unknown or schematic connection; never a claimed observed road route.

## SYN-24 — Implement plate-anomaly evidence and review workflow

**P2 · Samay · Unscheduled · After core model accuracy and incident evidence gates**

Versioned plate assessments and review APIs with original evidence and explicit unknown states.

- [ ] Evaluate readable, unreadable, not-visible, possibly-absent and unusual-format cases on labeled data.
- [ ] Require suitable views of the expected plate region before escalating possible absence; detector misses alone do not qualify.
- [ ] Report false positives across blur, occlusion, lighting and supported formats; no automatic offence from OCR failure.

## SYN-25 — Implement calibrated traffic density and congestion analytics

**P2 · Samay · Unscheduled · After tracking coverage capacity and incident gates**

Lane configuration, line-crossing events, coverage-aware traffic windows and congestion alerts.

- [ ] Count track crossings instead of frame detections; test direction, parked vehicles and tracking resets.
- [ ] Compare counts, occupancy and supported queue estimates against manually labeled clips.
- [ ] Expose missing coverage and calibration limits; no vehicles-per-kilometre or precise-speed claim without physical calibration and no direct signal actuation.
