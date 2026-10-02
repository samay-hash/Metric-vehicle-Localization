# Per-camera encounters and duplicate-safe storage

The model lab now writes `encounters.sqlite3` (SQLite WAL). This is a local store wired into `live_optimized.py`, not a migration of the production application database.

## Identity and evidence

- Encounter identity includes run, camera, source session and tracker ID/epoch. Plate text is not an encounter key.
- Frame and OCR observation IDs are deterministic. Replaying a log or retrying a write preserves counts, first/last-seen times and alert records. OCR insertion, encounter summary updates and alert updates share one write transaction.
- Several OCR readings can support one encounter. Every raw result, alternative, source reference and crop remains available. The displayed primary plate is ranked by distinct-frame support, then confidence; conflicting readings remain visible.
- The encounter keeps the earliest/latest observed **frame receipt UTC**, not OCR completion time. Its best crop uses the recorded image-quality score.
- The detector records frame observations even without successful OCR. It now saves `observation_track_id` for untracked boxes, so asynchronous OCR can attach to the exact source-frame observation regardless of arrival order.
- Idle encounters close after ten seconds; the runner closes remaining encounters after OCR drains. The upstream tracker resets across reconnects and long source-time gaps, so a later passage gets a new track group.
- Broken tracks, separate cameras, different sessions and untracked fragments are not automatically merged. This is deliberate: neither plate-text equality nor temporal proximity alone proves the same physical vehicle. Appearance/position-based reconciliation is still a later step.

## Local watchlist alerts

One alert row is keyed by `(encounter_id, watchlist_record_id)`. Additional supporting frames update evidence and support on that row. Conflicting or variant-disagreeing reads remain `possible_match_needs_review`. Three distinct supporting frames with no such conflict can become `repeated_match_needs_review`; neither status is a verified identity.

Only exact primary-candidate matches are used in this first version. Alternatives remain in the evidence but do not independently create alert rows. No Slack/email/push messages are sent. No watchlist entries are fabricated from benchmark detections. Disabling a watchlist entry stops future updates while preserving historical alert rows.

The live runner accepts optional `--watchlist /absolute/path/to/watchlist.json`. Supply a JSON array with `id`, `plate` (explicit uppercase alphanumeric string), and optional boolean `enabled`. Duplicate IDs or attempts to change a record's plate are rejected; use a new ID for a changed registration.

## Saved-run replay and reports

```bash
model_lab/.venv/bin/python model_lab/encounter_report.py \
  --run model_lab/runs/live_30cams_30min_fresh_v1
model_lab/.venv/bin/python model_lab/report_bundle.py \
  --build model_lab/runs/live_30cams_30min_fresh_v1
```

Replay uses the current OCR selection policy, preserving the original event in each stored observation. The database pins that policy for the run; a different analysis policy requires a separate database rather than silently changing prior evidence.

Artifacts: `encounters.sqlite3`, `encounters.json`, and `encounter_report.html`. The main `report.json` includes encounter data and links each OCR entry to its group. All four report views can be rendered from that JSON with the existing `report_bundle.py --json` command.

Historical limitation: the earlier ten-minute logs omitted detector indices for untracked boxes. Those OCR records are stored as isolated fragments with an explicit missing frame link; we do not guess their association. New live runs save the needed index.
