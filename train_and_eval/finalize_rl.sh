#!/bin/bash
cd /root/cadqa-bench
export PATH="$HOME/.local/bin:$PATH"
pkill -9 -f "grpo_train\.py" 2>/dev/null
echo "== installing rl6 =="
uv pip install --python /root/cadqa-rl-venv -r requirements.rl6.txt 2>&1 | tail -2
echo "== imports =="
/root/cadqa-rl-venv/bin/python -c "
import vllm, trl, unsloth, torch
from vllm.sampling_params import GuidedDecodingParams
import trl.trainer.grpo_trainer
print('IMPORTS-OK | vllm', vllm.__version__, '| trl', trl.__version__, '| torch', torch.__version__, '| unsloth', unsloth.__version__)
"
echo "== grpo 1-step test =="
rm -f grpo_test.log
CADQA_RL_ROWS=8 CADQA_RL_STEPS=1 CADQA_RL_GEN=2 CADQA_RL_BS=1 CADQA_RL_OUT=/root/cadqa-rl-test \
  /root/cadqa-rl-venv/bin/python /root/cadqa-bench/grpo_train.py > grpo_test.log 2>&1
echo "grpo exit: $?"
grep -E "train rows|reward|step|{'loss'|GRPO_DONE|Error|Traceback" grpo_test.log | tail -5
echo "ALL_FINALIZE_DONE"
