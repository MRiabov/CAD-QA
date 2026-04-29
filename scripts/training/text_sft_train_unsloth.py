"""Answer-only SFT entrypoint.

This script intentionally gates real training when GPU-only dependencies are
missing. It preserves a structured result so the experiment runner can record
why the canary did not launch on a local CPU machine.
"""

from __future__ import annotations

import argparse
import inspect
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
    parser.add_argument(
        "--pack-tokenized", action=argparse.BooleanOptionalAction, default=False
    )
    parser.add_argument(
        "--assistant-only-loss", action=argparse.BooleanOptionalAction, default=False
    )
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
    missing = [
        name
        for name in ("datasets", "torch", "transformers", "trl", "unsloth")
        if importlib.util.find_spec(name) is None
    ]
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
    import torch  # type: ignore[import-not-found]
    from transformers import Trainer  # type: ignore[import-not-found]
    from trl import SFTTrainer  # type: ignore[import-not-found]

    try:
        from trl import SFTConfig  # type: ignore[import-not-found]
    except ImportError:
        from transformers import TrainingArguments as SFTConfig  # type: ignore[import-not-found,no-redef]
    try:
        from unsloth import FastModel  # type: ignore[import-not-found]
    except ImportError:
        FastModel = None
        from unsloth import FastLanguageModel  # type: ignore[import-not-found]
    else:
        FastLanguageModel = None

    train_rows = read_jsonl(sft_dir / "train.jsonl")[: args.max_train_rows]
    eval_rows = read_jsonl(sft_dir / "validation.jsonl")[: args.max_eval_rows]
    if FastModel is not None:
        model, tokenizer = FastModel.from_pretrained(
            model_name=args.model,
            max_seq_length=args.max_seq_length,
            load_in_4bit=True,
            full_finetuning=False,
        )
        model = FastModel.get_peft_model(
            model,
            finetune_language_layers=True,
            finetune_attention_modules=True,
            finetune_mlp_modules=True,
            r=16,
            lora_alpha=16,
            lora_dropout=0,
            bias="none",
            random_state=1234,
            use_rslora=False,
            loftq_config=None,
        )
        FastModel.for_training(model)
    else:
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=args.model,
            max_seq_length=args.max_seq_length,
            load_in_4bit=True,
        )
        model = FastLanguageModel.get_peft_model(
            model,
            r=16,
            target_modules=[
                "q_proj",
                "k_proj",
                "v_proj",
                "o_proj",
                "gate_proj",
                "up_proj",
                "down_proj",
            ],
            lora_alpha=16,
            lora_dropout=0,
            bias="none",
            use_gradient_checkpointing="unsloth",
            random_state=1234,
        )
    text_tokenizer = _text_tokenizer(tokenizer)
    if getattr(text_tokenizer, "pad_token", None) is None:
        text_tokenizer.pad_token = text_tokenizer.eos_token
    train_examples = [_sft_example(tokenizer, row) for row in train_rows]
    eval_examples = [_sft_example(tokenizer, row) for row in eval_rows]
    if args.pack_tokenized:
        train_dataset = Dataset.from_list(
            _pack_tokenized_examples(
                text_tokenizer, train_examples, args.max_seq_length
            )
        )
        eval_dataset = (
            Dataset.from_list(
                _pack_tokenized_examples(
                    text_tokenizer, eval_examples, args.max_seq_length
                )
            )
            if eval_examples
            else None
        )
    else:
        train_dataset = Dataset.from_list(
            [{"text": row["text"]} for row in train_examples]
        )
        eval_dataset = (
            Dataset.from_list([{"text": row["text"]} for row in eval_examples])
            if eval_examples
            else None
        )
    training_args = _build_training_args(args, SFTConfig, torch)
    if args.pack_tokenized:
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
            data_collator=lambda features: _causal_lm_collator(
                features,
                text_tokenizer.pad_token_id,
                pad_to_length=args.max_seq_length,
            ),
        )
    else:
        trainer_kwargs: dict[str, Any] = {
            "model": model,
            "args": training_args,
            "train_dataset": train_dataset,
            "eval_dataset": eval_dataset,
        }
        trainer_signature = inspect.signature(SFTTrainer.__init__).parameters
        if "processing_class" in trainer_signature:
            trainer_kwargs["processing_class"] = tokenizer
        elif "tokenizer" in trainer_signature:
            trainer_kwargs["tokenizer"] = tokenizer
        if "dataset_text_field" in trainer_signature:
            trainer_kwargs["dataset_text_field"] = "text"
        if "max_seq_length" in trainer_signature:
            trainer_kwargs["max_seq_length"] = args.max_seq_length
        trainer = SFTTrainer(**trainer_kwargs)
    train_output = trainer.train()
    trainer.save_model(str(args.output_dir / "adapter"))
    text_tokenizer.save_pretrained(args.output_dir / "adapter")
    metrics = getattr(train_output, "metrics", {}) or {}
    return {
        "status": "completed",
        "reason": None,
        "train_metrics": metrics,
        "adapter_dir": str(args.output_dir / "adapter"),
        "pack_tokenized": args.pack_tokenized,
        "assistant_only_loss": args.assistant_only_loss,
        "loss_masking": "packed_assistant_tokens_only"
        if args.pack_tokenized
        else (
            "trl_assistant_only_loss"
            if args.assistant_only_loss
            else "full_sequence_prompt_and_answer"
        ),
    }


