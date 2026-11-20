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
dependency order, not importance: an entry can start once its prerequisite
lands, and the tests run alongside the milestone they cover.

There are 27 open entries: 18 P0 technical, 8 P1 product, and 1 P1 technical. No
P0 product decision remains open, and P2 is empty.

## P0

### Product (P0)

None. The last P0 product decision, `MC-39`, is closed below.

### Technical (P0)

Work order:

1. `MC-35` — the relation payload; a P0 relation clue cannot be checked without
   it.
2. `MC-16` — the scope filter; it decides what `03a` allocate task quotas may
   plan and `05` validate and export release may accept.
3. `MC-37` — the definition fields; a definition cannot carry the new decisions
   without them.
4. `MC-47` — the scalar target candidate set; a P0 target category has no
   candidates without it.
5. `MC-09` — identity and provenance; a definition cannot be persisted or
   reproduced without them.
6. `MC-14` — the failure record; every pipeline stage that rejects writes to it.
7. `MC-46` — the capability census artifact; `03c` resolve deficits cannot route
   a capability deficit without it.
8. `MC-40` — the deficit classes; `03c` resolve deficits cannot route a deficit
   without them.
9. `MC-44` — feasibility derivation; it produces the support tables `MC-13`
   checks against.
10. `MC-25` — the prompt template file; `04` render prompt and choices has
    nothing to render from without it.
11. `MC-11` — the rendering inputs; a prompt cannot be reproduced from the
    declared input without them.
12. `MC-12` — the release projection; the release columns have no writer without
    it.
13. `MC-13` — the coverage and balance checks; the first release gate.
14. `MC-15` — multiple-choice fairness; the choice gate.
15. `MC-38` — the release fields and fifth support file; the consumer contract.
16. `MC-26` — the manifest and dataset card fields; the release ships both.
17. `MC-41` — the construction test contract; it locks the invariants the other
    entries introduce.
18. `MC-42` — the golden record; the first end-to-end comparison.

#### MC-35 — Relation payload schema

The relation payload schema is not specified: the evidence fields per relation,
and the tolerance field for the relations that carry one. The measured-versus-
derived split is written in `graph-content.md` section 4.3, but the payload that
carries it is not, so a P0 parallel or perpendicular clue cannot be checked
reproducibly.

**Recommendation:** add `tolerance` and `evidence` to the relation payload in
`graph-persistence.md`, reusing the `Tolerance` and `EvidenceRef` payloads
already defined for measurements: a derived relation records the rule and its
references, a measured one records the kernel call. Exclude both fields from
`relation_id`, as `measurement_id` already excludes value, unit, tolerance, and
evidence.

#### MC-16 — Implementation-scope filter

The implementation-scope filter is not machine-readable: a P0/P1/P2 mark per
quota dimension value, consumed by `03a` allocate task quotas when planning and
by `05` validate and export release when validating. The marks exist in the
requirements as prose only, so later-scope values can enter the first release.

**Recommendation:** derive one scope table from the requirement marks and filter
at plan time; `05` validate and export release then asserts that no later-scope
value appears, which is a cheaper check than filtering.

#### MC-37 — Definition fields for the new decisions

The `TaskDefinition` fields required by the recorded decisions are absent:
`state_scope` and `clue_form_profile` are not fields, `answer_parameter` is not
a field, and `answer_evidence` does not define the `answer_equivalent_set` or
membership-probe payload. The field table predates `DS-32`, `DS-34`, and
`DS-38`, and `validity` is still a prose field with no typed check-result
payload.

**Recommendation:** add `state_scope`, `clue_form_profile`, and
`answer_parameter` as definition fields; add typed `answer_equivalent_set` and
membership-probe payloads to `answer_evidence`, with the set holding entity ids
and their answers so answer uniqueness can be rechecked from the definition
alone; and give `validity` a typed check-result payload. `answer_parameter` is
the point, direction, or category a parameterized answer declares.

#### MC-09 — Definition identity and provenance

Definition reproducibility is not specified: the canonical serialization and
hash inputs for `task_id`, `definition_sha256`, and the release `answer_sha256`,
plus the provenance a definition must carry — runtime extraction hash, graph
hash, plan version, constructor version, and seed. Without it, duplicate
identity and reproduction are both undefined. Render seed and template version
are rendering provenance in `04` render prompt and choices, not the construction
definition (`DS-35`). It absorbs `MC-10`.

