"""Read-only authenticated catalogue capture. Credentials never enter output files."""
import argparse
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlsplit
from common import REPO, RUNS, save_json


def capture_worker(url, camera, folder, safe_id, timeout, frame_count, sample_fps):
    import av
    import cv2
    av.logging.set_level(av.logging.PANIC)
    result = dict(camera, frames=[], status='connecting')
    start = time.monotonic()
    container = None
    try:
        container = av.open(url, options={'rtsp_transport': 'tcp'}, timeout=(timeout, timeout))
        stream = container.streams.video[0]
        stream.thread_type = 'AUTO'
        result['codec'] = stream.codec_context.name
        next_pts = None
        previous_pts = None
        for frame in container.decode(stream):
            pts = float(frame.pts * frame.time_base) if frame.pts is not None else None
            discontinuity = pts is not None and previous_pts is not None and pts < previous_pts
            previous_pts = pts
            if discontinuity:
                next_pts = None
            now = time.monotonic()
            sampling_time = pts if pts is not None else now - start
            if next_pts is not None and sampling_time < next_pts:
                if now - start > timeout + frame_count / sample_fps + 10:
                    break
                continue
            image = frame.to_ndarray(format='bgr24')
            filename = f'{len(result["frames"]):04d}.jpg'
            if not cv2.imwrite(str(folder / filename), image, [cv2.IMWRITE_JPEG_QUALITY, 95]):
                raise OSError('Unable to save captured frame')
            result['frames'].append({'path': f'{safe_id}/{filename}', 'pts_s': pts,
                                      'receipt_utc': datetime.now(timezone.utc).isoformat(),
                                      'width': frame.width, 'height': frame.height,
                                      'discontinuity': discontinuity})
            save_json(folder / 'capture.json', result)
            next_pts = sampling_time + 1 / sample_fps
            if len(result['frames']) >= frame_count:
                break
        result['status'] = ('captured' if len(result['frames']) == frame_count else
                            'partial_capture_eof' if result['frames'] else 'no_decodable_frames')
    except Exception as exc:
        # Third-party exception text can contain credential-bearing URLs.
        result['status'] = 'capture_failed'
        result['error_type'] = type(exc).__name__
    finally:
        if container is not None:
            container.close()
    save_json(folder / 'capture.json', result)


def main():
    import av
    import cv2
    import requests
    from dotenv import load_dotenv
    parser = argparse.ArgumentParser()
    parser.add_argument('--env-file', type=Path, default=REPO / 'backend/.env.registry')
    parser.add_argument('--profile', default='sentinel')
    parser.add_argument('--cameras', nargs='*')
    parser.add_argument('--frames', type=int, default=6)
    parser.add_argument('--sample-fps', type=float, default=2)
    parser.add_argument('--timeout', type=float, default=10)
    parser.add_argument('--output', type=Path, default=RUNS / 'capture')
    args = parser.parse_args()
    if args.frames < 1 or args.sample_fps <= 0 or args.timeout <= 0:
        parser.error('frames and sample-fps must be positive')
    load_dotenv(args.env_file, override=False)
    cfg = json.loads(os.environ['REGISTRY_CONNECTORS_JSON'])[args.profile]
    prefix = cfg['credentials_prefix']
    email, password = os.environ[prefix + '_EMAIL'], os.environ[prefix + '_PASSWORD']
    if urlsplit(cfg['login_url']).netloc != urlsplit(cfg['catalogue_url']).netloc:
        raise ValueError('Catalogue/login origins differ')
    session = requests.Session()
    login = session.post(cfg['login_url'], data={'email': email, 'password': password},
                         timeout=args.timeout, allow_redirects=False)
    if login.status_code not in (200, 302, 303):
        raise RuntimeError(f'Login failed HTTP {login.status_code}')
    response = session.get(cfg['catalogue_url'], timeout=args.timeout, allow_redirects=False)
    if response.status_code != 200:
        raise RuntimeError(f'Catalogue failed HTTP {response.status_code}')
    catalogue = response.json()
    if not isinstance(catalogue, list):
        raise ValueError('Expected a camera list')
    cameras = [{'id': str(c['id']), 'name': c.get('name', str(c['id']))} for c in catalogue]
    if len({c['id'] for c in cameras}) != len(cameras):
        raise ValueError('Duplicate camera IDs')
    save_json(args.output / 'catalogue.json', cameras)
    if args.cameras:
        unknown = set(args.cameras) - {c['id'] for c in cameras}
        if unknown:
            raise ValueError(f'IDs absent from live catalogue: {sorted(unknown)}')
        cameras = [c for c in cameras if c['id'] in args.cameras]
    manifest = {'started_at': datetime.now(timezone.utc).isoformat(), 'catalogue_count': len(catalogue),
                'transport': 'rtsp_tcp', 'sample_fps': args.sample_fps, 'frames_requested': args.frames,
                'timestamp_note': 'PTS is relative stream time; receipt UTC is not source capture UTC.', 'cameras': []}
    av.logging.set_level(av.logging.PANIC)
    origin = urlsplit(cfg['rtsp_origin'])
    print(f'Catalogue contains {len(catalogue)} cameras; capturing {len(cameras)} sequentially.', flush=True)
    for camera in cameras:
        cam_id = camera['id']
        safe_id = re.sub(r'[^a-zA-Z0-9_-]', '_', cam_id)
        folder = args.output / safe_id
        folder.mkdir(parents=True, exist_ok=True)
        path = cfg['rtsp_path_template'].format(camera_id=quote(cam_id, safe=''))
        url = f'{origin.scheme}://{quote(email, safe="")}:{quote(password, safe="")}@{origin.netloc}{path}'
        result = dict(camera, frames=[], status='connecting')
        start = time.monotonic()
        import multiprocessing
        ctx = multiprocessing.get_context('spawn')
        process = ctx.Process(target=capture_worker,
                              args=(url, camera, folder, safe_id, args.timeout, args.frames, args.sample_fps))
        result_file = folder / 'capture.json'
        if result_file.exists():
            raise FileExistsError('Use a fresh output folder for each capture session')
        process.start()
        process.join(args.timeout + args.frames / args.sample_fps + 5)
        timed_out = process.is_alive()
        if timed_out:
            process.terminate()
            process.join(3)
            if process.is_alive():
                process.kill()
                process.join()
        if result_file.exists():
            result = json.loads(result_file.read_text())
        if timed_out:
            result['status'] = 'partial_capture_timeout' if result['frames'] else 'capture_timeout'
        elif result['status'] == 'connecting':
            result['status'] = 'capture_process_failed'
        result['elapsed_s'] = round(time.monotonic() - start, 3)
        manifest['cameras'].append(result)
        save_json(args.output / 'manifest.json', manifest)
        print(f'{cam_id}: {result["status"]}, {len(result["frames"])} frames, {result["elapsed_s"]}s', flush=True)
    manifest['finished_at'] = datetime.now(timezone.utc).isoformat()
    save_json(args.output / 'manifest.json', manifest)


if __name__ == '__main__':
    main()
