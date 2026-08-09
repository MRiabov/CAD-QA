#!/bin/bash
set -x
export PATH="$HOME/.local/bin:$PATH"
pkill -9 -f "bench_vllm\.py" 2>/dev/null
rm -rf /root/cadqa-rl-venv
uv venv /root/cadqa-rl-venv --python 3.12
uv pip install --python /root/cadqa-rl-venv -r /root/cadqa-bench/requirements.rl5.txt
echo "RL_VENV_READY"
/root/cadqa-rl-venv/bin/python -c "import vllm, trl, unsloth, torch; print('vllm', vllm.__version__, '| trl', trl.__version__, '| torch', torch.__version__, '| unsloth', unsloth.__version__)"
