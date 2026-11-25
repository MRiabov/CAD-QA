# Learning what to learn: Training-stage-specific data for SFT-then-RL in small LLM reasoning (2026)

**Status:** external study note, not our result. Added 2026-10-08 for the related-work
citations.

## Citation

He, C., Zhang, R., Wang, Z. and Li, X. (2026) 'Learning What to Learn: Stage-Specific Data Sets <!-- dont-say: allow -->
for SFT-then-RL in Small `Language Model` Reasoning', arXiv preprint arXiv:2606.04466. Available
at: `arxiv.org/abs/2606.04466`.

- Reference: `prior-art.md`, reference [8].

## What it is

A study of *what data each post-training stage should see* for small LLM models, rather than
treating SFT-then-RL as one pipeline. Two small LLM models, five reasoning benchmarks.

## Findings

- SFT is better suited to acquiring not-yet-mastered reasoning skills; RL is better suited to
  consolidating skills the LLM model can already partly access.
- Training-stage mismatch is a failure mode: hard data during RL (all-zero reward) yields no signal.
- Their fix converts all-zero-reward failures into diagnostic + repair + new reasoning data for
  the next SFT Training stage ("Critique Fine-Tuning").
- Consistently improves over representative SFT, distillation, and RL baselines.

## Why it matters for CAD-QA

Gives a concrete rule for the `0→1→2→3→5` curriculum: SFT on hops the LLM model cannot yet solve,
RL on hops it partially solves. Also explains why CAD-QA's GRPO collapsed at hop 2 if the
policy had no partial signal there, and motivates persisting rejected/all-zero rows instead of
discarding them.

## Related

- `2026-rl-squeezes-sft-expands.md`
- `2026-slm-agentic-tool-calling.md`
