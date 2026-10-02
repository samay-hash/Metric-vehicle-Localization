"""Compare downloaded OCR models on the identical plate crops; no invented plates."""
import argparse
import json
import re
import time
from collections import Counter, defaultdict
from pathlib import Path
from common import MODELS, RUNS, save_json


def normalise(text):
    return re.sub(r'[^A-Z0-9]', '', text.upper())


def main():
    import cv2
    import numpy as np
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, default=RUNS / 'nano')
    parser.add_argument('--model', choices=['mobile', 'server', 'easyocr'], default='mobile')
    parser.add_argument('--max-crops', type=int)
    args = parser.parse_args()
    if args.model == 'easyocr':
        import easyocr
        model = easyocr.Reader(['en'], gpu=False, model_storage_directory=str(MODELS / 'easyocr'),
                               user_network_directory=str(MODELS / 'easyocr/network'),
                               download_enabled=False, verbose=False)
        def read(image):
            predictions = model.readtext(image, allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', detail=1)
            if not predictions:
                return '', 0.0
            return ''.join(p[1] for p in predictions), float(min(p[2] for p in predictions))
    else:
        from paddleocr import TextRecognition
        name = 'en_PP-OCRv5_mobile_rec' if args.model == 'mobile' else 'PP-OCRv5_server_rec'
        model = TextRecognition(model_name=name, model_dir=str(MODELS / name),
                                device='cpu', enable_mkldnn=False, cpu_threads=2)
        def read(image):
            result = list(model.predict(input=image, batch_size=1))[0]
            return str(result['rec_text']), float(result['rec_score'])
    items = []
    for line in (args.run / 'detections.jsonl').read_text().splitlines():
        frame = json.loads(line)
        for vehicle in frame['vehicles']:
            for plate in vehicle['plates']:
                items.append((frame, vehicle, plate))
    if args.max_crops:
        items = items[:args.max_crops]
    records, timings = [], []
    votes = defaultdict(list)
    for frame, vehicle, plate in items:
        image = cv2.imread(str(args.run / plate['crop']))
        if image is None:
            raise OSError(f'Missing crop {plate["crop"]}')
        start = time.perf_counter()
        raw, confidence = read(image)
        alternatives = [{'layout': 'single_line', 'raw': raw, 'confidence': confidence}]
        # Two-line read is an explicit hypothesis, not an automatic plate correction.
        # Preserve both variants for review; midpoint split needs validation on our crops.
        if image.shape[1] / image.shape[0] < 2.5 and image.shape[0] >= 24 and args.model != 'easyocr':
            middle = image.shape[0] // 2
            top, top_score = read(image[:middle])
            bottom, bottom_score = read(image[middle:])
            alternatives.append({'layout': 'two_line_midpoint', 'raw': top + bottom,
                                 'confidence': min(top_score, bottom_score)})
        best = max(alternatives, key=lambda x: x['confidence'])
        elapsed = (time.perf_counter() - start) * 1000
        candidate = normalise(best['raw'])
        # This broad filter is only a candidate gate, not a legal plate format classifier.
        usable = 6 <= len(candidate) <= 12 and any(c.isalpha() for c in candidate) and any(c.isdigit() for c in candidate)
        record = {'plate_id': plate['id'], 'camera_id': frame['camera_id'],
                  'frame_index': frame['frame_index'], 'track_id': vehicle['track_id'],
                  'crop': plate['crop'], 'model': args.model, 'alternatives': alternatives,
                  'candidate': candidate if usable else None, 'raw': best['raw'],
                  'confidence': best['confidence'], 'latency_ms': elapsed,
                  'status': 'candidate_needs_review' if usable else 'unreadable_or_nonplate'}
        records.append(record)
        timings.append(elapsed)
        if usable and vehicle['track_id'] is not None and best['confidence'] >= .8:
            votes[(frame['camera_id'], vehicle['track_id'])].append(record)
        if len(records) % 20 == 0:
            print(f'{args.model}: {len(records)}/{len(items)} plate crops', flush=True)
    consensus = []
    for (camera_id, track_id), observations in votes.items():
        counts = Counter((o['candidate'], o['frame_index']) for o in observations)
        by_candidate = Counter()
        for candidate, _ in counts:
            by_candidate[candidate] += 1
        winner, support = by_candidate.most_common(1)[0]
        consensus.append({'camera_id': camera_id, 'track_id': track_id, 'candidate': winner,
                          'distinct_frame_support': support,
                          'status': 'repeated_candidate_needs_review' if support >= 3 else 'insufficient_temporal_support',
                          'conflicting_candidates': len(by_candidate) > 1})
    (args.run / f'ocr_{args.model}.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in records))
    save_json(args.run / f'ocr_{args.model}_summary.json', {
        'model': args.model, 'crops_processed': len(records),
        'candidate_count': sum(r['candidate'] is not None for r in records),
        'latency_ms_including_first_inference': {'p50': float(np.percentile(timings,50)),
                                                'p95': float(np.percentile(timings,95))} if timings else {},
        'track_consensus': consensus, 'accuracy': None,
        'note': 'Predictions only. No ground-truth labels; confidence is not measured accuracy. No watchlist alerts sent.'})
    print(f'{args.model}: complete, {len(records)} crops', flush=True)


if __name__ == '__main__':
    main()
