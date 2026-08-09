# RL/SFT Progress — 2026-08-09 (checkpoint after ~8h)

Pipeline: teacher rejection sampling (deepseek-v4-flash) → tool-call traces → SFT gemma-4-E2B.
Status of each stage + the key evaluation finding.

## 1. Rejection sampling — COMPLETE ✅

- **275 validated traces** (`runs/gemma_bench/rl/sft_traces_final.jsonl`), quotas met exactly:
  {0-hop: 50, 1-hop: 50, 2-hop: 50, 3-hop: 75, 5-hop: 50}.
- Each trace = teacher reasoning (`message.reasoning`) + validated typed tool call
  (exact strings/ints, 1e-3 relative floats). **56/275 compacted** via `compact_trace`
  (long reasoning → compressed, original answer spliced server-side).
- Published as HF `MRiabov/cadqa-rl-2000` config **`sft_traces_v1`** (275 rows).
- Data sources: v3_curriculum (1,445 rows) = 100×0-hop (rc10) + **342 new 1-hop** + **357 new
  2-hop** (materialized on a throwaway RTX 2080 Ti, $0.06/h) + 291×3-hop + 338×5-hop.
- Spend: **$0** (deepseek-v4-flash currently $0/M on OpenRouter; balance $160).

## 2. SFT gemma-4-E2B — COMPLETE ✅

- Box: instance 47200188 (RTX 4080S 32 GB), canonical E2B env (trl 1.9.2 | transformers
  5.14.1 | torch 2.12.1 | unsloth 2026.8.9).
- `sft_train.py`: FastVisionModel + 16-bit LoRA r32, seq 16384, 4 epochs, LR 3e-4, 276 steps.
- Result: `SFT_DONE /root/cadqa-sft-final` — train_loss **0.1398**, mean_token_accuracy **86.9%**,
  entropy 0.413, 3.6M tokens, ~31 min.
- Adapter saved (LoRA weights only; base model not merged).

## 3. Evaluation — INCONCLUSIVE / POOR (key finding) ⚠️

Held-out eval (rows not in the 275 SFT traces, v3_curriculum):

| Eval | rows | acc | tool_valid |
|---|---|---|---|
| cap 1024 tokens | 24 | 4.2% | 12.5% |
| cap 2048 tokens | 12 | 16.7% | 16.7% |

**Why it's bad — observed in raw completions:** the SFT model **rambles in reasoning
exactly like the base model** (the RL-era failure mode): 2048-token completions are pure
reasoning with **no `submit_*` tool call emitted** by the end. So:
- tool_valid ≈ 17% (only ~1/6 rows emit a parseable call within the cap).
- The SFT learned the trace *content* (train token-acc 86.9%) but not the **short-form
  output discipline** — the teacher's traces were ≤4k, yet the model regenerates longer.
- Baselines to beat: base model rc10 (0-hop) 30%, release10k (2-5 hop) 14%.

**Interpretation:** the SFT run did not produce a model that reliably answers in tool-call
form within a bounded budget. The pipeline is correct; the failure is the model's
over-generation (same root cause as the earlier GRPO collapse — the model needs either a
higher generation budget at eval (4096) or a format-discipline fix).

## 4. Next steps (options)

1. **Re-eval with 4096 cap** on ~12 rows (slow, ~1-2h) to see if calls land after longer
   reasoning — establishes whether it's purely a budget problem.
2. **Format-discipline SFT**: include the answer contract in the SFT prompt (the traces
   omitted the "end with a tool call" instruction the teacher got) + trim traces to
   short-reasoning examples (use only the compacted traces for training).
3. **RL on top** (GRPO with tool-call reward) once SFT produces the calls at all — the
   original goal.

## 5. Box/artifacts state

- Instance 47200188 (4080S) still running (~14h uptime, ~$0.227/h ≈ $3.1 so far) — stop it
  unless work resumes immediately. Adapter at `/root/cadqa-sft-final` on the box.
- Local: `runs/gemma_bench/rl/` — tool_calls.py, teacher.py, rejection_sample.py,
  sft_train.py, eval_bench.py, sft_traces_final.jsonl (275), sampling_log.jsonl (1340).
- HF: `MRiabov/cadqa-rl-2000` — v2_curriculum (1445), v3_curriculum (1445), sft_traces_v1 (275).
- git: docs/rl_checkpoint_2026-08-08.md committed; this progress doc to be committed.
