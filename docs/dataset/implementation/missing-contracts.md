# Missing contracts

**Status:** ephemeral audit backlog, 2026-11-20. This is not a source of truth.
Each entry names an absent contract. When the contract is written into its owner
doc, delete the entry. Open questions remain in
[`open-questions.md`](open-questions.md).

Entries are grouped by priority, and within a priority by whether closing the
entry needs a **product decision** — a policy, threshold, or scope choice — or
only a **technical decision** that engineering can settle from the decisions
already recorded. Product entries block more than they appear to, because
writing code cannot close them.

Each section opens with a work order, most unblocking first. The order is
dependency order, not importance: an entry can start once its prerequisite lands,
and the tests run alongside the milestone they cover.

There are 26 open entries: 17 P0 technical, 8 P1 product, and 1 P1 technical. No
P0 product decision remains open, and P2 is empty.

## P0

### Product (P0)

None. The last P0 product decision, `MC-39`, is closed below.

### Technical (P0)

Work order:

1. `MC-43` — the pair domain; every distance and angle task depends on it.
2. `MC-35` — the relation payload; a P0 relation clue cannot be checked without it.
3. `MC-16` — the scope filter; it decides what `03a` may plan and `05` may accept.
4. `MC-37` — the definition fields; a definition cannot carry the new decisions without them.
5. `MC-09` — identity and provenance; a definition cannot be persisted or reproduced without them.
6. `MC-14` — the failure record; every pipeline stage that rejects writes to it.
7. `MC-40` — the deficit classes; `03c` cannot route a deficit without them.
8. `MC-44` — feasibility derivation; it produces the support tables `MC-13` checks against.
9. `MC-25` — the prompt template file; `04` has nothing to render from without it.
10. `MC-11` — the rendering inputs; a prompt cannot be reproduced from the declared input without them.
11. `MC-12` — the release projection; the release columns have no writer without it.
12. `MC-13` — the coverage and balance checks; the first release gate.
13. `MC-15` — multiple-choice fairness; the choice gate.
14. `MC-38` — the release fields and fifth support file; the consumer contract.
15. `MC-26` — the manifest and dataset card fields; the release ships both.
16. `MC-41` — the construction test contract; it locks the invariants the other entries introduce.
17. `MC-42` — the golden record; the first end-to-end comparison.

#### MC-43 — Pair domain in the graph builder

The `02c` builder work for the pair domain is missing: the derived
named-endpoint list per state, `distance_to` rows for named endpoint × candidate
endpoints, and rejection above `max_state_entities`. Point probes are already
written into `02b` and `02c`. The requirement is written in `graph-content.md`
section 4.1; the builder contract does not mention it.

**Recommendation:** build the pair domain from the declared endpoint entity
categories, emit only those rows, and reject the state above the limit rather than
truncating the domain.

#### MC-35 — Relation payload schema

The relation payload schema is not specified: the evidence fields per relation,
and the tolerance field for the relations that carry one. The measured-versus-
derived split is written in `graph-content.md` section 4.3, but the payload that
carries it is not, so a P0 parallel or perpendicular clue cannot be checked
reproducibly.

**Recommendation:** add `tolerance` and `evidence` to the relation payload in
`graph-persistence.md`, with evidence as a rule plus references for a derived
relation, or a kernel call for a measured one.

#### MC-16 — Implementation-scope filter

The implementation-scope filter is not machine-readable: a P0/P1/P2 mark per
quota dimension value, consumed by `03a` at plan time and by `05` at release.
The marks exist in the requirements as prose only, so later-scope values can
enter the first release.

**Recommendation:** derive one scope table from the requirement marks and filter
at plan time; `05` then asserts that no later-scope value appears, which is a
cheaper check than filtering.

#### MC-37 — Definition fields for the new decisions

