



import sys, os as _os
sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))  # train_and_eval root
import json, sys
sys.path.insert(0, "/root/cadqa-bench")
import torch
from datasets import load_dataset
from unsloth import FastVisionModel
from reward_cadqa import reward_cadqa

model, tokenizer = FastVisionModel.from_pretrained(
    model_name="unsloth/gemma-4-E2B-it", max_seq_length=8192,
    load_in_4bit=True, fast_inference=False)
tok = getattr(tokenizer, "tokenizer", tokenizer)

ds = load_dataset("MRiabov/cadqa-rl-2000", split="train").select(range(2))
prompts, golds, fmts = [], [], []
for r in ds:
    prompts.append(r["prompt"]); golds.append(r["gold_answer"]); fmts.append(r["answer_format"])

completions = []
for i, p in enumerate(prompts):
    msgs = [{"role": "user", "content": p}]
    inputs = tokenizer.apply_chat_template(msgs, add_generation_prompt=True, tokenize=True, return_dict=True, return_tensors="pt").to("cuda")
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=1024, temperature=1.0, top_p=0.95, top_k=64, do_sample=True)
    comp = tok.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()
    completions.append([{"role": "assistant", "content": comp}])
    try: gold = json.loads(json.loads(golds[i]))
    except Exception: gold = golds[i]
    print(f"=== row {i} | fmt={fmts[i]} | gold={gold!r}")
    print("   C:", repr(comp[:280]))
    print()
scores = reward_cadqa(completions, gold_answer=golds, answer_format=fmts)
print("REWARD SCORES:", scores)
