# Dataset kernel known issues

**Status:** working tracker, 2026-11-19. This is an audit record, not a
specification. It does not change a requirement or a contract.

**Scope:** the geometry-task producing kernel: `02c` CAD graph construction,
`03b` task-definition construction, and the contracts they consume (`02b`
capture, `03a` quotas, `05` release gates). `01` ETL and `04` rendering are
included only where they block the kernel.

**Companion docs:** `docs/dataset/implementation/missing-contracts.md` and
`docs/dataset/implementation/open-questions.md`. This tracker does not replace
them. It records the kernel-level failures those backlogs do not yet name, and
it gives each one a closure test. When an issue is closed, update the owning
doc and delete the row here.

## Verdict

The capture kernel (`02a`/`02b`/`02c`) is specified to an implementation-ready
level: instrumentation ABI, canonical JSON, 9-decimal hashing, entity IDs, a
closed failure taxonomy, and typed Parquet schemas.

The task-producing kernel is not. `03b` is a validity oracle with an output
schema, not a construction algorithm. `02c` does not build several primitives
that `03b` would need. The result is three distinct failure modes:

1. the engine cannot construct a valid task because the possible-answer set,
   clue application, and answer resolution are undefined;
2. the engine constructs a task whose uniqueness, units, frame, or gold answer
   is not well-defined;
3. the engine cannot reproduce what it constructed.

The dangerous mode is 2: it fails quietly and `05` can pass the result.

## Why this tracker exists

The previous graph audit already showed that graph completeness, not task text,
is the historical failure mode. From
`plans/oct-22/cq-query-scratch-experiment.md`:

| Old-graph fact | Result |
|---|---|
| Final-state faces present | 776 of 1,259 CADEvolve-C graphs (750 with an exact face count) |
| Face area present / correct where present | 462/787 (59%) / 332/462 (72%) |
| `adjacent_to` claims that are true | 765/784 (98%) |
| Real adjacencies the graph contains | 765/1,706 (45%) |
| Face-to-edge relation | missing in all 1,300 graphs |
| Face provenance (which operation created a face) | missing in all 1,300 graphs |

Those old graphs are superseded and must not be reused. The table matters
because it shows the failure mode: a graph that looks populated, passes a
schema check, and is still missing the facts tasks need. The new spec must not
repeat that with a cleaner schema.

## Severity

| Severity | Meaning |
|---|---|
| **Blocker** | The kernel cannot produce a P0 release, or it produces gold answers that are not well-defined. |
| **High** | The kernel can silently violate a P0 claim, or a quota cannot be filled for a reason the spec does not account for. |
| **Medium** | A contract is incomplete; a workaround exists but is not reproducible. |
| **Low** | A consistency or documentation defect. |

## Summary

| ID | Issue | Severity | Owner | Status |
|---|---|---|---|---|
| KI-DS-01 | `03b` has no construction grammar | Blocker | `03b` | open |
| KI-DS-02 | `02c` does not build P0 answer primitives | Blocker | `02c`, `graph-content` | open |
| KI-DS-03 | No geometry-semantics bridge for tolerance, equality, units, and frame | Blocker | `graph-persistence`, `03b`, release contract | open |
| KI-DS-04 | State capture uses `val()` and silently drops solids; invalid solids are accepted | High | `02b` | open |
| KI-DS-05 | Determinism is asserted but not gated | High | `02b`, `05` | open |
| KI-DS-06 | Quota capacity formula and expansion loop contradict | High | `03a`, `01b`, `03c` | open |
| KI-DS-07 | Dimension coupling makes the quota plan infeasible | High | `03a`, `03b` | open |
| KI-DS-08 | `geometry_required` definition and the 95% target do not close | High | `03b`, `05` | open |
| KI-DS-09 | Family derivation fallback can leak across splits | High | `01b` | open |
| KI-DS-10 | Release answer canonicalization and scoring are incomplete | Medium | `04`, `05`, release contract | open |
| KI-DS-11 | Task identity excludes the answer, allowing cross-release answer drift | Medium | `03b` | open |
| KI-DS-12 | `TaskDefinition` has no prompt-safe entity description | Medium | `03b`, `04` | open |
| KI-DS-13 | Failure accounting and run lifecycle are unowned | Medium | `05`, `00` | open |
| KI-DS-14 | No preflight corpus census or yield budget | High | `01b`, `02`, `03a` | open |

