"""Paths and local-only runtime settings for the independent model lab."""
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
MODELS = ROOT / 'models'
RUNS = ROOT / 'runs'
for key, value in {
    'HF_HOME': ROOT / '.cache/huggingface',
    'YOLO_CONFIG_DIR': ROOT / '.cache/ultralytics',
    'TORCH_HOME': ROOT / '.cache/torch',
    'PADDLE_HOME': ROOT / '.cache/paddle',
    'PADDLE_PDX_CACHE_HOME': ROOT / '.cache/paddlex',
    'MPLCONFIGDIR': ROOT / '.cache/matplotlib',
}.items():
    value.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault(key, str(value))
os.environ.setdefault('PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK', 'True')
os.environ.setdefault('OMP_NUM_THREADS', '2')
os.environ.setdefault('MKL_NUM_THREADS', '2')
os.environ.setdefault('ULTRALYTICS_AUTOINSTALL', 'false')


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
