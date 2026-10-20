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
  This is the path for batched evaluation and RL rollouts. The current `liquid-finetune` lock pins
  v0.22.0, so 0.22-vs-0.23 is **unverified** until the smoke test in Q2; SFT/HF eval are unaffected.
- **CPU / on-device / local:** **llama.cpp** + GGUF (`llama-server -hf LiquidAI/LFM2.5-…-GGUF`,
  OpenAI-compatible); also Ollama and LM Studio. (The LEAP Edge SDK is deprecated — build on
  llama.cpp.)
- **Direct Python / analysis:** **Transformers**.
- **Formats:** GGUF (`Q4_0`, `Q4_K_M`, `Q5_K_M`, `Q6_K`, `Q8_0`, `BF16`, `F16`), ONNX, MLX
  (Apple Silicon).
- **Speculative decoding (optional, serving-only).** LFM2.5 has no built-in MTP head; Liquid's DSpark
  draft (`LiquidAI/LFM2.5-{1.2B-Instruct,2.6B,8B-A1B}-DSpark`) is a separate ~300M checkpoint that runs for
  LFM2.5 on **SGLang** (PR #31041) or **llama.cpp**. vLLM has a `dspark` method but only for
  Qwen3/Qwen3-Omni, Gemma4, K3, and DeepSeek-V4 drafters — not the LFM drafter. Speculation is lossless and cannot change accuracy, so it is
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

**Hosted-reference deploy sanity (base model).** Separately from TA-C1, check that our deploy stack
actually reproduces the public base model: compare the locally served base (`vLLM`/`llama.cpp`) with
OpenRouter's hosted `liquid/lfm-2.5-2.6b:free` on a small **easy math** set — for example, 32 GSM8K
items or a pinned basic-arithmetic slice — in `no_tools` mode, greedy decoding, with the identical
system prompt. Do not use CAD-QA rows: this base model's CAD-QA accuracy is near chance, so CAD-QA has
no discriminative power for a deploy check. The point is a **collapse check**: after serving, the model
must still produce sane answers, not near-zero accuracy, empty output, or degenerate repetition. Report
exact-match accuracy and the invalid/empty-output rate for both runtimes plus per-row agreement. Accept
when local accuracy is within **5 percentage points** of the hosted reference and the local run shows no
collapse (near-zero accuracy, mass invalid output, or a template/parser failure). Exact token agreement
is diagnostic only: the hosted provider may use a different runtime or quantization. Record the row
IDs, dataset revision, endpoint, model slug, provider, and request settings in the run manifest. A
failure indicts the deploy stack, not the checkpoint.

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
  the DSpark draft is adopted (FT-D22 Q4). The `liquid-finetune` pin is still `vllm==0.22.0` while the
  official LFM2.5 support starts at ≥0.23. **Unverified, not proven broken:** 0.22 may load LFM2.5
  (same `Lfm2ForCausalLM` family), so smoke-test async eval/GRPO on the pin before adding a separate
  ≥0.23 environment.
- **Q3.** *(2026-10-20)* **The hosted-reference check is the deploy-stack sanity test.** Compare the
  locally served base with OpenRouter `liquid/lfm-2.5-2.6b:free` on a 32-row easy math set (for example,
  GSM8K or a pinned basic-arithmetic slice) in `no_tools` mode, greedy; accept when local exact-match
  accuracy is within 5 percentage points of the hosted reference and the local run shows no collapse
  (near-zero accuracy, mass invalid/empty output, or a template/parser failure). CAD-QA rows are
  excluded because the base model is near chance there, which would only measure noise. Token agreement
  is diagnostic. This is a base-deploy check, not adapter parity (TA-C1 still covers vLLM vs
  Transformers) and not a thesis number; it is local-only because it makes a network call to an external
  provider.
