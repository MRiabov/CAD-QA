"""Answer-only SFT entrypoint.

This script intentionally gates real training when GPU-only dependencies are
missing. It preserves a structured result so the experiment runner can record
why the canary did not launch on a local CPU machine.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

from cad_qa.jsonio import read_jsonl, write_json


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--sft-dir", type=Path)
    parser.add_argument("--model", default="unsloth/Qwen3.5-4B")
    parser.add_argument("--max-train-rows", type=int, default=256)
    parser.add_argument("--max-eval-rows", type=int, default=64)
    parser.add_argument("--max-steps", type=int, default=20)
    parser.add_argument("--per-device-train-batch-size", type=int, default=1)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=8)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--max-seq-length", type=int, default=4096)
    parser.add_argument("--dry-run", action="store_true")
    args, _unknown = parser.parse_known_args(argv)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    sft_dir = args.sft_dir or args.output_dir / "sft_dataset"
    train_count = _row_count(sft_dir / "train.jsonl")
    eval_count = _row_count(sft_dir / "validation.jsonl")
    result = {
        "schema": "cadqa_unsloth_sft_result_v1",
        "status": "dry_run" if args.dry_run else "gated",
        "model": args.model,
        "dataset_dir": str(args.dataset_dir),
        "sft_dir": str(sft_dir),
        "train_count": train_count,
        "eval_count": eval_count,
        "max_steps": args.max_steps,
        "reason": None,
    }
    if args.dry_run:
        result["reason"] = "dry_run_requested"
        write_json(args.output_dir / "train_result.json", result)
        print(json.dumps(result, indent=2, sort_keys=True))
        return
    missing = [name for name in ("datasets", "torch", "transformers", "trl", "unsloth") if importlib.util.find_spec(name) is None]
    if missing:
        result["reason"] = f"missing_training_dependencies:{','.join(missing)}"
        write_json(args.output_dir / "train_result.json", result)
        print(json.dumps(result, indent=2, sort_keys=True))
        raise SystemExit(2)
    train_result = _run_training(args, sft_dir)
    result.update(train_result)
    write_json(args.output_dir / "train_result.json", result)
    print(json.dumps(result, indent=2, sort_keys=True))


def _row_count(path: Path) -> int:
    if not path.exists():
        return 0
    return len(read_jsonl(path))


def _run_training(args: argparse.Namespace, sft_dir: Path) -> dict[str, Any]:
    from datasets import Dataset  # type: ignore[import-not-found]
    from transformers import TrainingArguments  # type: ignore[import-not-found]
    from trl import SFTTrainer  # type: ignore[import-not-found]
    from unsloth import FastLanguageModel  # type: ignore[import-not-found]

    train_rows = read_jsonl(sft_dir / "train.jsonl")[: args.max_train_rows]
    eval_rows = read_jsonl(sft_dir / "validation.jsonl")[: args.max_eval_rows]
    train_dataset = Dataset.from_list([{"text": _chat_text(row)} for row in train_rows])
    eval_dataset = Dataset.from_list([{"text": _chat_text(row)} for row in eval_rows]) if eval_rows else None
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=args.model,
        max_seq_length=args.max_seq_length,
        load_in_4bit=True,
    )
    model = FastLanguageModel.get_peft_model(
        model,
        r=16,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_alpha=16,
        lora_dropout=0,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=1234,
    )
    training_args = TrainingArguments(
        output_dir=str(args.output_dir / "trainer"),
        per_device_train_batch_size=args.per_device_train_batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        learning_rate=args.learning_rate,
        max_steps=args.max_steps,
        logging_steps=1,
        save_steps=max(args.max_steps, 1),
        report_to=[],
    )
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        dataset_text_field="text",
        max_seq_length=args.max_seq_length,
        args=training_args,
    )
    train_output = trainer.train()
    model.save_pretrained(args.output_dir / "adapter")
    tokenizer.save_pretrained(args.output_dir / "adapter")
    metrics = getattr(train_output, "metrics", {}) or {}
    return {
        "status": "completed",
        "reason": None,
        "train_metrics": metrics,
        "adapter_dir": str(args.output_dir / "adapter"),
    }


def _chat_text(row: dict[str, Any]) -> str:
    messages = row.get("messages")
    if not isinstance(messages, list):
        return ""
    parts = []
    for message in messages:
        if isinstance(message, dict):
            parts.append(f"<|{message.get('role', 'user')}|>\n{message.get('content', '')}")
    parts.append("<|end|>")
    return "\n".join(parts)


if __name__ == "__main__":
    main(sys.argv[1:])
