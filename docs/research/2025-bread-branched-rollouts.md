# BREAD: branched rollouts from expert anchors bridge SFT and RL (2025)

**Status:** external study note, not our result. Added 2026-10-08 for the RL-failure citations.

## Citation

'BREAD: Branched Rollouts from Expert Anchors Bridge SFT & RL for Reasoning' (2025), NeurIPS 2025
poster 118358; OpenReview `forum?id=NUDaln2vCe`. Available at:
`neurips.cc/virtual/2025/loc/san-diego/poster/118358`.

- Reference: `prior-art.md`, reference [26].
- Provenance: `[peer-reviewed]`.

## What it is

A study of the fundamental limitations of the SFT-then-RL paradigm for small LLM models, using a
toy student-expert LLM model over Markov chains to isolate when the training loop fails, and a method
(branched rollouts from expert anchors) to bridge the two stages.

## Findings

- **SFT + RL can fail completely** when (1) the expert's traces are too difficult for the small
  LLM model to express, or (2) the small LLM model's initialization yields **exponentially sparse
  rewards** as task complexity grows.
- The proposed bridge — branch rollouts off expert anchors rather than starting from scratch — is
  the paper's fix.

## Why it matters for CAD-QA

- Both failure conditions are live here: CAD-QA's hard (3+ hop) teacher traces may exceed what a
  ~2.5B LLM model can imitate, and the sparse exact-match reward on hard hops may be unreachable.
- It is the formal reason the system plan inserts a **Bridge** step for hard traces [8] and a
  **pass@k gate** before RL: without them, SFT→RL is predicted to fail, not merely underperform.
- Corroborates the task-difficulty evidence ([10][11][12]): the ceiling may be the task.

## Related

- `2026-grpo-null-web-agent.md`
- `2026-learning-what-to-learn.md`
- `2026-finetuning-with-sampling.md`
