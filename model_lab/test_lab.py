"""Lab correctness checks. Synthetic coordinates are unit tests, not evaluation footage."""
import json
import unittest
from pathlib import Path
from run_pipeline import clipped_box
from run_ocr import normalise
from common import ROOT, MODELS, sha256


class ContractTests(unittest.TestCase):
    def test_boxes_clip_to_original_image(self):
        self.assertEqual(clipped_box([-10, -5, 500, 200], 192, 108), [0, 0, 192, 108])

    def test_normalisation_does_not_guess_characters(self):
        self.assertEqual(normalise(' gj-01 ab 0123 '), 'GJ01AB0123')
        self.assertEqual(normalise('O0 I1 B8'), 'O0I1B8')
        self.assertEqual(normalise(''), '')

    def test_downloaded_model_integrity(self):
        path = MODELS / 'manifest.json'
        if not path.exists():
            self.skipTest('Weights not downloaded')
        manifest = json.loads(path.read_text())
        for item in manifest.values():
            entries = item.get('files', [item] if 'path' in item else [])
            for entry in entries:
                self.assertEqual(sha256(ROOT / entry['path']), entry['sha256'], entry['path'])

    def test_recorded_boxes_and_crops_are_consistent(self):
        import cv2
        runs = list((ROOT / 'runs').glob('combined_*/detections.jsonl'))
        if not runs:
            self.skipTest('No recorded run yet')
        for path in runs:
            records = [json.loads(line) for line in path.read_text().splitlines()]
            summary = json.loads((path.parent/'summary.json').read_text())
            self.assertEqual(len(records), sum(c['frames'] for c in summary['cameras']))
            for record in records:
                source = record['source']
                for vehicle in record['vehicles']:
                    x1,y1,x2,y2 = vehicle['bbox']
                    self.assertTrue(0 <= x1 < x2 <= source['width'])
                    self.assertTrue(0 <= y1 < y2 <= source['height'])
                    for plate in vehicle['plates']:
                        a,b,c,d = plate['bbox']
                        self.assertTrue(x1 <= a < c <= x2)
                        self.assertTrue(y1 <= b < d <= y2)
                        crop = cv2.imread(str(path.parent / plate['crop']))
                        self.assertEqual(crop.shape[:2], (plate['height'],plate['width']))


if __name__ == '__main__':
    unittest.main()