def _build_training_args(
    args: argparse.Namespace, sft_config_cls: Any, torch_module: Any
) -> Any:
    kwargs: dict[str, Any] = {
        "output_dir": str(args.output_dir / "trainer"),
        "dataset_text_field": "text",
        "max_length": args.max_seq_length,
        "per_device_train_batch_size": args.per_device_train_batch_size,
        "gradient_accumulation_steps": args.gradient_accumulation_steps,
        "learning_rate": args.learning_rate,
        "max_steps": args.max_steps,
        "logging_steps": 1,
        "save_steps": max(args.max_steps, 1),
        "report_to": [],
        "bf16": torch_module.cuda.is_available()
        and torch_module.cuda.is_bf16_supported(),
        "fp16": torch_module.cuda.is_available()
        and not torch_module.cuda.is_bf16_supported(),
        "optim": "adamw_8bit",
        "packing": False,
        "assistant_only_loss": bool(
            args.assistant_only_loss and not args.pack_tokenized
        ),
    }
    signature = inspect.signature(sft_config_cls.__init__).parameters
    return sft_config_cls(
        **{key: value for key, value in kwargs.items() if key in signature}
    )


def _sft_example(tokenizer: Any, row: dict[str, Any]) -> dict[str, str]:
    messages = row.get("messages")
    if not isinstance(messages, list):
        return {"text": "", "prompt_text": ""}
    prompt_messages = _prompt_messages(messages)
    if hasattr(tokenizer, "apply_chat_template") and getattr(
        tokenizer, "chat_template", None
    ):
        prompt_text = _apply_chat_template(
            tokenizer, prompt_messages, add_generation_prompt=True
        )
        text = _apply_chat_template(tokenizer, messages, add_generation_prompt=False)
    else:
        prompt_text = _chat_text(prompt_messages)
        text = _chat_text(messages)
    return {"text": text, "prompt_text": prompt_text}


def _prompt_messages(messages: list[Any]) -> list[Any]:
    prompt_messages = list(messages)
    if (
        prompt_messages
        and isinstance(prompt_messages[-1], dict)
        and prompt_messages[-1].get("role") == "assistant"
    ):
        return prompt_messages[:-1]
    return prompt_messages


def _apply_chat_template(
    tokenizer: Any, messages: list[Any], *, add_generation_prompt: bool
) -> str:
    kwargs = {
        "tokenize": False,
        "add_generation_prompt": add_generation_prompt,
    }
    try:
        signature = inspect.signature(tokenizer.apply_chat_template).parameters
    except (TypeError, ValueError):
        signature = {}
    if "enable_thinking" in signature:
        kwargs["enable_thinking"] = False
    try:
        return tokenizer.apply_chat_template(messages, **kwargs)
    except TypeError:
        kwargs.pop("enable_thinking", None)
        return tokenizer.apply_chat_template(messages, **kwargs)


