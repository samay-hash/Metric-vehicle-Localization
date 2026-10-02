# Optimized live benchmark

`live_optimized.py` is a separate runner. Previous generated runs were deleted at the user’s request before the fresh 30-camera benchmark.

## Implemented

- Configurable capture groups of one to five threads per process. The 30-camera laptop run uses six five-camera groups to reduce memory. A watchdog restart affects that group; connection retries normally happen within each camera thread.
- Native BGR pixels and source metadata transferred through bounded shared-memory buffers. Frames no longer undergo JPEG compression, filesystem handoff, then JPEG decoding before inference.
- Fair round-robin vehicle detection across cameras. Up to six vehicle regions per frame; plate inference groups them into batches of up to four (configurable).
- One best acceptable plate region per vehicle/frame before temporal crop selection. Native source pixels are retained; no speculative camera-specific crop excludes traffic.
- Separate OCR process with a 16-job queue, 1 MiB maximum crop payload, eight-second queue expiry and explicit overload/error counters. Detector throughput is not blocked on OCR model calls.
- Current selection: confidence ≥0.70, then configured plate-structure ranking, then bicubic preference on ties; CLAHE may win on structure or act as fallback. `plate_formats.json` contains versioned, source-linked hints. No universal ten-character rule or automatic character substitution is applied. The fresh run used the configured format-ranking policy; reports retain both logged and re-evaluated decisions. Repeated-frame evidence remains unverified.
- Metadata includes source session, source PTS, frame receipt time, OCR enqueue time and actual OCR completion time. Selected crop age uses its own frame, not the frame that triggers deferred OCR.
- Stage timings, memory/CPU samples, queue expiry, capture reconnects, tracker resets, skipped samples and code/model hashes are persisted.
- A capture deadline stops new work. Previously admitted OCR may drain afterward; post-deadline completions and finalization duration are reported separately.

## Run and render

```bash
model_lab/.venv/bin/python model_lab/live_optimized.py \
  --seconds 1800 --sample-fps 2 --plate-batch 4 \
  --all-cameras --expected-cameras 30 --capture-group-size 5 --max-frame-bytes 11059200 \
  --output model_lab/runs/live_30cams_30min_fresh_v1

model_lab/.venv/bin/python model_lab/report_live.py \
  --run model_lab/runs/live_30cams_30min_fresh_v1

model_lab/.venv/bin/python model_lab/report_bundle.py \
  --build model_lab/runs/live_30cams_30min_fresh_v1
```

To regenerate the benchmark, OCR and preprocessing HTML **from JSON without rerunning models or accessing cameras**:

```bash
model_lab/.venv/bin/python model_lab/report_bundle.py \
  --json model_lab/runs/live_30cams_30min_fresh_v1/report.json
```

Keep `evidence/`, `preprocessing/` and `performance.png` beside the JSON; image paths are relative. The HTML is static and works from `file://` without browser fetch permissions.

## JSON contract

`report.json` has schema version `synetra.reports.v1`. It is the complete report view model:

| Field | Contents |
|---|---|
| `run_id`, `schema_version` | Run identity and rendering contract version |
| `config` | Cameras, model hashes, bounds, selection policy and architecture |
| `summary` | Duration, abort/shutdown status, captures, detection/OCR completion and repeated candidates |
| `metrics` | Totals, latency distributions, resource summary and stage counters |
| `cameras` | Camera names, capture/inference counters and annotated evidence paths |
| `resources` | Time series for capture availability, FPS derivation, CPU, RAM and OCR backlog |
| `ocr` | Each original logged OCR result, selected-source metadata, selected variant, alternatives, transform parameters and paths to every preprocessing image |
| `ocr_events` | Completed, expired and failed OCR jobs, enqueue and completion times |
| `provenance`, `limits`, `artifacts` | Interpretation, reconstruction information and supporting artifacts |

Raw evidence is also retained separately: `detection_frames.jsonl`, `ocr_results.jsonl`, merged `observations.jsonl`, `resources.jsonl`, `summary.json`, `metrics.json`, `config.json`, and `preprocessing/manifest.json`. The merged observations attach OCR to its triggering frame while preserving the source frame that supplied its crop.

## What this does not establish

This is not a controlled accuracy comparison against the previous 30-camera run. Camera count, time, traffic and selection rules differ. Reduced load and implementation changes both affect performance. Detector/OCR accuracy needs human labels and the same held-out clips for each configuration.

Camera-specific regions, alternate high-resolution streams, hardware video decoding, detector fine-tuning and secondary recognizer arbitration have not been enabled without calibration or benchmark evidence. Full-frame regions and the supplied feeds are explicit in the run config. No LLM, vehicle ReID, route proof or production watchlist/alert integration is included.

Shared-memory capacity is configurable; the fresh 30-camera test allows 11,059,200 bytes per camera (2560×1440 BGR). Oversized source frames are reported as errors, not silently resized. RSS sums shared pages across processes and is not exact unique/GPU memory. This lab runner aborts if an inference worker dies; it does not pretend to provide production failover for stateful tracking.
