"""Run the downloaded plate ONNX exports on one actual vehicle crop."""
import argparse
import json
import time
from pathlib import Path
from common import MODELS, RUNS, save_json


def main():
    import cv2
    from ultralytics import YOLO
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, default=RUNS / 'combined_nano')
    args = parser.parse_args()
    records = [json.loads(line) for line in (args.run/'detections.jsonl').read_text().splitlines()]
    source = next(v['crop'] for r in records for v in r['vehicles'] if v['plates'])
    image = cv2.imread(str(args.run / source))
    results = []
    for size in ('n','s'):
        path = MODELS / f'license-plate-finetune-v1{size}.onnx'
        model = YOLO(str(path), task='detect')
        start = time.perf_counter()
        prediction = model.predict(image, device='cpu', imgsz=640, conf=.25, verbose=False)[0]
        results.append({'model': path.name, 'source_crop': source,
                        'elapsed_ms_including_startup': (time.perf_counter()-start)*1000,
                        'boxes': prediction.boxes.xyxy.tolist(),
                        'scores': prediction.boxes.conf.tolist(),
                        'note': 'Runtime smoke test only; one real crop, no accuracy claim.'})
    save_json(args.run / 'onnx_smoke.json', results)
    print('Both ONNX plate exports ran successfully on a real vehicle crop.')


if __name__ == '__main__':
    main()