## Issues

### KI-DS-01 — `03b` has no construction grammar

- **Severity:** Blocker
- **Owner:** `03b`
- **Status:** open
- **Symptom:** `03b` defines `TaskDefinition` fields, the clue predicate
  schema, validity predicates, step accounting, canonical identity, and attempt
  budgets. It never defines the construction itself.
- **Missing:** the initial possible-answer set per target category and state
  scope; how a typed clue filters that set; how a comparison reference
  resolves; how aggregation scope and rank work; the answer resolver per
  answer meaning; the constructor and sampling order; the derivation of the
  four support tables; the tie margin used by “exactly one answer.”
- **Evidence:** `03b` lines 56–68 (target binding), 70–109 (clue schema),
  140–162 (validity), 184–204 (identity). `missing-contracts.md` MC-08 names
  the gap but calls it one contract; it is the whole constructor.
- **Why it kills the engine:** “possible-answer set” is never defined as a
  typed model or an operation, so “a clue narrows” and “exactly one answer” are
  undefined. Any implementation will invent its own semantics, and two
  implementations will not agree on what a task is.
- **Closure test:** a written construction record for one 1-step, one 2-step,
  and one 4-step task, showing the initial set, each clue’s before/after set,
  the answer resolver, the uniqueness decision, and the rejection path. A
  fixture test reproduces the same answer candidate set trace byte-for-byte.

### KI-DS-02 — `02c` does not build P0 answer primitives

- **Severity:** Blocker
- **Owner:** `02c`, `graph-content`
- **Status:** open
- **Symptom:** `graph-content.md` requires measurements and relations that
  `02c` never constructs. The graph is a capture graph, not the answerable
  graph that `graph-content.md` §6.8 claims.
- **Missing:** `distance`; `angle`; `parallel_to`; `perpendicular_to`;
  `contains`; `intersects`; `distance_to`; `region` volume, area, bounding
  box, and centroid; `cadquery_profile` area; `path_segment` length; a point
  operand for membership and point-to-entity distance.
- **Evidence:** `graph-content.md` §3.3 (P0 relations) and §4 (P0
  measurements); `graph-persistence.md` catalog lines 92–114; the construction
  lists in `graph-construction.md` lines 66–128 contain none of the spatial
  relations and only solid-state, face, edge, vertex, CadQuery selector,
  CadQuery workplane, and effect measurements. `region` is created at lines 57–64 with a sign only.
- **Why it kills the engine:** `03a` plans quotas from support tables derived
  from task rules, so it will plan distance, angle, and relation-clue tasks.
  `03b` cannot fill them because the graph has no such measurements. `05`
  reports coverage gaps. The deficit loop then spends budget expanding data
  for a missing capability. The P0 release cannot meet R-8.
- **Closure test:** a construction table with one row for every
  `measurement_type` and `relation_type` in `graph-content.md`, naming the
  kernel call, subject, object, evidence rule, and tolerance. A fixture graph
  for one program contains at least one row of every P0 type.

### KI-DS-03 — No geometry-semantics bridge for tolerance, equality, units, and frame

- **Severity:** Blocker
- **Owner:** `graph-persistence`, `03b`, release contract
- **Status:** open
- **Symptom:** three unrelated notions of “equal” govern the engine:
  9-decimal round-half-to-even for hashes and entity IDs
  (`canonicalization.md` 17–27, 57–105); a run-level `TolerancePolicy` for
  measurement and relation comparisons (`graph-persistence.md` 116–138); and
  4 significant figures with half-a-unit-in-the-last-place for gold answers
  (DS-14, release contract 126–128). No rule connects them.
