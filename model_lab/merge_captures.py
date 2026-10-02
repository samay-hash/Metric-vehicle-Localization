"""Select one intact capture session per camera, retaining every attempt's status."""
import argparse
import json
import shutil
from pathlib import Path
from common import save_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('captures', nargs='+', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if (args.output / 'manifest.json').exists():
        parser.error('Choose a new output directory')
    selected, attempts = {}, []
    sampling_rates = set()
    for directory in args.captures:
        manifest = json.loads((directory / 'manifest.json').read_text())
        sampling_rates.add(manifest['sample_fps'])
        for camera in manifest['cameras']:
            attempts.append({'capture': str(directory.resolve()), 'camera_id': camera['id'],
                             'status': camera['status'], 'frames': len(camera['frames']),
                             'error_type': camera.get('error_type')})
            old = selected.get(camera['id'])
            if old is None or len(camera['frames']) >= len(old[1]['frames']):
                selected[camera['id']] = (directory, camera)
    if len(sampling_rates) != 1:
        parser.error('Do not combine captures with different sampling rates')
    cameras = []
    for camera_id, (directory, camera) in sorted(selected.items()):
        camera['capture_session'] = str(directory.resolve())
        for frame in camera['frames']:
            target = args.output / frame['path']
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(directory / frame['path'], target)
        cameras.append(camera)
    save_json(args.output / 'manifest.json', {'cameras': cameras, 'sample_fps': sampling_rates.pop(),
              'catalogue_count': len(cameras), 'attempts': attempts,
              'note': 'Best available capture per camera; independent sessions, not a simultaneous network observation.'})
    print(f'{sum(bool(c["frames"]) for c in cameras)}/{len(cameras)} cameras with frames')


if __name__ == '__main__':
    main()
