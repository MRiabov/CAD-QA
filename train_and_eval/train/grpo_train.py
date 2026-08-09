"""CAD-QA GRPO training for google/gemma-4-E2B-it.

Follows the official Unsloth Gemma 4 E2B RL notebook exactly
(https://colab.research.google.com/github/unslothai/notebooks/blob/main/nb/Gemma4_(E2B)_Reinforcement_Learning_Sudoku_Game.ipynb):
FastVisionModel, 16-bit LoRA, fast_inference=False (vLLM cannot load gemma-4), bnpo GRPO.
Env knobs: CADQA_RL_ROWS, CADQA_RL_STEPS, CADQA_RL_GEN, CADQA_RL_BS, CADQA_RL_OUT, CADQA_RL_LOSS.
"""




import sys, os as _os
sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))  # train_and_eval root
import json
import os
import sys

sys.path.insert(0, "/root/cadqa-bench")
from datasets import Dataset, load_dataset
import torch
from trl import GRPOConfig, GRPOTrainer
from unsloth import FastVisionModel

from reward_cadqa import reward_cadqa

N_ROWS = int(os.environ.get("CADQA_RL_ROWS", "512"))
MAX_STEPS = int(os.environ.get("CADQA_RL_STEPS", "60"))
NUM_GEN = int(os.environ.get("CADQA_RL_GEN", "2"))
BS = int(os.environ.get("CADQA_RL_BS", "1"))
OUT = os.environ.get("CADQA_RL_OUT", "/root/cadqa-rl-out")
LOSS = os.environ.get("CADQA_RL_LOSS", "bnpo")  # notebook default; 'grpo' also fine

max_seq_length = int(os.environ.get("CADQA_RL_SEQ", "16384"))  # 16K traces (hard requirement); fits 24GB 4090 at bs=4
lora_rank = 32

# --- model load (notebook cell 6) ---
model, tokenizer = FastVisionModel.from_pretrained(
    model_name="unsloth/gemma-4-E2B-it",
    max_seq_length=max_seq_length,
    load_in_4bit=False,  # 16-bit LoRA: proven at 4096/bs=1 on 16 GB (notebook default)
    fast_inference=False,  # vLLM cannot load gemma-4; use Unsloth inference
)

# --- LoRA (notebook cell 8) ---
model = FastVisionModel.get_peft_model(
    model,
    r=lora_rank,
    target_modules=[
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],
    lora_alpha=lora_rank * 2,
    use_gradient_checkpointing="unsloth",
    random_state=3407,
)

# --- dataset: HF cadqa-rl-2000, prompt as messages (notebook cell 41 format) ---
raw = load_dataset("MRiabov/cadqa-rl-2000", "v2_curriculum", split="train").select(range(N_ROWS))
rows = []
for r in raw:
    rows.append({
        "prompt": r["prompt"],
        "gold_answer": r["gold_answer"],
        "answer_format": r["answer_format"],
        "row_id": r["row_id"],
        "logical_hop_count": r["logical_hop_count"],
    })

# Curriculum: hop-ascending buckets (0 -> 2 -> 3 -> 4 -> 5) with weighted step shares;
# rows cycle within a bucket (seeded within-bucket shuffle); trainer shuffle disabled.
HOP_SHARES = json.loads(os.environ.get("CADQA_RL_HOP_SHARES", '{"0": 0.25, "2": 0.10, "3": 0.15, "4": 0.25, "5": 0.25}'))
import random as _random
_rng = _random.Random(42)
hops = sorted({r["logical_hop_count"] for r in rows})
buckets = {hop: [r for r in rows if r["logical_hop_count"] == hop] for hop in hops}
for hop in buckets:
    _rng.shuffle(buckets[hop])
ordered = []
allocated = 0
for hop in hops:
    share = round(MAX_STEPS * HOP_SHARES.get(str(hop), 0.0))
    share = min(share, MAX_STEPS - allocated)
    for i in range(share):
        ordered.append(buckets[hop][i % len(buckets[hop])])
    allocated += share
    print(f"curriculum stage hop={hop}: {len(buckets[hop])} rows -> {share} steps", flush=True)
if allocated < MAX_STEPS:
    tail = buckets[hops[-1]]
    for i in range(MAX_STEPS - allocated):
        ordered.append(tail[i % len(tail)])
    print(f"curriculum stage hop={hops[-1]} (tail): +{MAX_STEPS - allocated} steps", flush=True)
rows = ordered

rows_final = []
max_prompt_tokens = 0
for r in rows:
    prompt_messages = [{"role": "user", "content": r["prompt"]}]
    n = len(tokenizer.apply_chat_template(prompt_messages, add_generation_prompt=True, tokenize=True))
    max_prompt_tokens = max(max_prompt_tokens, n)
    rows_final.append({
        "prompt": prompt_messages,
        "gold_answer": r["gold_answer"],
        "answer_format": r["answer_format"],
        "row_id": r["row_id"],
    })
dataset = Dataset.from_list(rows_final)
print(f"train rows: {len(dataset)} (curriculum-ordered) | max prompt tokens: {max_prompt_tokens}", flush=True)

# --- GRPO config (notebook cell 43, env overrides for smoke runs) ---
max_completion_length = int(os.environ.get("CADQA_RL_MAXCOMP", "8192"))  # bounded rambling; 16K total context
training_args = GRPOConfig(
    temperature=1.0,
    learning_rate=5e-5,
    weight_decay=0.001,
    warmup_ratio=0.1,
    lr_scheduler_type="linear",
    optim="adamw_8bit",
    logging_steps=1,
    per_device_train_batch_size=BS,
    gradient_accumulation_steps=2,
    num_generations=NUM_GEN,
    generation_batch_size=4,
    shuffle_dataset=False,  # curriculum: iterate hop-ordered rows  # must be divisible by num_generations
    max_completion_length=max_completion_length,
    max_steps=MAX_STEPS,
    save_strategy="no",
    report_to="none",
    output_dir=OUT,
    epsilon=0.2,
    epsilon_high=0.28,
    delta=1.5,
    loss_type=LOSS,
    mask_truncated_completions=True,
)

# --- trainer (notebook cell 45) ---
trainer = GRPOTrainer(
    model=model,
    processing_class=tokenizer,
    reward_funcs=[reward_cadqa],
    args=training_args,
    train_dataset=dataset,
)

trainer.train()
model.save_pretrained(OUT)
tokenizer.save_pretrained(OUT)
print("GRPO_DONE", OUT, flush=True)
