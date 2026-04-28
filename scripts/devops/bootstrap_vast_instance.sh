#!/usr/bin/env bash
set -euo pipefail

python -m pip install --upgrade pip
python -m pip install -e ".[dev]"

echo "Bootstrap complete. Install GPU training dependencies separately if running Unsloth SFT."
