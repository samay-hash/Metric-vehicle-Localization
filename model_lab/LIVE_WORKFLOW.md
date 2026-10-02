# Improved live plate workflow and concurrent test

The `live_benchmark.py` runner connects every camera from the authenticated Sentinel catalogue concurrently. A shared YOLO11n + plate-n + Paddle English mobile OCR worker processes the newest available frame from each camera in round-robin order. It runs on the local laptop and writes only local evidence; it does not send production alerts.

## Improvements being tested

1. Preserve native-resolution vehicle and plate pixels.
2. Screen plate crops for native size, aspect ratio, low contrast, saturation and excessive area relative to the vehicle. These are provisional quality checks and can reject legitimate plates; rejected counts and reasons remain visible.
3. Collect distinct plate observations per vehicle track. Choose the strongest available crop using native size, contrast and sharpness. Short encounters fall back to their best available single crop after a waiting period.
4. Attempt a conservative four-corner contour fit and perspective transform. If the shape checks fail, preserve the original crop.
5. Find a low-ink gap between two text bands using horizontal projection. Read detected lines top-to-bottom. If no sufficiently clear gap exists, retain a single-line hypothesis. This is a validated-software prototype, not a trained line detector or an accuracy-certified segmenter.
6. Require confidence ≥0.70 plus the basic length and letter-and-digit checks, then prefer the stronger structural hint from `plate_formats.json`; bicubic breaks ties and CLAHE can win on structure or serve as fallback. Hints cover common state-shaped and BH-shaped layouts, with a lower rank for possible series digit/letter confusion. They do not enforce a universal ten-character length, validate an issued registration, or rewrite OCR characters. Unknown formats stay reviewable. Keep alternatives and mark agreement/disagreement. Every selected number remains unverified. Original run decisions and benchmark metrics are preserved; dedicated reports explicitly re-evaluate selection under the current versioned policy.
7. Require the same candidate on at least three distinct frames in the same camera/session/track, with no conflicting candidate, before labeling it a repeated candidate for review. It is never automatically treated as a verified identity. Variants of one image do not count as independent observations.

## Concurrency and bounds

- Thirty capture threads are grouped into six processes to share Python/native-library memory. Each stream decodes with one codec thread.
- All streams connect concurrently; model inference is shared. Target sampling is two frames per second per camera, not a promise of two processed frames per second.
- Each camera has one atomically replaced latest-frame slot. Old samples can be overwritten rather than accumulating a long queue. Sequence gaps and final unprocessed samples are counted.
- The worker processes up to six largest vehicle regions and two OCR selections per frame. Budget skips are logged. Frame receipt age over eight seconds is rejected.
- Source PTS, connection sessions and receipt UTC are separate. Trackers reset on a reconnect, non-increasing PTS, or a source-time gap over three seconds. Resetting one camera does not reset other cameras' track ID counter.
- Connections retry; a stalled capture group is restarted after its heartbeat watchdog expires. Restarting a five-camera group interrupts its healthy members too. This is an explicit limitation of this laptop test harness, not a production HA design.
- The measurement clock starts after the models warm up and capture processes have been launched. No new frames are admitted after the deadline; an already running inference may finish during shutdown. Any early abort is recorded.
- Persistent critical available RAM below 180 MB for 15 seconds ends the test rather than risking an out-of-memory failure. The aborted duration is reported, never represented as a complete test.

## Commands

Run from the repository root with the installed lab environment:

```bash
model_lab/.venv/bin/python model_lab/live_benchmark.py \
  --seconds 600 --sample-fps 2 \
  --output model_lab/runs/live_30cams_10min_v1

model_lab/.venv/bin/python model_lab/report_live.py \
  --run model_lab/runs/live_30cams_10min_v1
```

Use a new output directory for another run. For a quick smoke test, add `--cameras cam01 cam06 --seconds 15`. Every ID must exist in the current catalogue. Credentials remain in the existing environment file; none are written into the results.

## Evidence

- `config.json`: camera inventory, sampling target, thresholds and model hashes.
- `code_snapshot/` and `code_manifest.json`: exact implementation used for the run.
- `capture/<camera>/status.json`: persistent counters, connection errors and last-received timestamps.
- `resources.jsonl`: approximately one-second CPU/RAM and camera-receiving samples.
- `observations.jsonl`: every processed frame, boxes, quality reasons, original crop paths, geometry/line decisions, raw OCR alternatives and timing.
- `progress.json`: live progress while the run is active.
- `summary.json`: final measured duration, abort reason, captures and inference state.
- `metrics.json`, `RESULTS.md`, `report.html`: report generated after completion.
- `ocr_report.html`: every logged OCR attempt, decoded strings, per-line confidence, original crop and selected-frame metadata; searchable with an agreement-candidate filter.
- `preprocessing_report.html`: original, rectified, enlarged, split and contrast-adjusted crops, including padded OCR inputs. Intermediate images are reconstructed from saved PNGs and recorded transform parameters; OCR is not rerun. `preprocessing/manifest.json` maps every stage back to the original log.

To rebuild only the OCR and preprocessing views: `.venv/bin/python report_ocr_preprocessing.py --run runs/live_30cams_10min_v1` from `model_lab`. The main `report_live.py` command also generates them.

The original snapshots from the earlier sequential experiment are not a controlled accuracy baseline for this live run: scenes, traffic, thresholds, sampling and workload differ. Improved OCR accuracy requires labels and replaying both workflows on identical clips. This test establishes actual integration, runtime behavior and observed recognition outputs under concurrent feed load.

Run the eight geometry/selection/consensus software tests with:

```bash
cd model_lab
.venv/bin/python -m unittest test_plate_workflow -v
```

No extra LLM, generative super-resolution or vehicle ReID is included in this timed ANPR experiment. Those would add a separate load and require a separately declared benchmark.
