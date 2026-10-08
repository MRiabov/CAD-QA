# Owner audit — TODO

**Throwaway.** A working checklist for the project owner to chip through with the agent.
Not part of the canonical doc tree; not linted. Move or delete when done.

Legend: `[ ]` todo · `[x]` done · `(D#)` links a decision in
`plans/oct-7/restructure-docs.md`.

## A. Decisions to confirm

- [ ] A1 — Base training pipeline to adopt, after prior-art mining (D11).
- [ ] A2 — The writing method: describe logic+decisions, verify in the audit (D12).
- [ ] A3 — Whether a separate terse WHAT layer is needed (D14).
- [ ] A4 — Harness priorities: `numpy` primary; `no_tools`/`cadquery` P2 (D10).
- [ ] A5 — The ≥10k dataset tier is P2 (D6); CADEditQA is P2 (D7).
- [ ] A6 — Lint scope: port the product-launch linters + `rumdl` (D8).

## B. Readability audit (you read; flag every "what is this?")

- [x] B1 `docs/README.md`
- [ ] B2 `docs/docs-conventions.md`
- [ ] B3 `docs/glossary.md` (and the Pending additions list)
- [ ] B4 `docs/PRD.md`
- [ ] B5 `docs/development-context.md`
- [ ] B6 `docs/development-plan.md`
- [ ] B7 `docs/dataset/*` (README, requirements, decisions, pipeline 00–07)
- [ ] B8 `docs/fine-tuning/*` (README, requirements, decisions, pipeline 00–07)
- [ ] B9 `docs/evaluation/*`
- [ ] B10 Any term that needed a follow-up → report it as a defect; add to the glossary or
      the Don't-say list.

## C. Verification (Phase 0 audit) — the trust gates

- [ ] C1 Grader identity: `cad_qa/evaluation/grade.py::grade_public_private` matches golds
      on the oracle path (accuracy 1.0) on a frozen fixture.
- [ ] C2 Grader vs reward divergence: the eval grader (`tool_call_matches`) and the GRPO
      reward (`reward_cadqa`) agree on a fixture set (they currently differ in `text`
      substring and float tolerance).
- [ ] C3 `run_code` sandbox: proves no network, timeout enforced, no cadquery import; its
      own docstring says it is not a security boundary — confirm that is acceptable.
- [ ] C4 vLLM parity: greedy transformers vs vLLM outputs match on a fixed prompt set.
- [ ] C5 SFT: is the prompt masked (completion-only loss)? What exactly is supervised?
- [ ] C6 Merge step: no tracked code produces the merged model — write one or mark the gap.
- [ ] C7 GRPO starts from the base model, not the SFT adapter — confirm intended chain.
- [ ] C8 Environment: move the pins out of the gitignored `runs/`; resolve which stack
      produced the recorded results.
- [ ] C9 Dataset revisions: HF configs are names, not hashes — pin and record.
- [x] C10 `rows_loader` + tool-call tests pass (36 passed, 2026-10-07).

## D. Terminology

- [ ] D0 Owner term review in progress — see `term-audit.md` (working rename list).
- [ ] D1 Define the terms in `glossary.md` → "Proposed additions".
- [ ] D2 Legacy-term audit: sweep all docs replacing Don't-say usage with the Say term
      until the checker is green. Checker now exists (`tools/check_dont_say.py`); first run
      = 447 hits, see `dont-say-worklist.md`.

## E. Dataset

- [ ] E1 Re-derive a sample of golds by hand and confirm them.
- [ ] E2 Decide: freeze curriculum + held-out test, or regenerate ≥10k.
- [ ] E3 0-hop/1-hop synthesis gap (`synthesis.py` floors hop at 2).
- [ ] E4 `json`/`number` teacher coverage is zero — fix before training those formats.

## F. Baselines

- [ ] F1 Record the hard-slice (3+ hop) cost-effective-model numbers the ≤30% target
      actually refers to (currently unrecorded).
- [ ] F2 Decide: re-implement the pruned heuristic baselines against the current schema, or
      retire them.
- [ ] F3 Pick the canonical baseline slice (rc10 / release10k / frozen hard test).

## G. Paper and thesis

- [ ] G1 Target: course paper, thesis chapter, or external submission (sets required scope).
- [ ] G2 Verify every citation resolves.
