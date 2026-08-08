# CAD-QA Gemma-4-E2B In-Process Bench — [IN PROGRESS]

Date: 2026-08-08 · Status: running (fill in when complete)

## Purpose
Baseline accuracy of `google/gemma-4-E2B-it` on CAD-QA under two harnesses:
- **h1** closed-book zero-shot (no tools)
- **h3** minimal Python+CadQuery shell, agent loop (≤4 turns, 15 s exec timeout)

Two slices: legacy `cadqa_cadevolve_rc_10` (100 rows, comparable to the
Mimo 65% / DeepSeek 63% / Kimi 59% clean-100 Harbor numbers) and current
`release_10k` (100 rows, public/private).

## Hardware / cost
Vast contract 47166131 — RTX 5070 Ti 16 GB, 100 GB disk, $0.1611/hr, SK.
(unsloth FastModel 4-bit, transformers 5.5.0, torch 2.10.0+cu128, cadquery 2.8.0)

## Commands / artifacts
- runner: `runs/gemma_bench/local_run.py` (env knobs CADQA_*)
- requests: `runs/gemma_bench/requests/{rc10,release10k}_zero_shot.jsonl`
- keys: `runs/gemma_bench/slices/{rc10,release10k}/`
- outputs: `/root/cadqa-bench/out/responses_{h1,h3}_{slice}.jsonl` on the box

## Infra lessons (this session)
- Vast host 37055: HF DNS poisoned (Twitter/FB IPs) + TLS resets — fixed via
  /etc/hosts pin + HF_HUB_DISABLE_XET=1. Not auth-related.
- Vast host 28103: SSH key never injected; onstart-cmd injection also failed.
- gemma-4 processor requires content blocks `[{"type":"text",...}]` in
  apply_chat_template; `<turn|>` tokens must be stripped from decode.
- Kaggle P100 (sm_60) incompatible with torch 2.10 (sm_70+); kernel error.

## Results
(TODO fill: accuracy by harness x slice, hop counts, exec-error rate)