def _text_tokenizer(tokenizer_or_processor: Any) -> Any:
    return getattr(tokenizer_or_processor, "tokenizer", tokenizer_or_processor)


def _pack_tokenized_examples(
    tokenizer: Any, examples: list[dict[str, str]], max_seq_length: int
) -> list[dict[str, list[int]]]:
    eos_token_id = tokenizer.eos_token_id
    if eos_token_id is None:
        raise ValueError("Tokenizer must define eos_token_id for token packing.")
    token_stream: list[int] = []
    label_stream: list[int] = []
    packed: list[dict[str, list[int]]] = []
    for example in examples:
        full_token_ids = _encode_text(tokenizer, example["text"])
        prompt_token_ids = (
            _encode_text(tokenizer, example["prompt_text"])
            if example.get("prompt_text")
            else []
        )
        label_ids = full_token_ids.copy()
        label_ids[: min(len(prompt_token_ids), len(label_ids))] = [-100] * min(
            len(prompt_token_ids), len(label_ids)
        )
        has_supervised_target = any(label != -100 for label in label_ids)
        token_stream.extend(full_token_ids)
        label_stream.extend(label_ids)
        token_stream.append(eos_token_id)
        label_stream.append(eos_token_id if has_supervised_target else -100)
        while len(token_stream) >= max_seq_length:
            _append_supervised_chunk(
                packed, token_stream[:max_seq_length], label_stream[:max_seq_length]
            )
            token_stream = token_stream[max_seq_length:]
            label_stream = label_stream[max_seq_length:]
    if token_stream:
        _append_supervised_chunk(packed, token_stream, label_stream)
    if not packed and examples:
        raise ValueError(
            "No supervised packed chunks were produced. Increase --max-seq-length or reduce prompt length."
        )
    return packed


def _encode_text(tokenizer: Any, text: str) -> list[int]:
    encoded = tokenizer(text=text, add_special_tokens=False)
    input_ids = encoded["input_ids"]
    if input_ids and isinstance(input_ids[0], list):
        return list(input_ids[0])
    return list(input_ids)


def _append_supervised_chunk(
    packed: list[dict[str, list[int]]], input_ids: list[int], labels: list[int]
) -> None:
    if not any(label != -100 for label in labels):
        return
    packed.append(
        {
            "input_ids": list(input_ids),
            "attention_mask": [1] * len(input_ids),
            "labels": list(labels),
        }
    )


def _causal_lm_collator(
    features: list[dict[str, list[int]]],
    pad_token_id: int | None,
    *,
    pad_to_length: int | None = None,
) -> dict[str, Any]:
    import torch  # type: ignore[import-not-found]

    if pad_token_id is None:
        raise ValueError("Tokenizer must define pad_token_id for packed training.")
    max_len = max(len(feature["input_ids"]) for feature in features)
    if pad_to_length is not None:
        if max_len > pad_to_length:
            raise ValueError(
                f"Packed feature length {max_len} exceeds pad_to_length {pad_to_length}."
            )
        max_len = pad_to_length
    batch_input_ids = []
    batch_attention_mask = []
    batch_labels = []
    for feature in features:
        input_ids = list(feature["input_ids"])
        attention_mask = list(feature["attention_mask"])
        labels = list(feature["labels"])
        pad_len = max_len - len(input_ids)
        batch_input_ids.append(input_ids + [pad_token_id] * pad_len)
        batch_attention_mask.append(attention_mask + [0] * pad_len)
        batch_labels.append(labels + [-100] * pad_len)
    return {
        "input_ids": torch.tensor(batch_input_ids, dtype=torch.long),
        "attention_mask": torch.tensor(batch_attention_mask, dtype=torch.long),
        "labels": torch.tensor(batch_labels, dtype=torch.long),
    }


def _chat_text(row: dict[str, Any] | list[Any]) -> str:
    messages = row if isinstance(row, list) else row.get("messages")
    if not isinstance(messages, list):
        return ""
    parts = []
    for message in messages:
        if isinstance(message, dict):
            parts.append(
                f"<|{message.get('role', 'user')}|>\n{message.get('content', '')}"
            )
    parts.append("<|end|>")
    return "\n".join(parts)


if __name__ == "__main__":
    main(sys.argv[1:])
