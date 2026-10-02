"""Offline replay of actual captured feeds: detection, camera-local ByteTrack, plate crops.

OCR and ReID run in separate processes so the laptop need not hold every model in RAM.
This measures inference on captured frames, not concurrent live-stream capacity.
"""
import argparse
import json
import platform
import re
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from common import ROOT, MODELS, RUNS, save_json, sha256


def clipped_box(values, width, height):
    x1, y1, x2, y2 = [int(round(float(v))) for v in values]
    return [max(0, min(width, x1)), max(0, min(height, y1)),
            max(0, min(width, x2)), max(0, min(height, y2))]


def main():
    import cv2
    import numpy as np
    import torch
    from ultralytics import YOLO
    from ultralytics.trackers.byte_tracker import BYTETracker
    parser = argparse.ArgumentParser()
    parser.add_argument('--capture', type=Path, default=RUNS / 'capture')
    parser.add_argument('--output', type=Path, default=RUNS / 'nano')
    parser.add_argument('--vehicle-size', choices=['n', 's'], default='n')
    parser.add_argument('--plate-size', choices=['n', 's'], default='n')
    parser.add_argument('--device', default='auto')
    parser.add_argument('--imgsz', type=int, default=640)
    parser.add_argument('--vehicle-conf', type=float, default=0.25)
    parser.add_argument('--plate-conf', type=float, default=0.25)
    parser.add_argument('--cameras', nargs='*')
    args = parser.parse_args()
    torch.set_num_threads(2)
    device = ('mps' if torch.backends.mps.is_available() else 'cpu') if args.device == 'auto' else args.device
    capture = json.loads((args.capture / 'manifest.json').read_text())
    vehicle_path = MODELS / f'yolo11{args.vehicle_size}.pt'
    plate_path = MODELS / f'license-plate-finetune-v1{args.plate_size}.pt'
    for path in (vehicle_path, plate_path):
        if not path.exists():
            raise FileNotFoundError(path)
    vehicle = YOLO(str(vehicle_path))
    plate = YOLO(str(plate_path))
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'crops').mkdir(exist_ok=True)
    (args.output / 'vehicles').mkdir(exist_ok=True)
    (args.output / 'annotated').mkdir(exist_ok=True)
    # Warmup is explicitly excluded from steady-state timings.
    for model in (vehicle, plate):
        model.predict(np.zeros((640, 640, 3), np.uint8), device=device, imgsz=args.imgsz, verbose=False)
    metadata = {'started_at': datetime.now(timezone.utc).isoformat(), 'device': device,
                'platform': platform.platform(), 'torch': torch.__version__,
                'capture': str(args.capture.resolve()), 'imgsz': args.imgsz,
                'vehicle_conf': args.vehicle_conf, 'plate_conf': args.plate_conf,
                'model_sha256': {p.name: sha256(p) for p in (vehicle_path, plate_path)},
                'measurement': 'sequential captured-frame inference; excludes capture, startup and OCR/ReID',
                'cameras': []}
    timings = []
    with (args.output / 'detections.jsonl').open('w') as log:
        for camera in capture['cameras']:
            cam_id = camera['id']
            if args.cameras and cam_id not in args.cameras:
                continue
            tracker_args = SimpleNamespace(track_high_thresh=0.25, track_low_thresh=0.1,
                                           new_track_thresh=0.25, track_buffer=max(1, int(capture['sample_fps'])),
                                           match_thresh=0.8, fuse_score=True)
            tracker = BYTETracker(tracker_args)
            segment = 0
            counts = Counter(frames=0, vehicles=0, plates=0)
            tracks_seen = set()
            for frame_idx, frame_meta in enumerate(camera['frames']):
                frame = cv2.imread(str(args.capture / frame_meta['path']))
                if frame is None:
                    raise OSError(f'Cannot read frame {frame_meta["path"]}')
                if frame_meta.get('discontinuity'):
                    tracker.reset()
                    segment += 1
                height, width = frame.shape[:2]
                annotated = frame.copy()
                start = time.perf_counter()
                predictions = vehicle.predict(frame, classes=[2, 3, 5, 7], conf=0.1,
                                               device=device, imgsz=args.imgsz, verbose=False)[0]
                boxes = predictions.boxes.cpu().numpy()
                tracks = tracker.update(boxes, frame)
                # ByteTrack's final column is the index into this frame's detection array.
                track_by_detection = {int(row[-1]): f'{segment}:{int(row[4])}' for row in tracks}
                vehicle_ms = (time.perf_counter() - start) * 1000
                record = {'camera_id': cam_id, 'camera_name': camera['name'], 'frame_index': frame_idx,
                          'source': frame_meta, 'vehicles': [], 'vehicle_tracking_ms': vehicle_ms}
                for idx, detection in enumerate(boxes):
                    confidence = float(detection.conf[0])
                    if confidence < args.vehicle_conf:
                        continue
                    bbox = clipped_box(detection.xyxy[0], width, height)
                    x1, y1, x2, y2 = bbox
                    if x2 <= x1 or y2 <= y1:
                        continue
                    crop = frame[y1:y2, x1:x2]
                    track_id = track_by_detection.get(idx)
                    # Track IDs remain scoped to this camera and capture session.
                    if track_id is not None:
                        tracks_seen.add(track_id)
                    safe_cam = re.sub(r'[^a-zA-Z0-9_-]', '_', cam_id)
                    key = f'{safe_cam}_{frame_idx:04d}_{idx:03d}'
                    vehicle_file = f'vehicles/{key}.jpg'
                    cv2.imwrite(str(args.output / vehicle_file), crop)
                    item = {'id': key, 'bbox': bbox, 'class': vehicle.names[int(detection.cls[0])],
                            'confidence': confidence, 'track_id': track_id,
                            'crop': vehicle_file, 'plates': []}
                    plate_start = time.perf_counter()
                    plate_result = plate.predict(crop, conf=args.plate_conf, device=device,
                                                 imgsz=args.imgsz, verbose=False)[0]
                    item['plate_detection_ms'] = (time.perf_counter() - plate_start) * 1000
                    for plate_idx, box in enumerate(plate_result.boxes.cpu().numpy()):
                        px1, py1, px2, py2 = clipped_box(box.xyxy[0], x2-x1, y2-y1)
                        if px2 <= px1 or py2 <= py1:
                            continue
                        plate_crop = crop[py1:py2, px1:px2]
                        plate_key = f'{key}_p{plate_idx}'
                        filename = f'crops/{plate_key}.jpg'
                        cv2.imwrite(str(args.output / filename), plate_crop, [cv2.IMWRITE_JPEG_QUALITY, 98])
                        plate_box = [x1+px1, y1+py1, x1+px2, y1+py2]
                        gray = cv2.cvtColor(plate_crop, cv2.COLOR_BGR2GRAY)
                        item['plates'].append({'id': plate_key, 'bbox': plate_box,
                                               'confidence': float(box.conf[0]), 'crop': filename,
                                               'width': px2-px1, 'height': py2-py1,
                                               'sharpness': float(cv2.Laplacian(gray, cv2.CV_64F).var())})
                        cv2.rectangle(annotated, tuple(plate_box[:2]), tuple(plate_box[2:]), (0, 210, 255), 2)
                    record['vehicles'].append(item)
                    cv2.rectangle(annotated, (x1,y1), (x2,y2), (70,210,80), 2)
                    label = f'{item["class"]} {confidence:.2f} T{track_id if track_id is not None else "?"}'
                    cv2.putText(annotated, label, (x1,max(20,y1-5)), cv2.FONT_HERSHEY_SIMPLEX, .55, (70,210,80), 2)
                record['detection_pipeline_ms'] = (time.perf_counter() - start) * 1000
                timings.append(record['detection_pipeline_ms'])
                record['annotated'] = f'annotated/{cam_id}_{frame_idx:04d}.jpg'
                cv2.imwrite(str(args.output / record['annotated']), annotated)
                log.write(json.dumps(record) + '\n')
                log.flush()
                counts['frames'] += 1
                counts['vehicles'] += len(record['vehicles'])
                counts['plates'] += sum(len(v['plates']) for v in record['vehicles'])
            stats = {'camera_id': cam_id, 'name': camera['name'], 'capture_status': camera['status'],
                     **counts, 'local_tracks': len(tracks_seen)}
            metadata['cameras'].append(stats)
            save_json(args.output / 'summary.json', metadata)
            print(json.dumps(stats), flush=True)
    metadata['finished_at'] = datetime.now(timezone.utc).isoformat()
    metadata['detection_pipeline_ms'] = {'p50': float(np.percentile(timings, 50)),
                                        'p95': float(np.percentile(timings, 95))} if timings else {}
    metadata['counts_are_predictions_not_accuracy'] = True
    save_json(args.output / 'summary.json', metadata)


if __name__ == '__main__':
    main()
