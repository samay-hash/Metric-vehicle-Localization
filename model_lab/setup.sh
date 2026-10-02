#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export UV_CACHE_DIR="$PWD/.cache/uv"
mkdir -p models runs vendor .cache
uv venv --python "${LAB_PYTHON:-python3.12}" .venv
uv pip install --python .venv/bin/python -r requirements-lock-macos-arm64.txt
if [[ ! -d vendor/fast-reid/.git ]]; then
  git clone https://github.com/JDAI-CV/fast-reid.git vendor/fast-reid
fi
git -C vendor/fast-reid checkout c9bc3ceb2f7a6438b62fb515ea3df6d1e999e95d
.venv/bin/python download_models.py
