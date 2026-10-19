# Liquid Finetune — evaluation, async eval, and rollouts (2026)

**Status:** external study note (the `liquid-finetune` README), 2026-10-09. Records what the stack
provides for our evaluation and serving loops.

## Citation

Liquid AI, `Liquid4All/liquid-finetune` README (GitHub, fetched 2026-10-09).
`github.com/Liquid4All/liquid-finetune#evaluation`. `[vendor]`.

## Why it matters

It retires a hand-rolled trainer **and** a hand-rolled evaluator, and it reframes the
GPU-utilization problem: evaluation can run **without blocking training**.

## Evaluation

- An `evals:` section in a training config runs benchmarks every `eval_steps`; results log to wandb at
  `benchmark/{name}/score`. Metrics: `short_answer`, `grounding_iou`, `mcq_gen`, `logprob_zero_shot`,
  plus **custom metrics** (the Evaluation Guide, `src/liquid_finetune/evaluation/README.md`).
- Benchmark data uses the **same HF `messages` schema** as training data.
- **Standalone eval:** `liquid-finetune eval job_configs/eval_standalone_example.yaml --output results.json`
  (config uses `model_name`/`checkpoint`, `evals:`, an optional `backend:`).

## Async eval — the GPU-stall fix

- `async_eval` runs benchmarks **without pausing training**, using vLLM. Modes: `sync` (HF
  transformers, blocks), `sidecar` (vLLM, no pause, scheduled per cycle), `reserved` (vLLM, dedicated
  GPUs, single machine). Sidecar falls back to an HF LLM model for logprob scoring; failures are isolated.
- **Memory caveat:** `sidecar` shares the training GPU. A second 2.6B copy plus KV cache at 8k will not
  fit beside LoRA training on a 24 GB prototype; on A100 40 GB it may fit but competes for bandwidth and
  slows training. Use `sync` on 24 GB or `reserved` on a second GPU/B300 for reported runs.
- This is how a rented GPU is kept busy during evaluation (FT-D21).

## GRPO rollouts (vLLM)

- `DEFAULT_GRPO` / `DEFAULT_VLM_GRPO` set `use_vllm: true`; `vllm_mode: colocate` (vLLM inside each
  training worker) or `server` (`trl vllm-serve`; reserve `server_gpus` / `judge_gpus`). Server mode is
  single machine. Rewards are Python callables (`rewards:`), or an LLM judge (`rewards.judge`).
- One vLLM engine serves rollouts and, via async eval, evaluation — aligns with FT-D21.

## Other

- Backends: local CUDA (Ray Train), Modal, SLURM, KubeRay.
- GGUF eval: `job_configs/eval_gguf_example.yaml` (llama.cpp). QAT profiles target vLLM FP8.
- **Version note (checked 2026-10-19):** the CUDA lock still pins `vllm==0.22.0`, while the LFM2.5
  recipes require vLLM ≥0.23.0 for native `Lfm2ForCausalLM` serving. SFT/HF eval do not need vLLM; use a
  separate ≥0.23 environment for async eval/GRPO until upstream bumps the pin.

## Related

- `../../train-and-eval/fine-tuning/training.md` (stack and serving)
- `../../train-and-eval/evaluation/plan.md` (harness + scorer)
- `2026-benchcad.md` (transfer target)
