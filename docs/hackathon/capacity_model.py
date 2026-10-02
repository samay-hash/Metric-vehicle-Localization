"""Reproducible planning arithmetic. This does not benchmark or simulate video.

Run: python3 docs/hackathon/capacity_model.py --cameras 80000
Pass --measured-streams-per-host only with a recorded full-pipeline test result.
Units: Mbps, decimal bytes, GB/TB/PB; rates are configurable assumptions.
"""
import argparse
import json
import math


def positive(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("must be finite and greater than zero")
    return number


def fraction(value):
    number = float(value)
    if not math.isfinite(number) or not 0 <= number <= 1:
        raise argparse.ArgumentTypeError("must be between zero and one")
    return number


def count(value):
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def calculate(args):
    n = args.cameras
    bytes_per_second = n * args.bitrate_mbps * 1e6 / 8
    daily_video = bytes_per_second * 86400
    events_per_second = n * args.encounters_per_camera_second
    metadata_per_second = events_per_second * args.metadata_bytes
    crop_bytes_per_day = events_per_second * args.crop_fraction * args.crop_bytes * 86400
    result = {
        "classification": "planning_arithmetic_not_a_benchmark",
        "assumptions": vars(args),
        "workload": {
            "video_ingress_mbps": n * args.bitrate_mbps,
            "source_frames_per_second": n * args.source_fps,
            "analysis_frames_per_second": n * args.analysis_fps,
            "video_tb_per_day_single_copy": daily_video / 1e12,
            "retained_video_tb_single_copy": daily_video * args.retention_days / 1e12,
            "encoded_ring_buffer_gb": bytes_per_second * args.ring_seconds / 1e9,
            "encounters_per_second": events_per_second,
            "metadata_mbps": metadata_per_second * 8 / 1e6,
            "metadata_gb_per_day_raw": metadata_per_second * 86400 / 1e9,
            "selected_crops_gb_per_day_single_copy": crop_bytes_per_day / 1e9,
        },
        "host_sizing": None,
        "exclusions": [
            "video protocol overhead and bandwidth bursts",
            "WAL, indexes, replication, backups and filesystem overhead",
            "evidence clips, previews and optional VLM capacity",
            "regional rounding, standby nodes and fault-domain reserve",
            "CPU/GPU/decode/model throughput unless explicitly measured",
        ],
    }
    if args.measured_streams_per_host is not None:
        safe = math.floor(args.measured_streams_per_host * args.utilisation)
        if safe < 1:
            raise ValueError("reserve leaves fewer than one safe stream per host")
        result["host_sizing"] = {
            "classification": "projection_from_user_supplied_measurement",
            "measurement_evidence": args.measurement_evidence,
            "safe_streams_per_host": safe,
            "active_hosts_before_regional_rounding": math.ceil(n / safe),
            "warning": "Valid only for the same footage mix, FPS, models and hardware; add failure reserve per region.",
        }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cameras", type=count, default=50)
    parser.add_argument("--bitrate-mbps", type=positive, default=2.0)
    parser.add_argument("--source-fps", type=positive, default=15.0)
    parser.add_argument("--analysis-fps", type=positive, default=5.0)
    parser.add_argument("--retention-days", type=positive, default=15.0)
    parser.add_argument("--ring-seconds", type=positive, default=30.0)
    parser.add_argument("--encounters-per-camera-second", type=positive, default=0.1)
    parser.add_argument("--metadata-bytes", type=count, default=2000)
    parser.add_argument("--crop-fraction", type=fraction, default=0.2)
    parser.add_argument("--crop-bytes", type=count, default=100000)
    parser.add_argument("--measured-streams-per-host", type=count)
    parser.add_argument("--measurement-evidence", help="Path or URL to the actual benchmark artifact")
    parser.add_argument("--utilisation", type=positive, default=0.7)
    args = parser.parse_args()
    if args.analysis_fps > args.source_fps:
        parser.error("analysis FPS cannot exceed source FPS")
    if args.utilisation > 1:
        parser.error("utilisation must be at most one")
    if args.measured_streams_per_host and not args.measurement_evidence:
        parser.error("host sizing requires --measurement-evidence; do not enter an unmeasured GPU claim")
    try:
        result = calculate(args)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
