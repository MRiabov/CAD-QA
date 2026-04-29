#!/usr/bin/env bash
set -euo pipefail

# Bootstrap a Vast PyTorch image for CAD-QA experiments.
#
# Use the image's existing Python environment. Creating a second virtualenv or
# resolving the project training extra on these images can replace a working
# CUDA stack with packages that do not support the live driver.

PYTHON_BIN="${PYTHON_BIN:-python}"
export HF_HUB_ENABLE_HF_TRANSFER="${HF_HUB_ENABLE_HF_TRANSFER:-1}"
export WANDB_DISABLED="${WANDB_DISABLED:-true}"
export TOKENIZERS_PARALLELISM="${TOKENIZERS_PARALLELISM:-false}"
export PIP_ROOT_USER_ACTION="${PIP_ROOT_USER_ACTION:-ignore}"

"$PYTHON_BIN" -m pip install --upgrade pip wheel packaging
"$PYTHON_BIN" -m pip install --upgrade --index-url https://download.pytorch.org/whl/cu128 \
  "torch==2.10.0" torchvision torchaudio
"$PYTHON_BIN" -m pip install --upgrade \
  hf_transfer \
  huggingface_hub \
  datasets \
  "transformers==5.5.0" \
  "trl==0.24.0" \
  peft \
  bitsandbytes \
  accelerate \
  python-dotenv \
  pydantic \
  PyYAML \
  psutil

# Qwen3.5 uses gated-delta/linear-attention kernels. Install these without
# dependency resolution so pip cannot swap out the CUDA 12.8 Torch build.
"$PYTHON_BIN" -m pip install --upgrade --no-deps flash-linear-attention einops || true
TORCH_CUDA_ARCH_LIST="${TORCH_CUDA_ARCH_LIST:-8.0}" MAX_JOBS="${MAX_JOBS:-4}" \
  "$PYTHON_BIN" -m pip install --upgrade --no-build-isolation --no-deps causal-conv1d || true

"$PYTHON_BIN" -m pip install --upgrade "unsloth==2026.4.8"
"$PYTHON_BIN" -m pip install --no-build-isolation --no-deps --ignore-requires-python -e .

"$PYTHON_BIN" - <<'PY'
import importlib.util

print("Python environment ready.")
for name in ("torch", "transformers", "trl", "unsloth"):
    print(f"{name}: {'present' if importlib.util.find_spec(name) else 'missing'}")

if importlib.util.find_spec("torch"):
    import torch

    print(f"torch: {torch.__version__}")
    print(f"cuda_available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"gpu: {torch.cuda.get_device_name(0)}")
PY

echo "Bootstrap complete. Use configs/overnight_experiment_suite_vast.yaml on this instance."