The `TaskDefinition` fields required by the recorded decisions are absent:
`state_scope`, `clue_form_profile`, `answer_equivalent_set`, the membership
probe, and `answer_parameter` — the point, direction, or category a
parameterized answer declares. The field table predates `DS-32`, `DS-34`, and
`DS-38`, so the definition cannot carry what the decisions require.

**Recommendation:** add the five fields, with `answer_equivalent_set` holding
entity ids and their answers, so answer uniqueness can be rechecked from the
definition alone.

#### MC-09 — Definition identity and provenance

Definition reproducibility is not specified: the canonical serialization and
hash inputs for `task_id`, `definition_sha256`, and `answer_sha256`, plus the
provenance a definition must carry — runtime extraction hash, graph hash, plan
version, render seed, and template version. Without it, duplicate identity and
reproduction are both undefined. It absorbs `MC-10`.

**Recommendation:** serialize one canonical JSON per definition, hash that
serialization, and put the provenance block inside it, so a hash mismatch names
the changed input.

#### MC-14 — Failure record schema

The `failures.parquet` schema is not specified: columns, identity, dedupe, order,
merge from parallel writers, and aggregation. R-19 is not enforceable, and
parallel failure records cannot be combined safely.

**Recommendation:** one row per rejection with pipeline stage, input identity,
reason code, detail, and `task_id`; dedupe on the tuple of pipeline stage, input
identity, `task_id`, and reason; sort by pipeline stage then identity.

#### MC-40 — Deficit classes

Deficit classes are missing for a missing capability, a pair outside the domain,
and a missing point probe. `03c` predates `DS-33` and `MC-36`, so each would be
classified as a construction underfill and sent to the wrong loop.

**Recommendation:** add `capability_deficit` (no active program has it →
`ProgramRequest`), `pair_domain_deficit` (the state exceeds the entity limit →
reject the state), and `probe_deficit` (no surviving probe → no membership task
from that state).

#### MC-44 — Feasibility derivation

Feasibility derivation is not defined: how a support table decides that a
dimension value is feasible at a task reasoning step count, as reachability over
the clue grammar. Five support tables ship with no derivation rule, so their rows
are assertions rather than computed facts.

**Recommendation:** define feasibility as the same cover search as construction
against a symbolic graph where every capability is present; derive all five
tables from that one search.

#### MC-25 — Prompt template file

The root `prompts.yaml` file and its schema are absent. `04` renders from it, but
the file does not exist, so the convention is documentation without an artifact.

**Recommendation:** add the file with template id, typed placeholders, and
dataset and evaluation namespaces; `04` rejects a missing, extra, or untyped
placeholder.

#### MC-11 — Rendering inputs

The `04` input contract omits program text, render seed, and template version.
`04` renders from them, but `io-contracts.md` names only `TaskDefinition`, so
rendering cannot reproduce a prompt from the declared input alone.

**Recommendation:** add the three fields to the `04` row of `io-contracts.md`;
`04` already owns the `prompts.yaml` contract.

#### MC-12 — Release projection

The `TaskDefinition` to release-table projection is unowned:
`answer_schema_version`, `answer_sha256`, `prompt_sha256`, `evidence_json`,
`clue_types`, tolerance, and scoring have no writer. `04` emits release rows and
`05` validates them, but neither owns the field mapping.

**Recommendation:** assign the projection to `04`, which already emits release
rows, and let `05` validate the result; keep the field mapping in the release
contract so it is written once.

#### MC-13 — Release coverage and balance checks

Release coverage and balance checks are missing: step mix, warmup, program floor,
target category, answer meaning, answer format, clue type, and clue operand form
balance, plus the 1% and 25% caps. `05` currently checks only that released
values appear in the support tables, so the first release can pass without
meeting R-7–R-12.

**Recommendation:** add one check per requirement R-7–R-12, each naming the
requirement it enforces, so a missing check is visible as a missing row.

#### MC-15 — Multiple-choice fairness checks

