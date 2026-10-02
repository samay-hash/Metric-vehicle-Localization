"""Download documented non-LLM checkpoints; record exact revisions and hashes."""
import argparse
import json
import urllib.request
from datetime import datetime, timezone
from common import ROOT, MODELS, save_json, sha256


def download(url, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        tmp = path.with_suffix(path.suffix + '.part')
        urllib.request.urlretrieve(url, tmp)
        tmp.replace(path)
    return {'path': str(path.relative_to(ROOT)), 'url': url,
            'bytes': path.stat().st_size, 'sha256': sha256(path)}


def main():
    from huggingface_hub import snapshot_download
    parser = argparse.ArgumentParser()
    parser.add_argument('--group', choices=['all', 'detectors', 'ocr', 'reid'], default='all')
    args = parser.parse_args()
    manifest_path = MODELS / 'manifest.json'
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    def record(name, entry):
        expected_path = ROOT / 'model_manifest.json'
        if expected_path.exists():
            expected = json.loads(expected_path.read_text()).get(name, {})
            old_files = expected.get('files', [expected] if 'path' in expected else [])
            expected_hashes = {f['path']: f['sha256'] for f in old_files}
            for file in entry.get('files', [entry] if 'path' in entry else []):
                if file['path'] in expected_hashes and file['sha256'] != expected_hashes[file['path']]:
                    raise ValueError(f'Frozen checkpoint hash mismatch: {file["path"]}')
        if manifest_path.exists():
            manifest.update(json.loads(manifest_path.read_text()))
        manifest[name] = entry
        save_json(manifest_path, manifest)
        print('Ready:', name, flush=True)
    if args.group in ('all', 'detectors'):
        for size in ('n', 's'):
            name = f'yolo11{size}.pt'
            record(name, download(f'https://github.com/ultralytics/assets/releases/download/v8.3.0/{name}', MODELS / name))
        repo = 'morsetechlab/yolov11-license-plate-detection'
        revision = '251a30d7daedca065f56e04b0af04052c907c68f'
        for size in ('n', 's'):
            for ext in ('pt', 'onnx'):
                name = f'license-plate-finetune-v1{size}.{ext}'
                entry = download(f'https://huggingface.co/{repo}/resolve/{revision}/{name}', MODELS / name)
                entry.update(revision=revision, license='AGPL-3.0',
                             caveat='Author reports train/test contamination; Indian CCTV accuracy unvalidated.')
                record(name, entry)
    if args.group in ('all', 'ocr'):
        for name in ('en_PP-OCRv5_mobile_rec', 'PP-OCRv5_server_rec'):
            repo = f'PaddlePaddle/{name}'
            revision = {'en_PP-OCRv5_mobile_rec': '267c36e24c331595590fe7bd72bde2436fd286f2',
                        'PP-OCRv5_server_rec': 'b26c3587fda8da3c8ec0ce357214b4d661ff1558'}[name]
            folder = MODELS / name
            snapshot_download(repo, revision=revision, local_dir=folder,
                              allow_patterns=['*.json', '*.yml', '*.yaml', '*.pdiparams', '*.txt', '*.md'])
            record(name, {'repo': repo, 'revision': revision, 'license': 'Apache-2.0',
                          'files': [{'path': str(p.relative_to(ROOT)), 'sha256': sha256(p),
                                     'bytes': p.stat().st_size} for p in folder.rglob('*')
                                    if p.is_file() and '.cache' not in p.parts]})
        import easyocr
        easyocr.Reader(['en'], gpu=False, model_storage_directory=str(MODELS / 'easyocr'),
                       user_network_directory=str(MODELS / 'easyocr/network'), verbose=False)
        record('easyocr', {'source': 'https://github.com/JaidedAI/EasyOCR',
                           'files': [{'path': str(p.relative_to(ROOT)), 'sha256': sha256(p),
                                      'bytes': p.stat().st_size} for p in (MODELS / 'easyocr').glob('*.pth')]})
    if args.group in ('all', 'reid'):
        name = 'veri_sbs_R50-ibn.pth'
        entry = download(f'https://github.com/JDAI-CV/fast-reid/releases/download/v0.1.1/{name}', MODELS / name)
        entry.update(training_dataset='VeRi', source='https://github.com/JDAI-CV/fast-reid/blob/master/MODEL_ZOO.md')
        record(name, entry)
    save_json(MODELS / 'download-status.json', {'completed_at': datetime.now(timezone.utc).isoformat(), 'group': args.group})


if __name__ == '__main__':
    main()