**Recommendation:** serialize one canonical JSON per definition, hash that
serialization, and put the construction provenance block inside it, so a hash
mismatch names the changed input. Record rendering provenance separately in the
`04` render prompt and choices output.

#### MC-14 — Failure record schema

The `failures.parquet` schema is not specified: columns, identity, dedupe,
order, merge from parallel writers, and aggregation. R-19 is not enforceable,
and parallel failure records cannot be combined safely.

**Recommendation:** one row per rejection with pipeline stage, input identity,
reason code, detail, and `task_id` when a task exists; dedupe on the tuple of
pipeline stage, input identity, `task_id`, and reason; sort by pipeline stage
then identity.

#### MC-40 — Deficit classes

Deficit classes are missing for a missing capability and a missing point probe.
`03c` resolve deficits has a "reserve or new capability needed" row that sends a
missing capability to `ProgramRequest`, but it has no named `capability_deficit`
reason and no census lookup, so `DS-33` is not enforceable. A missing probe is
also unnamed: a state with no surviving probe supports no membership task, and
the current table would treat it as a pool-capability problem and request more
programs even when only one state is affected.

A pair that is not emitted is not a deficit class. `graph-content.md` says a pair
that is not emitted is not a candidate, and a state above `max_state_entities` is
rejected at graph construction, so neither reaches `03c` resolve deficits. An
underfilled pair-relation quota target is handled like any other underfilled
target: the census decides whether it is a `capability_deficit` or a
plan/capacity conflict. There is no separate pair class.

**Recommendation:** add `capability_deficit` (no active program has the
capability → query the census, then `ProgramRequest`) and `probe_deficit` (no
surviving probe in the state → drop membership from that state; escalate to
`capability_deficit` only when no state in the pool has a probe). Record the
pair emission rule as a graph-construction rule and handle an underfilled pair target
through `capability_deficit` or the existing plan/capacity classes, not a new
pair class.

#### MC-44 — Feasibility derivation

Feasibility derivation is not computable: `task-step-support.md` defines support
existentially ("there exists a feasible derivation of exactly s steps") and says
the tables are derived from `03b` construct task definitions, but it gives no
reachability rule over the clue grammar. Four support tables ship today and a
fifth is planned (`MC-38`); none has a computable derivation, so their rows are
assertions rather than computed facts.

**Recommendation:** define feasibility as an existential over the clue grammar,
not over a concrete graph: a value is supported at step count `s` when a
symbolic construction can produce a valid definition of exactly `s` steps using
only that value's allowed clue forms and the structural rules in `03b` construct
task definitions (`selected` needs an earlier clue, `cross_state` is P2,
property has no operand form, answer-format compatibility). Implement it as the
same cover search as construction, with the graph replaced by the grammar's full
fact set and the validity rules unchanged, and derive all five tables from that
one search.

#### MC-46 — Capability census artifact

The program capability census has a contract in
`algorithm/program-capability-census.md`, but no artifact or I/O contract. The
census is emitted by `02c` build CAD graph and consumed by `03a` allocate task
quotas, `03b` construct task definitions, and `03c` resolve deficits, yet
`io-contracts.md` lists only `CadGraph` as the `02` execute CadQuery and build
graph output, `artifacts.md` has no census row, and the module README and `03b`
construct task definitions input lists omit it even though the `03a` allocate
task quotas doc names it. `DS-33` makes the census the deficit path's capability
index, so `03` task generation cannot route a `capability_deficit` without it.

**Recommendation:** add `ProgramCapabilityCensus` to the `02` execute CadQuery
and build graph output in `io-contracts.md`, add an artifact row in
`artifacts.md` with writer `02c` build CAD graph, readers `03a` allocate task
quotas/`03b` construct task definitions/`03c` resolve deficits, identity (graph
hash plus census schema version), and format, and add it to the `03a` allocate
task quotas/`03b` construct task definitions input lists. Decide whether it is a
fourth graph table or a sidecar artifact; the current "versioned with the graph
artifact" wording does not say which.

#### MC-47 — Scalar target candidate set

