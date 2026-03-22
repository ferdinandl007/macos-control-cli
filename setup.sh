#!/usr/bin/env bash
set -euo pipefail

VENV_DIR="$HOME/.openclaw/tools/desktop-control/.venv"
MODEL_DIR="$HOME/.openclaw/models/omniparser"

echo "=== Desktop Control Setup ==="

# 1. Create venv with uv + Python 3.12
echo "[1/3] Creating venv at $VENV_DIR ..."
mkdir -p "$(dirname "$VENV_DIR")"
/opt/homebrew/bin/uv venv --python python3.12 "$VENV_DIR"

# 2. Install Python dependencies
echo "[2/3] Installing Python dependencies ..."
/opt/homebrew/bin/uv pip install --python "$VENV_DIR/bin/python" \
    torch \
    torchvision \
    ultralytics \
    transformers \
    Pillow \
    huggingface_hub \
    numpy

# 3. Download OmniParser v2 models
echo "[3/3] Downloading OmniParser v2 models ..."
mkdir -p "$MODEL_DIR"

"$VENV_DIR/bin/python" - <<'PYEOF'
import os
from huggingface_hub import snapshot_download

model_dir = os.path.expanduser("~/.openclaw/models/omniparser")

print("Downloading icon_detect model...")
snapshot_download(
    repo_id="microsoft/OmniParser-v2.0",
    allow_patterns=["icon_detect/*"],
    local_dir=model_dir,
)

print("Downloading icon_caption model...")
snapshot_download(
    repo_id="microsoft/OmniParser-v2.0",
    allow_patterns=["icon_caption/*"],
    local_dir=model_dir,
)

print("Models downloaded to:", model_dir)
for root, dirs, files in os.walk(model_dir):
    for f in files:
        path = os.path.join(root, f)
        size_mb = os.path.getsize(path) / (1024 * 1024)
        print(f"  {os.path.relpath(path, model_dir)} ({size_mb:.1f} MB)")
PYEOF

echo ""
echo "=== Setup complete ==="
echo "Venv: $VENV_DIR"
echo "Models: $MODEL_DIR"
echo "Test with: $VENV_DIR/bin/python skills/desktop-control/test_vision.py"
