#!/usr/bin/env python
"""CAD-QA GRPO training for google/gemma-4-E2B-it (unsloth + TRL).

Run on a CUDA box with unsloth + trl installed (proven on A100/4090-class;
Blackwell consumer GPUs are slow for rollout generation). Rollouts use vLLM
(`use_vllm=True`) for CUDA-graph-fast generation.

Data: https://huggingface.co/datasets/MRiabov/cadqa-rl-2000 (train=2000, validation=98)
Reward: runs/gemma_bench/rl/reward_cadqa.py (exact-match, mirrors the repo grader)

Env knobs:
  CADQA_RL_MODEL  model id (default unsloth/gemma-4-E2B-it)
  CADQA_RL_ROWS   number of train rows (default 512)
  CADQA_RL_STEPS  max steps (default 60)
  CADQA_RL_BS     per-device batch (default 2)
  CADQA_RL_GEN    rollouts per prompt (default 4)
  CADQA_RL_OUT    output dir (default /root/cadqa-rl-out)
"""

import os
import re
import sys

os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

from datasets import load_dataset  # noqa: E402
from trl import GRPOTrainer, GRPOConfig  # noqa: E402
from unsloth import FastModel  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reward_cadqa import reward_cadqa  # noqa: E402

MODEL = os.environ.get("CADQA_RL_MODEL", "unsloth/gemma-4-E2B-it")
N_ROWS = int(os.environ.get("CADQA_RL_ROWS", "512"))
MAX_STEPS = int(os.environ.get("CADQA_RL_STEPS", "60"))
PER_DEVICE_BS = int(os.environ.get("CADQA_RL_BS", "2"))
NUM_GEN = int(os.environ.get("CADQA_RL_GEN", "4"))
OUT = os.environ.get("CADQA_RL_OUT", "/root/cadqa-rl-out")


def _clean_completion(text: str) -> str:
    """Extract the model's answer from a raw completion."""
    m = re.search(r"FINAL\s*ANSWER\s*:?\s*(.+)", text, re.DOTALL)
    if m:
        text = m.group(1)
    m = re.search(r"```(?:python|py)?\s*\n(.*?)```", text, re.DOTALL)
    if m:
        text = m.group(1)
    text = re.sub(r"<[^>]*turn[^>]*>", "", text)
    return text.strip()


def cadqa_reward(prompts, completions, answer_format, gold_answer, **kwargs):
    return [
        reward_cadqa(g, f, _clean_completion(c))
        for g, f, c in zip(gold_answer, answer_format, completions)
    ]


def load_model():
    model, tokenizer = FastModel.from_pretrained(
        model_name=MODEL, max_seq_length=3072, dtype=None, load_in_4bit=True,
    )
    model = FastModel.get_peft_model(
        model,
        r=16,
        lora_alpha=16,
        lora_dropout=0,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        use_gradient_checkpointing="unsloth",
        random_state=42,
    )
    return model, tokenizer


def main() -> None:
    ds = load_dataset("MRiabov/cadqa-rl-2000", split="train").select(range(N_ROWS))
    print("train rows:", len(ds), flush=True)
    model, tokenizer = load_model()

    config = GRPOConfig(
        output_dir=OUT,
        learning_rate=5e-6,
        warmup_ratio=0.1,
        lr_scheduler_type="cosine",
        per_device_train_batch_size=PER_DEVICE_BS,
        num_generations=NUM_GEN,
        max_prompt_length=1536,
        max_completion_length=512,
        num_train_epochs=1,
        beta=0.04,
        bf16=True,
        logging_steps=1,
        save_steps=MAX_STEPS,
        max_steps=MAX_STEPS,
        use_vllm=True,
        vllm_gpu_memory_utilization=0.5,
        vllm_device="cuda",
    )
    trainer = GRPOTrainer(
        model=model,
        processing_class=tokenizer,
        args=config,
        train_dataset=ds,
        reward_funcs=[cadqa_reward],
    )
    trainer.train()
    trainer.save_model(os.path.join(OUT, "adapter"))
    print("GRPO_DONE saved to", os.path.join(OUT, "adapter"), flush=True)


if __name__ == "__main__":
    main()