- **Missing:** the definition of a tie and a near-tie; the margin used to
  reject a near-tie; how a threshold clue is evaluated when the measurement is
  within tolerance of the threshold; per-component tolerance for a 3D coordinate or
  bounding box; the default values of `TolerancePolicy` (the structure is
  defined, the values are never stated); a `scoring_rule` value for a
  structured answer with numeric tolerance; the canonical JSON rules for
  `gold_answer_json`, `tolerance_json`, and `evidence_json`.
- **Evidence:** `graph-persistence.md` 116–138; `release-dataset-contract.md`
  98 and 126–128. The old kernel used `GEOMETRY_MARGIN_EPSILON = 1e-6`
  (`dataset/query/resolver.py:24`); the new spec has no equivalent.
- **Why it kills the engine:** symmetric parts produce exact ties and are
  rejected; near-ties produce tasks that flip under rounding. A single
  absolute tolerance cannot be correct for all components of a coordinate or
  bounding box. The grader and the constructor disagree on equality.
- **Closure test:** one decision record fixes frame, unit, tolerance defaults,
  equality, tie margin, rounding, per-component tolerance, and scoring. A
  fixture test shows a clean tie is rejected, a near-tie inside the margin is
  rejected, and a value just outside the margin is accepted.

### KI-DS-04 — State capture uses `val()` and silently drops solids; invalid solids are accepted

- **Severity:** High
- **Owner:** `02b`
- **Status:** open
- **Symptom:** `runtime.md` 153–176 says for `capture = state`: “`Workplane`:
  call `val()` once; null is a `non_solid_result` failure.” In CadQuery 2.7.0,
  `Workplane.val()` returns `self.objects[0] if self.objects else
  self.plane.origin`.
- **Consequences:** a `Workplane` with multiple objects yields only the first
  solid; the rest are silently absent from the state, so volume, counts,
  bounding box, centroid, effect deltas, and every downstream answer are
  wrong. An empty `Workplane` returns a `Vector`, not null, so the documented
  `non_solid_result` branch is wrong. Separately, a state is accepted when
  `len(shape.Solids()) >= 1` and `is_valid` is recorded but never gated
  (`geometry-classification.md` 27–38), so a task can carry a gold answer
  measured from invalid geometry.
- **Why it kills the engine:** this is silent corruption in the one function
  every answer depends on. It is worse than a rejection because the release
  still builds.
- **Closure test:** capture `vals()` and define a multi-object state as a
  compound (or reject it); classify the empty case explicitly; reject or mark
  an invalid state non-release-ready. Tests cover a multi-object `Workplane`,
  an empty `Workplane`, and an invalid solid.

### KI-DS-05 — Determinism is asserted but not gated

- **Severity:** High
- **Owner:** `02b`, `05`
- **Status:** open
- **Symptom:** the spec pins Python, CadQuery, OCP, `PYTHONHASHSEED=0`, and
  the canonicalization version. It does not pin OCC parallel/thread mode,
  `clean()` behavior, or `fuse` `glue`/`tol` settings. `Workplane.combine()`
  calls `clean()` by default. There is no double-run equality check.
- **Evidence:** `runtime.md` 9–17 and 153–176; `canonicalization.md` 83–105
  (`shape_hash` depends on 9-decimal geometry).
- **Why it kills the engine:** a last-bit difference changes entity IDs, graph
  UUIDs, task IDs, and split assignment. R-18 fails silently, and cached
  artifacts become unreproducible.
- **Closure test:** pin the OCC settings and `clean`/`fuse` behavior; run the
  same program set twice and compare `runtime_extraction_result_sha256`, graph
  hashes, and the release hash; fail on mismatch.

### KI-DS-06 — Quota capacity formula and expansion loop contradict

