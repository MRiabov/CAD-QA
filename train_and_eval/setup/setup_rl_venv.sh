#!/bin/bash
set -x
cd /root/cadqa-bench
export PATH="$HOME/.local/bin:$PATH"
if ! command -v uv >/dev/null; then
  curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1
fi
export PATH="$HOME/.local/bin:$PATH"
uv --version
uv venv /root/cadqa-rl-venv --python 3.12
uv pip install --python /root/cadqa-rl-venv -r /root/cadqa-bench/requirements.rl.txt
echo "RL_VENV_READY"
/root/cadqa-rl-venv/bin/python -c "import vllm, trl, unsloth, torch; print('vllm', vllm.__version__, '| trl', trl.__version__, '| torch', torch.__version__, '| unsloth ok')"