`task-structure.md` makes `Scalar value` a P0 task target category: "a
measurement or count with no entity chosen as the answer."
`algorithm/construction.md` defines `possible_answers` as "all entities of the
target category in the state scope", which has no meaning for a scalar target,
and `03b` construct task definitions binds a target to "exactly one entity or
scalar value" without saying how a scalar candidate set is enumerated or
narrowed. A P0 target category therefore cannot be constructed.

**Recommendation:** define the scalar candidate set as the measurement instances
in the state scope (subject entity or state, measurement type, and value),
define how a clue narrows that set, and define target binding and answer
evidence for a scalar target. If the product does not want scalar targets in P0,
remove the category from the P0 scope instead of leaving it unconstructible.

#### MC-25 — Prompt template file

The root `prompts.yaml` file and its schema are absent. `04` render prompt and
choices reads it, but the file does not exist, so the convention is
documentation without an artifact.

**Recommendation:** add the file with template id, typed placeholders, and
dataset and evaluation namespaces; `04` render prompt and choices rejects a
missing, extra, or untyped placeholder.

#### MC-11 — Rendering inputs

The `04` render prompt and choices input contract omits program text, render
seed, and template version. `04` render prompt and choices depends on them, but
`io-contracts.md` names only `TaskDefinition`, so rendering cannot reproduce a
prompt from the declared input alone. `TaskDefinition` carries `program_id` and
`program_sha256`, not the program text.

**Recommendation:** add the program text (or a `NormalizedProgram` reference),
the render seed, and the prompt template version to the `04` render prompt and
choices row of `io-contracts.md`; `04` render prompt and choices already owns
the rendering contract for `prompts.yaml`.

#### MC-12 — Release projection

The `TaskDefinition` to release-table projection is unowned:
`answer_schema_version`, `answer_sha256`, `prompt_sha256`, `evidence_json`,
`clue_types`, tolerance, and scoring have no writer. `04` render prompt and
choices emits release rows and `05` validate and export release checks them, but
neither owns the field mapping.

**Recommendation:** assign the projection to `04` render prompt and choices,
which already emits release rows, and let `05` validate and export release check
the result; keep the field mapping in the release contract so it is written
once. `answer_schema_version` and `answer_sha256` are release-only fields, so
`04` render prompt and choices must compute them; `evidence_json` and
`clue_types` are projections of definition fields.

#### MC-13 — Release coverage and balance checks

Release coverage and balance checks are missing: step mix, warmup, program
floor, target category, answer meaning, answer format, and clue type, plus the
5–25% answer-format range, the 1–10% answer-meaning range, and the 1% and 25%
caps. The P1 clue operand form balance target is `MC-45`. `05` validate and
export release currently checks only that released values appear in the support
tables, so the first release can pass without meeting R-7–R-10.

**Recommendation:** add one check per requirement R-7–R-10 for the first
release, and R-11–R-12 when their P1 scope ships; each check names the
requirement it enforces, so a missing check is visible as a missing row. Enforce
the clue operand form balance check when `MC-45` sets its target.

#### MC-15 — Multiple-choice fairness checks

P0 multiple-choice fairness checks are missing: the correct choice is present,
choices are distinct in the answer space, unit, frame, and precision match,
descriptions do not leak the answer, and labels are deterministic. A choice pool
of five entries can still be invalid. It absorbs `MC-24`.

**Recommendation:** write one check list in `03b` construct task definitions
when a task is built, and reuse it in `05` validate and export release when the
release is checked; pool size is necessary but not sufficient. Define the typed
`choice_pool` entry (candidate, distinguishing facts, and P2 error mode) at the
same time.

#### MC-38 — Release fields and the fifth support file

The release table omits `clue_form_profile`, and `clue-form-by-step.json` is
absent from the support files. `DS-38` requires the field, and `DS-31` and
`DS-37` require the fifth support table; the release contract still lists four
support files. `answer_equivalent_set` belongs inside `evidence_json` under
`DS-32`, not in a new release column.

**Recommendation:** add `clue_form_profile` to the release table and
`clue-form-by-step.json` to `support/`; extend the `05` validate and export
release copy list and the manifest hash record so all five are versioned
together. Update the "four derived files" wording in `artifacts.md` and
`task-step-support.md`, and add the support tables to the `05` validate and
export release input contract.

#### MC-26 — Release manifest and dataset card