P0 multiple-choice fairness checks are missing: the correct choice is present,
choices are distinct in the answer space, unit, frame, and precision match,
descriptions do not leak the answer, and labels are deterministic. A choice pool
of five entries can still be invalid. It absorbs `MC-24`.

**Recommendation:** write one check list in `03b` at construction and reuse it
in `05` at release; pool size is necessary but not sufficient.

#### MC-38 — Release fields and the fifth support file

The release table omits `clue_form_profile` and `answer_equivalent_set`, and
`clue-form-by-step.json` is absent from the support files. `DS-32` and `DS-38`
require the fields, and the release contract lists four support files.

**Recommendation:** add the two fields and the fifth file, then extend the `05`
copy list and the manifest hash record so all five are versioned together.

#### MC-26 — Release manifest and dataset card

The release manifest and dataset card have no owner or content spec, though the
release contract requires both. The manifest needs `release_id`, generator
version, upstream version, and external-manifest linkage; the card needs its
sections and the answer conventions. Evaluation material is tracked separately
in `MC-28`.

**Recommendation:** `05` owns both; take the field list from the release
contract and record the generator version, upstream version, and external
manifest hash in `manifest.json`.

#### MC-41 — Construction test contract

The test contract for the construction invariants is missing: pair-domain
completeness, `is_inside` reproducibility from a probe, clear-case margin
rejection, and redundant-clue rejection. The invariants are written, but nothing
verifies them, so a regression is invisible.

**Recommendation:** one test per invariant, plus a property test that every
accepted definition passes the validity list, plus one end-to-end test on the
golden record.

#### MC-42 — Golden record format

The golden-record file format is not defined for the box-with-hole task. The
first end-to-end test needs a fixed record to compare against, and an untyped
record drifts silently.

**Recommendation:** one JSON file per golden task holding the program, the
expected canonical clue sequence, and the expected answer with its evidence; the
test compares the constructed definition field by field.

## P1

### Product (P1)

Work order:

1. `MC-22` — geometry-required for 1-step tasks; it changes what the first release counts.
2. `MC-20` — duplicate normalized text; it can put the same `task_id` in two splits.
3. `MC-17` — reserve lifecycle; it decides whether the fast loop can promote.
4. `MC-18` — program-floor backfill; it keeps the program floor after execution failures.
5. `MC-23` — stop budgets; the deficit loop has no terminating condition without them.
6. `MC-45` — operand-form balance target; it needs the first release distribution.
7. `MC-27` — transfer overlap and the external benchmark.
8. `MC-28` — review and evaluation material.

#### MC-22 — Geometry-required for 1-step tasks

The geometry-required rule for 1-step no-clue tasks is wrong, and the 95%
aggregate check is missing. The current definition requires a task clue to depend
on the built shape, so every 1-step task is marked false even when the answer
needs geometry — which is every membership task.

**Recommendation:** define `geometry_required` as "the answer cannot be computed
from the program text alone", which covers the answer step; a 1-step membership
task then counts as geometry-required and the 95% check applies to all tasks.

#### MC-20 — Duplicate normalized text across collections

Duplicate normalized text across collections is unresolved. `01d` gives
identical normalized bytes one `program_id`, `01b` keeps both rows with
different families, and `task_id` is keyed on `program_sha256`, so the release
can hold two rows with the same `task_id` and different splits.

**Recommendation:** keep both selection rows for collection accounting, but
graph and construct once per `program_id` and use the survivor's family, which is
the rule `01b` already applies within a collection.

#### MC-17 — Reserve program lifecycle

The active and reserve lifecycle is unresolved: whether reserve programs get
graphs, and whether the fast loop may use them. `01c` fetches reserve rows and
`03c` claims the fast loop needs no new data, which cannot both hold.

**Recommendation:** fetch reserve without graphing; promotion becomes a `03a`
decision that emits a graph request, so the fast loop can promote and the slow
loop still pays for new data.

#### MC-18 — Program floor backfill

