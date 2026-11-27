# Manual verification protocol

**Status:** working plan, 2026-11-21. Turns the owner verification points in
[`dataset-implementation-plan.md`](dataset-implementation-plan.md#owner-verification-points)
into repeatable passes, and names the seams those points do not cover.

## Why this exists

The tests own mechanics: schemas, hashes, ordering, counts, determinism. The
owner owns four judgements: whether the extraction checker is trustworthy,
whether a task reads as a question, whether the answer is right, and whether a
miss is acceptable. The plan names those judgements but not how to make them
cheaply or what they miss.

A manual pass is not a code audit. It is a handful of passes over the same
pipeline at three resolutions:

| Pass | Question | Resolution | When |
|---|---|---|---|
| 0. Negative control | Would a broken checker actually fail? | one deliberate mutation per checker | once per checker |
| 1. Task trace | Does one task hold together across every artifact? | one row, every pipeline stage | `P0-W2`, repeat at `P0-W4` and `P0-W6` |
| 2. Graph | Does the graph contain what the program contains? | one program, every element | `P0-W3` |
| 3. Batch | Does it hold at scale, and is anything silently missing? | 100 programs, distributions | `P0-W3`, `P0-W5`, `P0-W6` |
| 4. Consumer | Can someone use the release without the generator? | 5 rows, fresh environment | `P0-W6`, `P0-W7` |

Record every pass as a ledger row or a dated note next to the artifact. A pass
with no named artifact is not evidence.

## Pass 0 — Negative controls

A green check is evidence only if the check fails when it should. This is the
cheapest hour in the project and it is absent from the plan.

For each checker, mutate one input and confirm the failure is named, located,
and given the right disposition. Do not fix the mutation; discard it.

| Checker | Mutation | Required signal |
|---|---|---|
| Extraction-graph oracle | Delete one expected relation | Missing relation, named kind and endpoints |
| Extraction-graph oracle | Add a relation the oracle does not expect | Orphan relation, not a pass |
| Extraction-graph oracle | Change one measurement beyond tolerance | Value outside tolerance, with both values |
| Extraction-graph oracle | Weaken a descriptor so it matches two entities | Record defect: descriptor is ambiguous |
| Extraction-graph oracle | Add a row the oracle marks `excluded` | Oracle is `stale` |
| Completeness report | Delete a required `has_face` row | `missing_count` > 0, disposition `extractor_gap` |
| Completeness report | Add a relation kind absent from the table | `unclassified_count` > 0 |
| Completeness report | Remove an `evidence_ref` from a persisted row | Orphan row |
| Release checks | Tighten one bound in `balance.yaml` | `miss` on the named check, export blocked |
| Release checks | Remove one support-table row | Coverage gap at the named step count |
| Reconciliation | Delete one failure row | Count mismatch names the failing pipeline stage and both counts |
| Review gate | Change one prompt byte without a new ledger row | Key mismatch blocks export |
| Determinism | Rerun the same inputs | No unit executed, byte-identical release |
| Determinism | Change one program byte | New `program_id`, new graph identity, new release |

Pass: every mutation produces its named signal. A mutation that passes is a
checker defect, not a data condition.

## Pass 1 — One task end-to-end

Pick one release row from the sample. Follow it backwards; do not trust the
report that produced it.

| Step | Look at | Pass signal |
|---|---|---|
| 1 | `release.parquet` row | One prompt, one answer, one evidence record, one split |
| 2 | `prompt` | Reads as a question; answer-free; the program block hashes to `program_sha256` |
| 3 | `TaskDefinition` | Target, clues, answer, evidence, uniqueness rule all present and typed |
| 4 | Each clue's bound entity | Resolves to exactly one CAD graph entity in the stated state |
| 5 | `answer_evidence` | Names the measurement or rule that produces the answer; references exist |
| 6 | Graph row | The measurement value and unit match the evidence; the subject is the clue's entity |
| 7 | Runtime row | CAD topology entity identity, state, and effect agree with the graph row |
| 8 | AST row | Operation order, method, CadQuery profile, and CadQuery workplane agree with the program text |
| 9 | Render | Each highlighted entity is the one its clue names; the target is distinct |
| 10 | Manifest and card | The row is counted in the right step, split, format, and meaning |

Then answer the task yourself from the prompt, and recompute the answer with a
small plain-CadQuery script from the program text. Both must agree with
`gold_answer` inside `tolerance`.

Fail signals: a clue true of two entities; an answer needing a measurement the
graph does not hold; a highlight that names a different entity; a prompt that
contains the answer or a hidden ID; a program block that does not hash to
`program_sha256`.

This is the click-through. One row is enough to catch a broken seam; it is not
a sample of the release.

## Pass 2 — One program's extraction graph

Pick a program that has a CadQuery profile, a CadQuery workplane, a cut, a
transform, and more than one solid state. Read the program first, then the graph.

1. Write the expected operation, feature, and state list by hand.
2. Compare the graph's CAD graph entity counts and `before`/`after` chain with
   that list.
3. For the final state, write a table of faces (face surface kind, area,
   centroid) and edges (length, endpoints). Compare with a render or a ten-line
   CadQuery script.
4. Check incidence: every non-seam edge belongs to two faces; every vertex
   belongs to its edges; `adjacent_to` is the unordered shared-edge set.
5. Check provenance: `uses` and `derived_from` exist for the CadQuery profile
   and the CadQuery workplane the program actually used.
6. Check material change: the box adds a region, the cut removes one, `part_of`
   points back to the feature, and the effect delta equals final minus previous.
7. Read the completeness report: expected versus actual per kind, every
   exception, and the disposition. No exception may be unexplained.
8. Read the oracle record: the same checks, plus every descriptor resolves to
   exactly one entity, and every `excluded` entry is a real exclusion rather
   than a hidden P0 capability.
9. Diff the oracle builder's method table against `02a`'s allowlist
   (`extraction/ast/algorithm/pipeline.md`). The geometry path is deliberately
   different; the classification must not be. Make this a test.

Pass: your hand table equals the graph, the oracle equals the graph, and every
difference has a contract sentence behind it.

## Pass 3 — Batch tour

Run 100 programs, then the full active pool. Read one report, not rows. The
report needs these fields; if the generator does not print them, add them to
the run report before the pass.

| Field | Why |
|---|---|
| Programs entering and leaving each pipeline stage, plus failures by reason | R-19 reconciliation; a pipeline stage that drops 20% is invisible in a release count |
| Per-program graph entities, relations, measurements (min, median, p95, max) | Silent partial loss; compare with the pre-rebuild baseline of 677,937 entities and 20,135,608 relations per 1,000 programs |
| Per-state entity count versus `max_state_entities` | Rejections that should be corpus defects, not truncation |
| Pair rows per named endpoint | The pair emission rule is linear; a quadratic or zero count is a bug |
| Support-table cells with zero accepted graphs | The capability that disappeared |
| Construction yield per program and per family | Whether 10,000 tasks are reachable |
| Wall clock, CPU, peak memory per program; import cost share | The `EX-22` budget and the 7–9% import target |
| Review-ledger cells still `pending` | The release gate's real state |

Then spot-check, not audit:

- ten rejected programs: read the program, the reason, and the disposition. Is
  the rejection legitimate, or is it an extractor gap wearing a corpus-defect
  label?
- ten accepted graphs: does each contain the features its program text has?
- the dataset release geometry residual-defect sample: draw it uniformly from
  the pinned dataset release program pool at the stated seed and size
  `min(pool_size, 300)` at `bound_p = 0.01`; verify the draw, not only the
  result
  ([`release-dataset-contract.md`](../../docs/dataset/requirements/release-dataset-contract.md#dataset-release-geometry-residual-ledger)).

Pass: no failure reason is unexplained; every distribution sits inside a stated
range; every support-table cell has a witness or a reason; every rejected
program has a disposition.

Fail signals: one reason code owns a whole program family; median relations
drop by more than the contract change explains; a capability cell has zero
accepted graphs; a program has a graph but not the feature its text builds.

## Pass 4 — Consumer read-back

Use a fresh environment with no generator code. Read only the release directory.

1. Answer five tasks from `release.parquet` alone. Compare with `gold_answer`.
2. Run the grader on gold, a near-miss inside tolerance, a value outside
   tolerance, a wrong answer format, and a multiple-choice label.
3. Check splits: one family in one split; a test row at each claimed step.
4. Compare `manifest.json`, `dataset-card.md`, and the parquet counts.
5. Extract the program block from each prompt, hash it, and compare with
   `program_sha256` (`DA-14` says the release has no separate program table).
6. Sum `failures.parquet` and compare with the manifest and the reconciliation.
7. Read the card's answer conventions: angle, signed material change, declared
   position point, topology category, membership boundary, precision. Do they
   match the rows you read?

Pass: a consumer can use the release without the generator, and the card's
conventions match the actual answers.

## Requirement coverage

| Requirement | Manual pass | Batch pass |
|---|---|---|
| R-1 answers correct | Pass 1, independent recompute | 20-answer sample recomputed |
| R-2 exactly one answer | Pass 1, uniqueness rule | rejection counts for ambiguity |
| R-3 multiple choice fair | Pass 4, one MC row | choice-pool size and label distribution |
| R-4 95% built shape | Pass 1, answer-from-text test | `built_shape_share_floor` |
| R-5 no trivial shortcuts | P1 — read the `03b` rejection count against [`views/shortcut-resistance.md`](../../docs/dataset/requirements/views/shortcut-resistance.md) | `shortcut_resistance` rejects; the P0 release makes no claim |
| R-6 no answer leakage | Pass 1, read the prompt | answer-in-prompt check |
| R-7 answer formats | one row per format | per-step format mix |
| R-8 coverage | support table against the release | coverage checks |
| R-9 steps 1–5 | one row per step | step mix and range |
| R-10 1,000 models | — | `distinct_cad_model_count` |
| R-13 splits | one family | split isolation |
| R-14 test never trained | card and recipe | test count per step |
| R-15 warmup labeled | one warmup row | `warmup_set` |
| R-17 understandable | dataset browser | review gate |
| R-18 reproducible | Pass 0 determinism | manifest hashes |
| R-19 nothing silent | Pass 0 reconciliation, Pass 3 failures | pipeline stage reconciliation |

## Seams this worktree leaves open

These are not verification items; they are reasons a pass cannot yet pass. Fix
them in the owner documents before the corresponding pass is evidence.

| # | Seam | Evidence | Why it bites |
|---|---|---|---|
| 1 | The two-edge angle has no reference class | `graph-content.md` §4 declares the two-edge angle at P0, but no reference class names an edge and `EdgeAttributes` stores no direction (`02c` Q1) | A P0 angle kind is declared but cannot be emitted, so a task that needs one has no row |
| 2 | The extraction-graph oracle does not calibrate the P0 clue vocabulary | Both records are `final_state`, exclude CadQuery profiles, CadQuery workplanes, `uses`, `derived_from`, effects, and selectors, and carry `capabilities: []` | The extraction calibration set covers final-state topology and per-entity measurements on two boxes; provenance, pair relations, effects, and membership are uncalibrated there (the task-construction records and the prompt examples cover the task-side vocabulary) |
| 3 | The kernel-oracle capture check has no contract | The plan names it; `graph-completeness.md` now scopes it to dev-mode calibration | Production is projection-only, so this is not a release blocker; the dev-mode path still needs a tolerance rule before it is evidence |
| 4 | No negative control is scheduled | The owner table lists reviews, not mutations | Every green check is unproven until Pass 0 runs |

The dataset release absence and geometry residual review work closed on
2026-11-27: the contract is in
[`release-dataset-contract.md`](../../docs/dataset/requirements/release-dataset-contract.md#dataset-release-review-ledgers),
and `05` gates on both ledgers.

## Additions to the owner verification table

| Work item | What the owner verifies | Artifact | Time |
|---|---|---|---|
| `P0-W2` | Pass 0 on the oracle checker and the review gate | mutation log | ~30 min |
| `P0-W3` | Pass 0 on the completeness report and reconciliation | mutation log | ~30 min |
| `P0-W3` | Pass 2 on one hard program, plus the oracle builder/allowlist diff | hand table and oracle record | ~1–2 h |
| `P0-W3` | Pass 3 on the 100-program slice: the distribution report and ten failures | run report | ~1–2 h |
| `P0-W6` | Pass 0 on the release checks, Pass 4 consumer read-back | mutation log and five-row trace | ~1 h |
| `P0-W7` | Pass 3 on the full pool, Pass 4 on the release | run report and release trace | ~2 h |
| `P1-W5` | The shortcut-resistance view — reviewed 2026-11-25; re-check if the threshold or topology list changes | [`views/shortcut-resistance.md`](../../docs/dataset/requirements/views/shortcut-resistance.md) | ~30 min |

## What not to verify manually

- Schema, hashes, ordering, counts, and determinism. The tests own them.
- Every graph row. The oracle and the batch distribution own that.
- Every prompt. The review matrix samples it.
- Code style and doc lint. The repository checks own them.

The point of the protocol is to spend human time only where a test cannot
decide, and to spend it once per seam rather than once per row.
