"""SFT gemma-4-E2B on validated CAD-QA teacher traces (tool-call style).

Reads sft_traces.jsonl (agent training trace records: prompt + reasoning-then-tool-call),
formats as single-turn chat (user: prompt, assistant: agent training trace), and SFTs with
FastVisionModel + QLoRA (4-bit NF4 base, LoRA adapters) at 16K context
(canonical E2B notebook recipe).
"""



from __future__ import annotations

import sys
import os as _os
sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))  # train_and_eval root

import os
from pathlib import Path

from datasets import Dataset
from pydantic import BaseModel, Field
from trl import SFTConfig, SFTTrainer
from unsloth import FastVisionModel

from tool_calls import HarnessMode


# trl 1.9.2 removed push_to_hub_token; unsloth's patched SFTTrainer may still
# pass it via to_dict() spread. Also force eos_token=<turn|> (gemma-4 E2B's real
# eos) on every SFTConfig construction, since the trainer rebuilds its config.
_orig_sft_config_init = SFTConfig.__init__


def _sft_config_init(self, *args, **kwargs):
    kwargs.pop("push_to_hub_token", None)
    kwargs["eos_token"] = "<turn|>"  # force: gemma-4 E2B's real eos token
    kwargs["pad_token"] = "<pad>"
    return _orig_sft_config_init(self, *args, **kwargs)


SFTConfig.__init__ = _sft_config_init

SEQ = int(os.environ.get("CADQA_SFT_SEQ", "6144"))  # 100% of 268 sequences fit (max 5822)
EPOCHS = float(os.environ.get("CADQA_SFT_EPOCHS", "4"))
LR = float(os.environ.get("CADQA_SFT_LR", "3e-4"))
OUT = os.environ.get("CADQA_SFT_OUT", "/root/cadqa-sft-final")
TRACES = os.environ.get("CADQA_SFT_TRACES", "/root/cadqa-bench/sft_texts.jsonl")
ROWS = int(os.environ.get("CADQA_SFT_ROWS", "0"))  # 0 = all


class Trace(BaseModel):
    row_id: str = Field(min_length=1)
    hop: int = Field(ge=0)
    prompt: str = Field(min_length=1)
    tool_name: str = Field(min_length=1)
    trace: str = Field(min_length=1)
    gold: str = Field(min_length=1)
    answer_format: str = Field(min_length=1)
    compacted: bool = False
    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    mode: HarnessMode = Field(default=HarnessMode.NO_TOOLS)
    text: str | None = Field(default=None)


def load_traces(path: Path) -> list[Trace]:
    traces = [Trace.model_validate_json(line) for line in path.read_text().splitlines() if line.strip()]
    if ROWS > 0:
        traces = traces[:ROWS]
    return traces


def build_dataset(traces: list[Trace]) -> Dataset:
    # pre-rendered gemma-native text (normalize_traces.py): train on plain text
    records = [{"text": t.text} for t in traces if t.text]
    if len(records) != len(traces):
        raise SystemExit(f"missing pre-rendered text: {len(traces) - len(records)} traces")
    return Dataset.from_list(records)


def main() -> None:
    traces = load_traces(Path(TRACES))
    if not traces:
        raise SystemExit(f"no traces in {TRACES}")
    print(f"traces: {len(traces)} | seq {SEQ} | epochs {EPOCHS} | lr {LR}")

    model, tokenizer = FastVisionModel.from_pretrained(
        "unsloth/gemma-4-E2B-it",
        max_seq_length=SEQ,
        load_in_4bit=True,          # QLoRA: 4-bit NF4 base, LoRA adapters on top
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype="bfloat16",
        fast_inference=False,
    )
    # gemma-4 E2B uses <turn|> as eos; unsloth's default <EOS_TOKEN> is not in vocab
    tokenizer.eos_token = "<turn|>"
    tokenizer.pad_token = tokenizer.eos_token
    model = FastVisionModel.get_peft_model(
        model,
        r=32,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_alpha=64,
        use_gradient_checkpointing="unsloth",
        random_state=3407,
    )

    ds = build_dataset(traces)
    config = SFTConfig(
        output_dir=OUT,
        per_device_train_batch_size=4,
        gradient_accumulation_steps=1,
        learning_rate=LR,
        num_train_epochs=EPOCHS,
        logging_steps=5,
        save_strategy="steps",
        save_steps=50,
        report_to="none",
        max_length=SEQ,
        packing=False,
        lr_scheduler_type="cosine",
        warmup_ratio=0.05,
        eos_token="<turn|>",
        loss_type="nll",
    )
    print("DEBUG config.eos_token =", repr(config.eos_token), flush=True)
    trainer = SFTTrainer(
        model=model,
        args=config,
        train_dataset=ds,
        processing_class=tokenizer,
    )
    trainer.train()
    model.save_pretrained(OUT)
    tokenizer.save_pretrained(OUT)
    print(f"SFT_DONE {OUT}")


if __name__ == "__main__":
    main()
