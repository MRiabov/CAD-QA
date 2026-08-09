#!/bin/bash
# Official E2B RL notebook environment (unsloth.ai/docs/models/gemma-4/train + Sudoku notebook)
set -x
export PATH="$HOME/.local/bin:$PATH"
cd /root/cadqa-bench
if ! command -v uv >/dev/null; then curl -LsSf https://astral.sh/uv/install.sh | sh > /dev/null 2>&1; fi
export PATH="$HOME/.local/bin:$PATH"

pkill -9 -f "grpo_trai[n].py" 2>/dev/null
rm -rf /root/cadqa-rl-venv
uv venv /root/cadqa-rl-venv --python 3.12

# Exact install cell from Gemma4_(E2B)_Reinforcement_Learning_Sudoku_Game.ipynb
uv pip install --python /root/cadqa-rl-venv -qqq \
    "torch>=2.8.0" "triton>=3.4.0" numpy pillow torchvision bitsandbytes \
    "unsloth_zoo[base] @ git+https://github.com/unslothai/unsloth-zoo" \
    "unsloth[base] @ git+https://github.com/unslothai/unsloth" \
    git+https://github.com/triton-lang/triton.git@0add68262ab0a2e33b84524346cb27cbb2787356#subdirectory=python/triton_kernels
uv pip install --python /root/cadqa-rl-venv --upgrade --no-deps \
    "transformers>=5.5.0" "tokenizers>=0.22.0,<=0.23.0" "trl>=0.28.0" unsloth unsloth_zoo
uv pip install --python /root/cadqa-rl-venv -qqq "huggingface_hub>=1.5.0,<2.0"
uv pip install --python /root/cadqa-rl-venv --no-deps --upgrade timm

echo "NOTEBOOK_ENV_READY"
/root/cadqa-rl-venv/bin/python -c "import unsloth, trl, transformers, torch; print('unsloth', unsloth.__version__, '| trl', trl.__version__, '| transformers', transformers.__version__, '| torch', torch.__version__)"
/root/cadqa-rl-venv/bin/python -c "from unsloth import FastVisionModel; from trl import GRPOTrainer, GRPOConfig; print('IMPORTS_OK')"