The release manifest and dataset card have a writer (`05` validate and export
release) and the release contract lists the manifest fields, but several
contents are still unspecified: the `release_id` derivation, the
`generator_version` value, the upstream dataset version value, the
external-manifest linkage field, and the dataset-card outline, including the
answer conventions the card must state. Evaluation material is owned by `MC-28`.
`io-contracts.md` also names only `ReleaseTable` as the `05` validate and export
release input, although `05` validate and export release reads the external
dataset manifest and the support tables.

**Recommendation:** keep `05` validate and export release as the owner; add the
missing fields to release contract section 7 and a dataset-card outline; define
`release_id` and `generator_version`; add the external dataset manifest and the
support tables to the `05` validate and export release input model.

#### MC-41 — Construction test contract

The test contract for the construction invariants is missing: pair-emission
completeness, `is_inside` reproducibility from a probe, clear-case margin
rejection, and redundant-clue rejection. The invariants are written, but
`pipeline/testing/README.md` is a stub and nothing verifies them, so a
regression is invisible.

**Recommendation:** one test per invariant, plus a property test that every
accepted definition passes the validity list, plus one end-to-end test on the
golden record (after `MC-42` fixes its format).

#### MC-42 — Golden record format

The golden-record file format is not defined for the box-with-hole task.
`algorithm/construction.md` points at
`plans/nov-19/03b-task-construction-design.md` as the first golden record, but
that is a plan document, not a fixed data file. The first end-to-end test needs
a fixed record to compare against, and an untyped record drifts silently.

**Recommendation:** one versioned JSON file per golden task holding the program,
the expected canonical clue sequence, and the expected answer with its evidence;
the test compares the constructed definition field by field.

## P1

### Product (P1)

Work order:

1. `MC-22` — geometry-required for 1-step tasks; it changes what the first
   release counts.
2. `MC-20` — duplicate normalized text; it can put the same `task_id` in two
   splits.
3. `MC-17` — reserve lifecycle; it decides whether the fast loop can promote.
4. `MC-18` — program-floor backfill; it keeps the program floor after execution
   failures.
5. `MC-23` — stop budgets; the deficit loop has no terminating condition without
   them.
6. `MC-45` — operand-form balance target; it needs the first release
   distribution.
7. `MC-27` — transfer overlap and the external benchmark.
8. `MC-28` — review and evaluation material.

#### MC-22 — Geometry-required for 1-step tasks

The geometry-required rule for 1-step no-clue tasks is wrong, and the 95%
aggregate check is missing. The current definition requires a task clue to
depend on the built shape, so every 1-step task with no clue is marked false
even when the answer needs geometry — including every 1-step membership task.

**Recommendation:** define `geometry_required` as "the answer cannot be computed
from the program text alone", which covers the answer step; a 1-step membership
task then counts as geometry-required and the 95% check applies to all tasks.
Restate R-4 the same way, or the check measures a different property from the
requirement.

#### MC-20 — Duplicate normalized text across collections

Duplicate normalized text across collections is unresolved. `01d` normalize
programs gives identical normalized bytes one `program_id` and says later stages
must not treat the records as distinct, but `01b` select program pool keeps both
rows with different families and no pipeline stage enforces the rule. `task_id`
is keyed on `program_sha256`, so the release can hold two rows with the same
`task_id` and different splits.

**Recommendation:** keep both selection rows for collection accounting, but
graph and construct once per `program_id` and use the survivor's family, which
is the rule `01b` select program pool already applies within a collection. State
which stage enforces it (`03a` allocate task quotas at graph selection or `03b`
construct task definitions at construction).

#### MC-17 — Reserve program lifecycle

The active and reserve lifecycle is unresolved: whether reserve programs get
graphs, and whether the fast loop may use them. `01c` fetch program pool loads
reserve rows, `03a` allocate task quotas says to keep reserve families for `03c`
resolve deficits, and `03c` resolve deficits says the fast loop uses only graphs
already in the pool. If reserve is fetched but not graphed, the fast loop cannot
use it; if it is graphed, the fast loop is no longer free.

**Recommendation:** fetch reserve without graphing; promotion becomes a `03a`
allocate task quotas decision that emits a graph request, which is a slow-loop
cost. The fast loop stays limited to active graphs. If the owner wants reserve
available to the fast loop, graph reserve eagerly and account for the cost
instead.

#### MC-18 — Program floor backfill

