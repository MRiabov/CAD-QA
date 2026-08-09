#!/bin/bash
export PATH="$HOME/.local/bin:$PATH"
pkill -9 -f "grpo_trai[n].py" 2>/dev/null
uv pip uninstall --python /root/cadqa-rl-venv vllm 2>&1 | tail -1
uv pip install --python /root/cadqa-rl-venv -q "transformers==5.5.0" 2>&1 | tail -1
/root/cadqa-rl-venv/bin/python -c "
import trl, unsloth, torch, transformers
from trl import GRPOTrainer
print('IMPORTS-OK | trl', trl.__version__, '| transformers', transformers.__version__, '| torch', torch.__version__, '| unsloth', unsloth.__version__)
"
