# RLVE: scaling RL with adaptive verifiable environments (2025)

**Status:** external study note, not our result. Added 2026-10-08 for the environment-scaling
framing.

## Citation

'RLVE: Scaling Up Reinforcement Learning for Language Models with Adaptive Verifiable
Environments' (2025), arXiv:2511.07317. Available at: `arxiv.org/html/2511.07317v1`. (Author list
not captured at survey time.)

- Reference: `prior-art.md`, reference [31].
- Provenance: `[preprint]`.

## What it is

RLVE trains an LLM model on **verifiable environments** that (1) procedurally generate an
unbounded number of problems with configurable difficulty and (2) provide algorithmically
verifiable rewards. Each environment adapts its difficulty distribution to the evolving policy.
The authors build `RLVE-Gym`, a suite of 400 environments.

## Findings

- **Environment scaling — expanding the collection of training environments — consistently
  improves generalizable reasoning** on held-out environments.
- **More RL data within a fixed set is not enough**: a single environment already generates
  unbounded data, so data volume saturates but environment count keeps helping.
- Static data distributions give **vanishing learning signal** when problems are too easy or too
  hard for the policy; adaptive difficulty keeps the signal alive.
- Starting from a strong RLVR LLM model already trained to saturation, continuing with RLVE (400
  environments) gives **+3.37%** average across six reasoning benchmarks versus **+0.49%** for
  more of the original RLVR at **>3×** compute.
- The authors expect **environment engineering** to become as foundational as feature/data/prompt
  engineering.

## Why it matters for CAD-QA

- It is the direct evidence for the system plan's thesis: the lever is the **number and quality of
  verifiable environments**, not the SFT volume.
- The "too easy or too hard → vanishing signal" finding is the same pass-rate band the plan already
  gates on ([21][22]); RLVE adds that the fix is **adaptive/generated difficulty**, not just
  filtering.
- The CAD-QA analogue: a task generator over the frozen dataset rows (Parquet/CSV → prompt + scalar
  gold) with configurable hop/difficulty, plus the exact-match scorer, is our `RLVE-Gym`.

## Related

- `2025-scaling-environments-llm-agents.md`
- `2025-online-difficulty-filtering-rlvr.md`
- `2026-endless-terminals-warm-start.md`