Program-floor backfill after execution failures is undefined, including the
post-execution path when the 1,000-program floor is missed. `01c` fetch program
pool checks the floor before execution; execution failures can still drop the
usable count below 1,000. It absorbs `MC-19`. A 10k-task release can currently
ship with fewer than 1,000 usable programs.

**Recommendation:** one backfill loop triggered by the usable-program count:
promote reserve, graph it, replan; record the count in the deficit ledger so the
trigger is data, not a manual check.

#### MC-23 — Stop and expansion budgets

Numeric retry, expansion, and stop budgets are missing. `03c` resolve deficits
names an expansion budget but gives no number, so the stop rule is not
computable; a deficit can loop until it is noticed, and the cost of a slow loop
is unbounded. The `AcceptedMiss` record also has no fields.

**Recommendation:** state the stop rule as a deficit threshold after a fixed
number of expansion rounds, with a hard cap on pool growth; the numbers belong
in the task quota plan. Define the `AcceptedMiss` payload (quota target,
remaining count, reason, owner, plan version) so an accepted miss is data.

#### MC-45 — Clue operand form balance target

`DS-37` defers balance over clue operand form to P1, but no artifact carries the
target: the balance table in `task-structure.md` section 6 has no row for it,
and the plan-level target table names no share. P1 can therefore ship without a
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
for R-16 are undefined. Q1 asks how the P1 same-CAD-model check works, but PRD
Q7 already resolves P0 (normalized program text) and P1 (AST-normalized hash
plus a shape check), so Q1 is stale. Transfer overlap has no input artifact.

**Recommendation:** retire Q1 in favour of PRD Q7's definition and pin the
external benchmark to one released revision recorded in the manifest. R-16 is
P1, so the first release only needs the P0 exact-text check that `05` validate
and export release already performs.

#### MC-28 — Review and evaluation material

Human review and evaluation-material ownership is unassigned. R-17 and section
11 name artifacts with no pipeline stage and no writer, so the release can ship
without them. R-17 is P0, and evaluation material is a P0 deliverable.

**Recommendation:** `05` validate and export release owns a review artifact and
a review gate before export; review does not change a definition, so a failed
review rejects the row and records the reason. `05` validate and export release
also owns the evaluation material: a prompt-only view plus the scoring
instructions derived from the answer columns.

### Technical (P1)

Work order:

1. `MC-29` — run-level execution contract; retries and cache hits are promised
   without it.

#### MC-29 — Run-level execution contract

Run-level execution contracts are missing: the run manifest artifact, completion
markers, cache lookup, atomic writes, and resume semantics. The run-level graph
tolerance policy content is specified in `graph-persistence.md`, but the run
manifest that hosts it is not an artifact in `artifacts.md`. Retries and cache
hits are promised without the surrounding contract.

**Recommendation:** put the run contract in `artifacts.md`: one run manifest
with the tolerance policy and its hash, one completion marker per artifact,
write to a temporary path then rename, and a cache key of input hash plus every
version that affects the output. State the resume rule: skip an artifact only
when its completion marker and identity match.

## Closed or merged in the 2026-11-20 pass

- `MC-31` — the slow loop in `03c` resolve deficits includes `01d` normalize
  programs; the flow line in `00` end to end was the defect and is fixed.
- `MC-43` — the named-endpoint derivation, the pair rows, and the state-size
  rejection are written in `graph-construction.md`.
- `MC-08` — the resolver table is written in `03b` construct task definitions,
  with the angle, position, material-change, and topology-change conventions.
  The dataset card now has to state them for consumers.
- `MC-39` — clue operand form is coverage-only in P0, with one clue occurrence
  per supported form per step count and no share; `03a` allocate task quotas now
  says so.
- `MC-36` — the state entity limit is a scope constant measured once per
  implementation scope, and the rule is written in `graph-content.md` section
  4.1. The first number is produced when the P0 pool is selected, which is plan
  work rather than a missing contract.
- `MC-32` — the external manifest has no link field; the repo-wide link check
  passes.
- `MC-34` — the implementation README now lists the test contract folder and the
  streamlined folder.
- `MC-19` — merged into `MC-18`; both named the same backfill path.
- `MC-24` — merged into `MC-15`; both named multiple-choice fairness.
- `MC-10` — merged into `MC-09`; identity and provenance are one reproducibility
  contract.