- **Severity:** High
- **Owner:** `03a`, `01b`, `03c`
- **Status:** open
- **Symptom:** `03a` computes `per_program_task_quota = min(100,
  ceil(10_000 / usable_program_count))` and then uses it as a capacity
  ceiling: `family_task_capacity = program_count * per_program_task_quota *
  probe_success_rate` (lines 169–182). With 1,500 programs the quota is 7, so
  capacity is `10,500 * probe_rate`. At a 0.8 probe rate that is 8,400, short
  of 10,000, even though the 1% cap permits 100 tasks per program.
- **Second contradiction:** `03c`’s slow loop “extends beyond the active and
  reserve sets” (`01b` 130–145), while `01b` calls 1,500 a hard cap and says
  never to exceed it (`01b` 36–53). The engine either deadlocks on a deficit
  or violates its own cap.
- **Why it kills the engine:** the capacity formula cannot absorb construction
  failures, and the only recovery path conflicts with the selection policy.
  The engine can declare a quota short even when the corpus could supply it.
- **Closure test:** separate the capacity ceiling (the 1% cap) from the
  allocation target (the average needed); reconcile the hard cap with
  supplemental selection; add a preflight census (KI-DS-14) and a backfill
  contract.

### KI-DS-07 — Dimension coupling makes the quota plan infeasible

- **Severity:** High
- **Owner:** `03a`, `03b`
- **Status:** open
- **Symptom:** `03a` allocates task target category, clue type, answer
  meaning, and answer format independently. `03b` maps each answer meaning to
  a native format and then says multiple choice is a presentation wrapper
  valid for every answer meaning “when the definition carries enough real
  choices” (`03b` 111–138, Q4 at 247–250).
- **Contradiction 1:** membership and validity have a two-value answer space;
  P0 requires at least five unique choices in the same answer space
  (`prompt-content.md` 100–114). Five real choices cannot exist. Multiple
  choice is therefore not valid for every meaning.
- **Contradiction 2:** at step count 1, if six formats are supported, each
  format’s conditional share is about 16.7%, so multiple choice needs at
  least half of that (about 8.3%). If multiple choice comes only from identity
  tasks and identity is 5% of the release, multiple choice is 5% and violates
  the balance rule. Wrapping other meanings as multiple choice fixes one
  dimension and breaks the numeric formats. The independent allocations do
  not account for this coupling.
- **Why it kills the engine:** the plan can be arithmetically valid and
  constructively impossible. `03b` then underfills a target that the planner
  believes is feasible.
- **Closure test:** a compatibility matrix of answer meaning by answer format
  with explicit “multiple choice not allowed” rows; a joint feasibility check
  in `03a`; a worked allocation at step count 1 that satisfies both balance
  rules.

### KI-DS-08 — `geometry_required` definition and the 95% target do not close

- **Severity:** High
- **Owner:** `03b`, `05`
- **Status:** open
- **Symptom:** `geometry_required` is defined as “at least one task clue
  depends on the built shape” (release contract 94; R-4). A 1-step measurement
  task has no task clue, so it is `false`. The 1-step bucket is 5% of the
  release. The maximum achievable is therefore exactly 95%, with no margin;
  any 2-step task with a non-geometric clue drops below the target.
- **Second gap:** `05` does not check the aggregate 95% value
  (`missing-contracts.md` MC-22 names the definition but not the release
  coverage gate).
- **Why it kills the engine:** the central “requires the built shape” claim
  can be violated without any pipeline stage failing. The task can be
  answerable from literals and still pass.
- **Closure test:** decide whether the answer step counts toward
  `geometry_required` (the answer is still a geometry measurement); add the
  aggregate check to `05`; add a fixture that fails when the share is below
  95%.

### KI-DS-09 — Family derivation fallback can leak across splits

- **Severity:** High
- **Owner:** `01b`
- **Status:** open
- **Symptom:** `01b` assigns `unknown:<source_id>` when `path_family` is
  empty or the collection is unknown (lines 92–93). That makes every such
  program its own family, so near-duplicate programs from one generator can
  land in different splits. Deduplication is within a collection only (lines
  23–26), so a cross-collection duplicate can also receive a different family.
