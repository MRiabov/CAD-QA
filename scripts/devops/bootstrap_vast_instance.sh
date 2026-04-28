#!/usr/bin/env bash
set -euo pipefail

python -m pip install --upgrade pip
python -m pip install uv

CADQA_EXTRAS="${CADQA_EXTRAS:-dev,cadquery,training}"
python -m pip install -e ".[${CADQA_EXTRAS}]"

python - <<'PY'
import importlib.util

print("Python environment ready.")
for name in ("torch", "transformers", "trl", "unsloth", "cadquery"):
    print(f"{name}: {'present' if importlib.util.find_spec(name) else 'missing'}")

if importlib.util.find_spec("torch"):
    import torch

    print(f"torch: {torch.__version__}")
    print(f"cuda_available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"gpu: {torch.cuda.get_device_name(0)}")
PY

echo "Bootstrap complete. Override CADQA_EXTRAS to change installed extras."
