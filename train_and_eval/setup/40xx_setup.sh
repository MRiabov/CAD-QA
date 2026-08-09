#!/bin/bash
# 40xx (Ada sm_89) setup: Path-1 env (unsloth fast kernels, no vllm) + trl patches + model
set -x
export PATH="$HOME/.local/bin:$PATH"
cd /root/cadqa-bench

# 0) HF DNS check + pin workaround if poisoned
HF_IP=$(python3 -c "import socket; print(socket.gethostbyname('huggingface.co'))" 2>/dev/null)
echo "HF DNS: $HF_IP"
case "$HF_IP" in
  199.59.*) echo "DNS poisoned; pinning CloudFront"; echo "54.230.114.8 huggingface.co" >> /etc/hosts;;
  *) echo "DNS clean";;
esac
export HF_HUB_DISABLE_XET=1

# 1) uv + venv
if ! command -v uv >/dev/null; then curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1; fi
export PATH="$HOME/.local/bin:$PATH"
uv venv /root/cadqa-rl-venv --python 3.12
uv pip install --python /root/cadqa-rl-venv -r /root/cadqa-bench/requirements.path1.txt
echo "VENV_READY"

# 2) trl patches (vllm is absent; guard its imports)
/root/cadqa-rl-venv/bin/python - <<'PYEOF'
import glob
base = "/root/cadqa-rl-venv/lib/python3.12/site-packages/trl/"
targets = [
    "trainer/grpo_trainer.py",
    "trainer/rloo_trainer.py",
    "scripts/vllm_serve.py",
    "extras/vllm_client.py",
]
for rel in targets:
    p = base + rel
    s = open(p).read()
    orig = s
    # GuidedDecodingParams guard
    s = s.replace(
        "    from vllm.sampling_params import GuidedDecodingParams",
        "    try:\n        from vllm.sampling_params import GuidedDecodingParams\n    except ImportError:\n        GuidedDecodingParams = None")
    # unguarded vllm imports -> try/except
    for imp in ("from vllm.distributed.device_communicators.pynccl import PyNcclCommunicator",
                "from vllm import LLM, SamplingParams"):
        if imp in s and "try:" not in s.split(imp)[0][-30:]:
            s = s.replace(imp, "try:\n    " + imp + "\nexcept ImportError:\n    " + imp.split(" import ")[1].split(",")[0] + " = None")
    if s != orig:
        open(p, "w").write(s)
        print("patched", rel)
PYEOF
echo "TRL_PATCHED"
/root/cadqa-rl-venv/bin/python -c "from trl import GRPOTrainer; print('GRPO_IMPORT_OK')"

# 3) model download (4-bit unsloth repo)
HF_HUB_DISABLE_XET=1 /root/cadqa-rl-venv/bin/python -c "
from huggingface_hub import snapshot_download
print('DL_DONE', snapshot_download('unsloth/gemma-4-e2b-it-unsloth-bnb-4bit'))
" 2>&1 | tail -1

# 4) 4-bit load probe (fallback: bf16)
/root/cadqa-rl-venv/bin/python - <<'PYEOF'
import torch
from unsloth import FastModel
try:
    m, t = FastModel.from_pretrained(
        model_name="unsloth/gemma-4-e2b-it-unsloth-bnb-4bit",
        max_seq_length=3072, dtype=None, load_in_4bit=True)
    print("PROBE_4BIT_OK")
except Exception as e:
    print("PROBE_4BIT_FAIL", str(e)[:120])
    m, t = FastModel.from_pretrained(
        model_name="unsloth/gemma-4-e2b-it-unsloth-bnb-4bit",
        max_seq_length=3072, dtype=torch.bfloat16, load_in_4bit=False)
    print("PROBE_BF16_OK")
PYEOF
echo "40XX_SETUP_DONE"