- **Why it kills the engine:** the split unit is the only thing preventing
  train/test leakage. A fallback that manufactures a unique family per
  program defeats it silently.
- **Closure test:** mark unknown-family programs non-release-ready, or map them
  all to one family; reconcile duplicate normalized text before split
  assignment; a synthetic duplicate pair must never land in two splits.

### KI-DS-10 — Release answer canonicalization and scoring are incomplete

- **Severity:** Medium
- **Owner:** `04`, `05`, release contract
- **Status:** open
- **Symptom:** `gold_answer_json`, `tolerance_json`, and `evidence_json` are
  “canonical JSON,” but the canonicalization rules live in
  `extraction/canonicalization.md` and are scoped to extraction. The release
  contract has no equivalent. `scoring_rule` offers `exact`,
  `numeric_tolerance`, and `structured_exact` (line 98); there is no
  structured numeric tolerance for a bounding box or workplane state.
  `answer_unit` is a string in the release contract but an enum in the graph.
  No document defines how an LLM model’s free-form output is parsed before
  scoring.
- **Why it kills the engine:** two implementations can hash the same answer
  differently, and a bounding box cannot be scored with the declared rules.
  The evaluation harness is a P0 deliverable with no owner
  (`missing-contracts.md` MC-26, MC-28).
- **Closure test:** a release canonicalization section; a scoring enum that
  covers structured numeric tolerance; a parse contract for each answer
  format; a fixture that scores a correct, a near-miss, and a malformed
  answer.

### KI-DS-11 — Task identity excludes the answer, allowing cross-release answer drift

- **Severity:** Medium
- **Owner:** `03b`
- **Status:** open
- **Symptom:** canonical task identity is `(program_sha256, target binding
  identity, canonical task clue sequence, answer meaning)` (lines 191–204).
  The gold answer is excluded. `definition_sha256` includes the answer, so it
  changes, but `task_id` does not. A later release can keep the same
  `task_id` with a different gold answer.
- **Why it kills the engine:** cumulative releases promise that a task’s split
  is preserved, but not that its answer is. Cached evaluation results and
  training data keyed by `task_id` can silently mix two answers.
- **Closure test:** decide whether `task_id` includes the answer, or state
  that a changed answer is a new task with a new ID. Document the rule in
  `03b` and the release contract; add a manifest check that an existing
  `task_id` has the same `answer_sha256` across releases.

### KI-DS-12 — `TaskDefinition` has no prompt-safe entity description

- **Severity:** Medium
- **Owner:** `03b`, `04`
- **Status:** open
- **Symptom:** DS-15 forbids variable names in task text and choices. The
  graph has a `label` field, but it is “a display string; not used for
  identity or binding” and is not specified as prompt-safe
  (`graph-persistence.md` 264–265). `03b`’s `choice_pool` carries
  “distinguishing graph facts,” but clue operands have no description field.
  `04` may render text and order the pool, but it must not bind a new target.
- **Why it kills the engine:** a provenance clue such as “the operation that
  cut the cylindrical hole” needs a description of the bound operation. If
  the definition carries only an operation ID and a variable name, `04` either
  renders the variable name (violating DS-15 and R-6) or invents a
  description (violating the `04` boundary).
- **Closure test:** add a prompt-safe description or a stable description
  reference to every bound entity in `TaskDefinition`; add a render test that
  no variable name or internal identifier appears in any prompt.

### KI-DS-13 — Failure accounting and run lifecycle are unowned

- **Severity:** Medium
- **Owner:** `05`, `00`
- **Status:** open
- **Symptom:** `failures.parquet` has no schema, identity, dedupe, order, or
  merge rule (`missing-contracts.md` MC-14). There is no run manifest,
  completion marker, cache lookup, atomic write, or resume semantics
  (MC-29). `05` has no coverage and balance gate (MC-13), so a release can
  pass the current checks without meeting R-7–R-12.
