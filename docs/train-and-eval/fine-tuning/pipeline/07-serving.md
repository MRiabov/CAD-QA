# 07 — serving

## Purpose

Merge the SFT adapter into LFM2.5 and serve the merged LLM model. Serving is a **separate inference
runtime**: it loads the merged weights only, never the training optimizer or updating weights (FT-D20).
Run **one serving engine per rented GPU window** and sequence train → merge → serve → evaluate rather
than co-running training and serving (FT-D21).

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

## Inputs / outputs

- **In:** a LoRA **adapter** (04).
- **Out:** a **merged LLM model**, then a GGUF artifact (llama.cpp) and/or a vLLM / SGLang-served
  endpoint.

## Requirement

The served LLM model must be numerically equivalent to the transformers LLM model it was merged from;
parity must be shown before any served number is used (FT-D10, TA-C1). Merge is a tracked step (FT-D12;
TA-D2).

## Recipe

- **Merge** the adapter into the bf16 base (cookbook / `merge_adapter.py`), then **export** to GGUF
  and/or serve natively with vLLM. Quantization is an export/serving step, not a training step.
- For batched evaluation and RL rollouts, prefer a **vLLM** endpoint; for local/edge, a **GGUF** file.

## Verification

```bash
# GPU: serve the merged LLM model and check parity against transformers
vllm serve <merged-checkpoint> --tool-call-parser lfm2
# local: llama.cpp
llama-server -m <merged>.gguf -c 4096 --port 8080
```

## Open questions

- **Q1.** Parity precision: argmax token ids, or logprobs within a tolerance (TA-C1)?
- **Q2.** Which GPU runtime for our batched rollouts — vLLM or SGLang (both documented for LFM2.5)?