Program-floor backfill after execution failures is undefined, including the
post-execution path when the 1,000-program floor is missed. It absorbs `MC-19`.
A 10k-task release can currently ship with fewer than 1,000 usable programs.

**Recommendation:** one backfill loop triggered by the usable-program count:
promote reserve, graph it, replan; record the count in the deficit ledger so the
trigger is data, not a manual check.

#### MC-23 — Stop and expansion budgets

Numeric retry, expansion, and stop budgets are missing. `03c` has no computable
stop rule, so a deficit can loop until it is noticed, and the cost of a slow loop
is unbounded.

**Recommendation:** state the stop rule as a deficit threshold after a fixed
number of expansion rounds, with a hard cap on pool growth; the numbers belong in
the task quota plan.

#### MC-45 — Clue operand form balance target

`DS-37` defers balance over clue operand form to P1, but no artifact carries the
target: the balance table in `task-structure.md` section 6 has no row for it, and
the plan-level target table names no share. P1 can therefore ship without a
balance check, and P0 coverage does not stand in for one: it proves presence,
not a useful mix. If the P0 diagnostic reports severe imbalance, the target is
needed for that release rather than P1.

Equal share is the current target, not a settled one. The forms differ in what
they demand: a `selected` reference resolves by pointer, a `named` reference
identifies a described entity, and an `aggregated` reference computes a
measurement over a set. A later revision may skew the share toward the
computation forms, and the share must then stay within what the program
capability census can supply, because a target above supply becomes a deficit
rather than a mix. That revision waits for measured distributions, so `DS-38`
stands unchanged: clue form is descriptive, not a difficulty axis.

**Recommendation:** keep equal share for the first release, add the row when the
P1 support grid is measured, and revisit the share after the first release
reports its operand-form distribution.

#### MC-27 — Transfer overlap and the external benchmark

Q1 is not reconciled with PRD Q7, and the external benchmark input and revision
for R-16 are undefined. Q1 is stale, and transfer overlap has no input.

**Recommendation:** retire Q1 in favour of PRD Q7's definition and pin the
external benchmark to one released revision recorded in the manifest.

#### MC-28 — Review and evaluation material

Human review and evaluation-material ownership is unassigned. R-17 and section
11 name artifacts with no pipeline stage and no writer, so the release can ship
without them.

**Recommendation:** `05` owns a review artifact and a review gate before export;
review does not change a definition, so a failed review rejects the row and
records the reason.

### Technical (P1)

Work order:

1. `MC-29` — run-level execution contract; retries and cache hits are promised without it.

#### MC-29 — Run-level execution contract

Run-level execution contracts are missing: run manifest, completion markers,
cache lookup, atomic writes, resume semantics, and the run-level graph tolerance
policy. Retries and cache hits are promised without them.

**Recommendation:** put the run contract in `artifacts.md`: one completion
marker per artifact, write to a temporary path then rename, and a cache key of
input hash plus every version that affects the output.

## Closed or merged in the 2026-11-20 pass

- `MC-31` — the slow loop in `03c` includes `01d`; the flow line in `00` was the
  defect and is fixed.
- `MC-08` — the resolver table is written in `03b`, with the angle, position,
  material-change, and topology-change conventions. The dataset card now has to
  state them for consumers.
- `MC-39` — clue operand form is coverage-only in P0, with one clue occurrence
  per supported form per step count and no share; `03a` now says so.
- `MC-36` — the state entity limit is a scope constant measured once per
  implementation scope, and the rule is written in `graph-content.md` section
  4.1. The first number is produced when the P0 pool is selected, which is plan
  work rather than a missing contract.
- `MC-32` — the external manifest has no link field; the repo-wide link check
  passes.
- `MC-34` — the implementation README now lists the test contract folder and
  the streamlined folder.
- `MC-19` — merged into `MC-18`; both named the same backfill path.
- `MC-24` — merged into `MC-15`; both named multiple-choice fairness.
- `MC-10` — merged into `MC-09`; identity and provenance are one
  reproducibility contract.
