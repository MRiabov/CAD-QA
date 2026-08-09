



import sys, os as _os
sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))  # train_and_eval root
import glob, time
from vllm import LLM, SamplingParams

snap = sorted(glob.glob("/root/.cache/huggingface/hub/models--google--gemma-4-E2B-it/snapshots/*/"))[0]
print("model:", snap, flush=True)
t0 = time.time()
llm = LLM(model=snap, dtype="bfloat16", gpu_memory_utilization=0.7, max_model_len=8192, trust_remote_code=False)
print("engine_load_secs:", round(time.time() - t0, 1), flush=True)
prompts = ["Write a short CadQuery script that creates a 10x10x10 box and prints its volume. Keep it short."] * 8
sp = SamplingParams(temperature=0.2, top_p=0.95, top_k=64, max_tokens=256)
t1 = time.time()
outs = llm.generate(prompts, sp)
dt = time.time() - t1
n = sum(len(o.outputs[0].token_ids) for o in outs)
print(f"vllm: {len(outs)} seqs, {n} tokens in {round(dt,2)}s -> tok_s={round(n/dt,1)}", flush=True)
print("VLLM_DONE", flush=True)