- **Why it kills the engine:** R-19 (“nothing disappears silently”) is
  unenforceable, and a crashed run can leave a partial release that looks
  complete. Without the coverage gate, the engine cannot tell a good release
  from a bad one.
- **Closure test:** a typed `failures.parquet` schema and an additivity test
  (selected = accepted + rejected, by reason); a run manifest with completion
  markers and atomic writes; a `05` coverage/balance gate with a fixture that
  fails on a missing value and on a cap violation.

### KI-DS-14 — No preflight corpus census or yield budget

- **Severity:** High
- **Owner:** `01b`, `02`, `03a`
- **Status:** open
- **Symptom:** the pool is selected by metadata before any AST extraction,
  execution, graph build, or task construction. There is no measured pass rate
  per stage, no measured tasks per program, and no rejection-reason census.
  The release needs 10,000 tasks and 1,000 usable programs; `01b` selects
  1,500 active programs with a 1,000-program floor.
- **Why it kills the engine:** the first time the engine learns its yield is
  after building 1,500 graphs. If AST, execution, graph, or construction yield
  is below the implicit 33% failure budget, the release cannot hit its targets,
  and the only recovery path is the cap-conflicted slow loop (KI-DS-06).
- **Closure test:** run a census on the selected pool and record, per stage,
  the accepted and rejected counts by reason; record tasks per program and
  per family; use the census to size the pool and set the attempt budgets; add
  a release gate that refuses to start a 10k release when the projected
  capacity is below the target.

## Already tracked elsewhere

This tracker does not duplicate the existing backlog. The mapping is:

| Existing item | Covered here |
|---|---|
| MC-08 construction grammar | KI-DS-01 |
| MC-09, MC-10 identity and provenance | KI-DS-01, KI-DS-05 |
| MC-11, MC-12 `04` input and release projection | KI-DS-12, KI-DS-10 |
| MC-13 release coverage and balance | KI-DS-08, KI-DS-10, KI-DS-13 |
| MC-14 `failures.parquet` | KI-DS-13 |
| MC-15, MC-24 multiple-choice fairness | KI-DS-07 |
| MC-18, MC-19 program-floor backfill | KI-DS-06, KI-DS-14 |
| MC-20 duplicate/family reconciliation | KI-DS-09 |
| MC-22 geometry-required rule | KI-DS-08 |
| MC-23 retry and stop budgets | KI-DS-06 |
| MC-26, MC-28 manifest, dataset card, evaluation material | KI-DS-10, KI-DS-13 |
| MC-29 run manifest and resume | KI-DS-13 |
| MC-35 relation fields | KI-DS-02 |

## Suggested order

**Batch A — unblock construction.** KI-DS-01, KI-DS-02, KI-DS-03. These three
decide whether a task can be constructed at all and whether its answer is
well-defined. Nothing else is testable until they are written.

**Batch B — stop silent corruption.** KI-DS-04, KI-DS-05, KI-DS-08. These are
small, local fixes with high value: they prevent wrong golds and unreproducible
runs.

**Batch C — make the plan honest.** KI-DS-06, KI-DS-07, KI-DS-09, KI-DS-14.
These decide whether the engine can hit its targets and whether the split is
real.

**Batch D — close the release contracts.** KI-DS-10, KI-DS-11, KI-DS-12,
KI-DS-13. These are needed before a consumer can score, reproduce, or audit the
release.

## What is not an issue

The following are specified well enough to implement and should not be
rewritten while the blockers are open:

- the `02a` accepted subset and method allowlist, with measured corpus counts
  (`allowlist.md` 105–115);
- the `02b` instrumentation rewrite and parent/child protocol;
- the canonical numeric, JSON, span, fingerprint, and ordering rules
  (`canonicalization.md`);
- the graph ID derivation and typed Parquet schema
  (`graph-persistence.md`);
- the closed failure taxonomy and no-partial-output rule
  (`validation.md`);
- artifact ownership and immutability (`artifacts.md`).

## Change log

- **2026-11-19:** created from the kernel audit. Fourteen open issues; three
  blockers.
