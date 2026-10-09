# 07 — serving

## Purpose

Release the SFT **LoRA adapter** (base + adapter) and, on demand, merge/export it. Serving is a
**separate inference runtime**: it loads the merged weights or base + adapter, never the training
optimizer or updating weights (FT-D20, FT-D23). Run **one serving engine per rented GPU window** and
sequence train → serve → evaluate rather than co-running training and serving (FT-D21).

## Where the runtimes are documented

Liquid documents serving in `docs.liquid.ai/deployment/*`:

- **GPU (high throughput):** **vLLM** or **SGLang**. LFM2.5 is native to vLLM (`Lfm2ForCausalLM`) since
  v0.23.0 — no `--trust-remote-code`, nothing to patch; set the `lfm2` tool-call parser for tool use.
  This is the path for batched evaluation and RL rollouts.
- **CPU / on-device / local:** **llama.cpp** + GGUF (`llama-server -hf LiquidAI/LFM2.5-…-GGUF`,
  OpenAI-compatible); also Ollama and LM Studio. (The LEAP Edge SDK is deprecated — build on
  llama.cpp.)
- **Direct Python / analysis:** **Transformers**.
- **Formats:** GGUF (`Q4_0`, `Q4_K_M`, `Q5_K_M`, `Q6_K`, `Q8_0`, `BF16`, `F16`), ONNX, MLX
  (Apple Silicon).
- **Speculative decoding (optional, serving-only).** LFM2.5 has no built-in MTP head; Liquid's DSpark
  draft (`LiquidAI/LFM2.5-{1.2B-Instruct,2.6B,8B-A1B}-DSpark`) is a separate ~300M checkpoint served by
  **SGLang** or **llama.cpp** (not vLLM). Speculation is lossless and cannot change accuracy, so it is
  off by default; the draft targets the base LLM model, so acceptance is re-measured after SFT (FT-D22).

## Inputs / outputs

- **In:** a LoRA **adapter** (04).
- **Out:** the **adapter** (primary artifact) and, on demand, a **merged LLM model** → GGUF (llama.cpp)
  and/or a vLLM / SGLang-served endpoint.

## Requirement

The thesis number comes from **HF Transformers** (the reference runtime, FT-D23), so it needs **no
serving-parity check**. A number produced by a **non-Transformers runtime** (vLLM / SGLang) must be shown
numerically equivalent to Transformers before it is quoted (FT-D10, TA-C1). Merge is a tracked step
(FT-D12; TA-D2).

## Recipe

- **Adapter-first:** ship base + adapter; load it with PEFT/Transformers for evaluation, or serve it with
  vLLM (`--enable-lora --lora-modules cadqa=<adapter>`) with **no merge needed**.
- **Merge/export on demand:** merge into the bf16 base (`merge_and_unload`) only for a standalone
  checkpoint or a **GGUF K-quant** export (an F16 GGUF can convert from the adapter). Quantization is an
  export/serving step, not a training step.
- For batched evaluation and RL rollouts, a **vLLM** endpoint; for local/edge, a **GGUF** file.

## Verification

```bash
# reference (no parity needed): HF Transformers + adapter
uv run python train_and_eval/eval/eval_bench.py --model <adapter-or-merged> --mode numpy
# optional served path: vLLM native LFM2.5 + LoRA
vllm serve <base> --enable-lora --lora-modules cadqa=<adapter> --tool-call-parser lfm2
# local: llama.cpp (needs a merged/GGUF artifact)
llama-server -m <merged>.gguf -c 4096 --port 8080
```

## Resolved questions

- **Q1.** *(2026-10-09)* Parity applies only to a **non-Transformers runtime** (FT-D23). Criterion:
  **argmax token-id agreement** on a fixed prompt set in bf16, with a **logprob tolerance** for near-ties;
  report the disagreement rate. Quantized GGUF is out of scope (not bit-exact by design). `TA-C1`.
- **Q2.** *(2026-10-09)* **vLLM by default** (native LFM2.5; matches LEAP/TRL rollouts); **SGLang** only if
  the DSpark draft is adopted (FT-D22 Q4). Reconcile the `liquid-finetune` pin (`vllm==0.22.0`) with the
  serving need (≥0.23).
