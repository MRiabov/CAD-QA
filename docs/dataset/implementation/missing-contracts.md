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

There are 30 open entries: 2 P0 product, 18 P0 technical, 7 P1 product, and 3 P1
technical. P2 is empty.

## P0

### Product decisions

#### MC-36 — State entity limit

The `max_state_entities` limit is not finalized. The named-endpoint rule and
the no-cap policy are written in `graph-content.md`; the limit is provisional at
500.
Distance, angle, and the P0 pair relations (`distance_to`, `parallel_to`,
`perpendicular_to`) are P0 task content, so a pair the graph never enumerated
makes a P0 task unconstructible, and the failure looks like a construction
deficit rather than a graph-domain limit.

**Recommendation:** measure entity counts per solid state on the selected P0 pool
and set the limit at the smallest round number above the 99th percentile; record
the distribution next to the limit, and re-measure at each later implementation
scope — P1 adds relations and states, so entity counts rise. The limit is a
measured quantity per scope, not a constant.

#### MC-39 — Clue operand form coverage minimum

The coverage minimum for clue operand form is not stated. `DS-37` makes it a P0
coverage dimension, but the allocation equation in `03a` gives the `+1` minimum
only to target category, answer meaning, answer format, and clue type. `03a` also
says "allocate the four quota dimensions separately" while listing five, and its
plan-acceptance list omits clue operand form. Without a number, `03a` cannot
allocate the dimension at all.

**Recommendation:** extend the `+1` coverage minimum to clue operand form,
counted over clue occurrences like clue type, because operand form is a property
of a clue and not of a task. Correct the "four quota dimensions" sentence and the
plan-acceptance list in the same edit.

### Technical decisions

#### MC-43 — Pair domain in the graph builder

The `02c` builder work for the pair domain is missing: the derived
named-endpoint list per state, the pair rows for named endpoint × candidate
endpoints (the `distance_to`, `angle`, `parallel_to`, `perpendicular_to`,
`coplanar_with`, and `coaxial_with` elements), and rejection above
`max_state_entities`. Point probes are already written into `02b` and `02c`.
`graph-content.md` section 4.1 states the requirement; `graph-construction.md`
references the domain but does not define the named-endpoint derivation, the
emitted rows, or the state rejection.

**Recommendation:** build the pair domain from the declared endpoint entity
categories, emit only those rows, and reject the state above the limit rather than
truncating the domain. Record the derivation and the entity-count check in
`graph-construction.md`, not only in the requirement.

#### MC-35 — Relation payload schema

The relation payload schema is not specified: the evidence fields per relation,
and the tolerance field for the relations that carry one. The measured-versus-
derived split is written in `graph-content.md` section 4.3, but the payload that
carries it is not, so a P0 parallel or perpendicular clue cannot be checked
reproducibly.

**Recommendation:** add `tolerance` and `evidence` to the relation payload in
`graph-persistence.md`, reusing the `Tolerance` and `EvidenceRef` payloads already
defined for measurements: a derived relation records the rule and its references,
a measured one records the kernel call. Exclude both fields from `relation_id`,
as `measurement_id` already excludes value, unit, tolerance, and evidence.

#### MC-08 — Answer resolver

The answer resolver is not written: one rule per answer meaning that turns the
bound target and the answer-equivalent set into the gold answer and its
evidence. `algorithm/construction.md` calls `answer(candidate)` but never
defines it; `03b` defines validity and `same_answer` but not the resolver that
produces the answer it validates.

**Recommendation:** write a resolver table next to the answer-format table in
`03b`, one row per answer meaning, naming the kernel call or the exact derivation
and the evidence it records. Settle the two equality gaps in the same table:
membership `same_answer` lists an `on the boundary` label that the binary
membership answer cannot produce, and topology-change equality compares "the same
changed set" without defining it.

#### MC-37 — Definition fields for the new decisions

The `TaskDefinition` fields required by the recorded decisions are absent:
`state_scope` and `clue_form_profile` are not fields, and `answer_evidence` does
not define the `answer_equivalent_set` or membership-probe payload. The field
table predates `DS-32`, `DS-34`, and `DS-38`, and `validity` is still a prose
field with no typed check-result payload.

**Recommendation:** add `state_scope` and `clue_form_profile` as definition
fields; add typed `answer_equivalent_set` and membership-probe payloads to
`answer_evidence`, with the set holding entity ids and their answers so answer
uniqueness can be rechecked from the definition alone; and give `validity` a
typed check-result payload.

#### MC-09 — Definition identity and provenance

Definition reproducibility is not specified: the canonical serialization and
hash inputs for `task_id`, `definition_sha256`, and the release `answer_sha256`,
plus the provenance a definition must carry — runtime extraction hash, graph
hash, plan version, constructor version, and seed. Without it, duplicate
identity and reproduction are both undefined. Render seed and template version
are rendering provenance in `04`, not the construction definition (`DS-35`).
It absorbs `MC-10`.

**Recommendation:** serialize one canonical JSON per definition, hash that
serialization, and put the construction provenance block inside it, so a hash
mismatch names the changed input. Record rendering provenance separately in the
`04` output.

#### MC-11 — Rendering inputs

The `04` input contract omits program text, render seed, and template version.
`04` renders from them, but `io-contracts.md` names only `TaskDefinition`, so
rendering cannot reproduce a prompt from the declared input alone.
`TaskDefinition` carries `program_id` and `program_sha256`, not the program text.

**Recommendation:** add the program text (or a `NormalizedProgram` reference),
the render seed, and the prompt template version to the `04` row of
`io-contracts.md`; `04` already owns the rendering contract for `prompts.yaml`.

#### MC-12 — Release projection

The `TaskDefinition` to release-table projection is unowned:
`answer_schema_version`, `answer_sha256`, `prompt_sha256`, `evidence_json`,
`clue_types`, tolerance, and scoring have no writer. `04` emits release rows and
`05` validates them, but neither owns the field mapping.

**Recommendation:** assign the projection to `04`, which already emits release
rows, and let `05` validate the result; keep the field mapping in the release
contract so it is written once. `answer_schema_version` and `answer_sha256` are
release-only fields, so `04` must compute them; `evidence_json` and `clue_types`
are projections of definition fields.

#### MC-13 — Release coverage and balance checks

Release coverage and balance checks are missing: step mix, warmup, program floor,
target category, answer meaning, answer format, clue type, and clue operand form
balance, plus the 5–25% answer-format range, the 1–10% answer-meaning range, and
the 1% and 25% caps. `05` currently checks only that released values appear in
the support tables, so the first release can pass without meeting R-7–R-10.

**Recommendation:** add one check per requirement R-7–R-10 for the first release,
and R-11–R-12 when their P1 scope ships; each check names the requirement it
enforces, so a missing check is visible as a missing row.

#### MC-15 — Multiple-choice fairness checks

P0 multiple-choice fairness checks are missing: the correct choice is present,
choices are distinct in the answer space, unit, frame, and precision match,
descriptions do not leak the answer, and labels are deterministic. A choice pool
of five entries can still be invalid. It absorbs `MC-24`.

**Recommendation:** write one check list in `03b` at construction and reuse it
in `05` at release; pool size is necessary but not sufficient. Define the typed
`choice_pool` entry (candidate, distinguishing facts, and P2 error mode) at the
same time.

#### MC-38 — Release fields and the fifth support file

The release table omits `clue_form_profile`, and `clue-form-by-step.json` is
absent from the support files. `DS-38` requires the field, and `DS-31` and
`DS-37` require the fifth support table; the release contract still lists four
support files. `answer_equivalent_set` belongs inside `evidence_json` under
`DS-32`, not in a new release column.

**Recommendation:** add `clue_form_profile` to the release table and
`clue-form-by-step.json` to `support/`; extend the `05` copy list and the
manifest hash record so all five are versioned together. Update the "four
derived files" wording in `artifacts.md` and `task-step-support.md`, and add the
support tables to the `05` input contract.

#### MC-16 — Implementation-scope filter

The implementation-scope filter is not machine-readable: a P0/P1/P2 mark per
quota dimension value, consumed by `03a` at plan time and by `05` at release.
The marks exist in the requirements as prose only, so later-scope values can
enter the first release.

**Recommendation:** derive one scope table from the requirement marks and filter
at plan time; `05` then asserts that no later-scope value appears, which is a
cheaper check than filtering.

#### MC-14 — Failure record schema

The `failures.parquet` schema is not specified: columns, identity, dedupe, order,
merge from parallel writers, and aggregation. R-19 is not enforceable, and
parallel failure records cannot be combined safely.

**Recommendation:** one row per rejection with pipeline stage, input identity,
reason code, detail, and `task_id` when a task exists; dedupe on the tuple of
pipeline stage, input identity, `task_id`, and reason; sort by pipeline stage then
identity.

#### MC-40 — Deficit classes

Deficit classes are missing for a missing capability and a missing point probe.
`03c` has a "reserve or new capability needed" row that sends a missing
capability to `ProgramRequest`, but it has no named `capability_deficit` reason
and no census lookup, so `DS-33` is not enforceable. A missing probe is also
unnamed: a state with no surviving probe supports no membership task, and the
current table would treat it as a pool-capability problem and request more
programs even when only one state is affected.

A pair outside the domain is not a deficit class. `graph-content.md` says a pair
outside the domain is not a candidate, and a state above `max_state_entities` is
rejected at graph construction, so neither reaches `03c`. An underfilled
pair-relation quota target is handled like any other underfilled target: the
census decides whether it is a `capability_deficit` or a plan/capacity conflict.
There is no separate pair-domain class.

**Recommendation:** add `capability_deficit` (no active program has the
capability → query the census, then `ProgramRequest`) and `probe_deficit` (no
surviving probe in the state → drop membership from that state; escalate to
`capability_deficit` only when no state in the pool has a probe). Record the pair
domain as a graph-construction rule and handle an underfilled pair target through
`capability_deficit` or the existing plan/capacity classes, not a new pair-domain
class.

#### MC-41 — Construction test contract

The test contract for the construction invariants is missing: pair-domain
completeness, `is_inside` reproducibility from a probe, clear-case margin
rejection, and redundant-clue rejection. The invariants are written, but
`pipeline/testing/README.md` is a stub and nothing verifies them, so a regression
is invisible.

**Recommendation:** one test per invariant, plus a property test that every
accepted definition passes the validity list, plus one end-to-end test on the
golden record (after `MC-42` fixes its format).

#### MC-42 — Golden record format

The golden-record file format is not defined for the box-with-hole task.
`algorithm/construction.md` points at
`plans/nov-19/03b-task-construction-design.md` as the first golden record, but
that is a plan document, not a fixed data file. The first end-to-end test needs a
fixed record to compare against, and an untyped record drifts silently.

**Recommendation:** one versioned JSON file per golden task holding the program,
the expected canonical clue sequence, and the expected answer with its evidence;
the test compares the constructed definition field by field.

#### MC-44 — Feasibility derivation

Feasibility derivation is not computable: `task-step-support.md` defines support
existentially ("there exists a feasible derivation of exactly s steps") and says
the tables are derived from `03b`, but it gives no reachability rule over the
clue grammar. Four support tables ship today and a fifth is planned (`MC-38`);
none has a computable derivation, so their rows are assertions rather than
computed facts.

**Recommendation:** define feasibility as an existential over the clue grammar,
not over a concrete graph: a value is supported at step count `s` when a symbolic
construction can produce a valid definition of exactly `s` steps using only that
value's allowed clue forms and the structural rules in `03b` (`selected` needs an
earlier clue, `cross_state` is P2, property has no operand form, answer-format
compatibility). Implement it as the same cover search as construction, with the
graph replaced by the grammar's full fact set and the validity rules unchanged,
and derive all five tables from that one search.

#### MC-45 — Capability census artifact

The program capability census has a contract in
`algorithm/program-capability-census.md`, but no artifact or I/O contract. The
census is emitted by `02c` and consumed by `03a`, `03b`, and `03c`, yet
`io-contracts.md` lists only `CadGraph` as the `02` output, `artifacts.md` has no
census row, and the module README and `03b` input lists omit it even though the
`03a` doc names it. `DS-33` makes the census the deficit path's capability index,
so `03` cannot route a `capability_deficit` without it.

**Recommendation:** add `ProgramCapabilityCensus` to the `02` output in
`io-contracts.md`, add an artifact row in `artifacts.md` with writer `02c`,
readers `03a`/`03b`/`03c`, identity (graph hash plus census schema version), and
format, and add it to the `03a`/`03b` input lists. Decide whether it is a fourth
graph table or a sidecar artifact; the current "versioned with the graph
artifact" wording does not say which.

#### MC-46 — Scalar target candidate set

`task-structure.md` makes `Scalar value` a P0 task target category: "a
measurement or count with no entity chosen as the answer."
`algorithm/construction.md` defines `possible_answers` as "all entities of the
target category in the state scope", which has no meaning for a scalar target,
and `03b` binds a target to "exactly one entity or scalar value" without saying
how a scalar candidate set is enumerated or narrowed. A P0 target category
therefore cannot be constructed.

**Recommendation:** define the scalar candidate set as the measurement instances
in the state scope (subject entity or state, measurement type, and value), define
how a clue narrows that set, and define target binding and answer evidence for a
scalar target. If the product does not want scalar targets in P0, remove the
category from the P0 scope instead of leaving it unconstructible.

## P1

### Product decisions

#### MC-17 — Reserve program lifecycle

The active and reserve lifecycle is unresolved: whether reserve programs get
graphs, and whether the fast loop may use them. `01c` fetches reserve rows,
`03a` says to keep reserve families for `03c`, and `03c` says the fast loop uses
only graphs already in the pool. If reserve is fetched but not graphed, the fast
loop cannot use it; if it is graphed, the fast loop is no longer free.

**Recommendation:** fetch reserve without graphing; promotion becomes a `03a`
decision that emits a graph request, which is a slow-loop cost. The fast loop
stays limited to active graphs. If the owner wants reserve available to the fast
loop, graph reserve eagerly and account for the cost instead.

#### MC-18 — Program floor backfill

Program-floor backfill after execution failures is undefined, including the
post-execution path when the 1,000-program floor is missed. `01c` checks the
floor before execution; execution failures can still drop the usable count below
1,000. It absorbs `MC-19`. A 10k-task release can currently ship with fewer than
1,000 usable programs.

**Recommendation:** one backfill loop triggered by the usable-program count:
promote reserve, graph it, replan; record the count in the deficit ledger so the
trigger is data, not a manual check.

#### MC-20 — Duplicate normalized text across collections

Duplicate normalized text across collections is unresolved. `01d` gives
identical normalized bytes one `program_id` and says later stages must not treat
the records as distinct, but `01b` keeps both rows with different families and no
pipeline stage enforces the rule. `task_id` is keyed on `program_sha256`, so the release
can hold two rows with the same `task_id` and different splits.

**Recommendation:** keep both selection rows for collection accounting, but
graph and construct once per `program_id` and use the survivor's family, which is
the rule `01b` already applies within a collection. State which stage enforces
it (`03a` at graph selection or `03b` at construction).

#### MC-22 — Geometry-required for 1-step tasks

The geometry-required rule for 1-step no-clue tasks is wrong, and the 95%
aggregate check is missing. The current definition requires a task clue to depend
on the built shape, so every 1-step task with no clue is marked false even when
the answer needs geometry — including every 1-step membership task.

**Recommendation:** define `geometry_required` as "the answer cannot be computed
from the program text alone", which covers the answer step; a 1-step membership
task then counts as geometry-required and the 95% check applies to all tasks.
Restate R-4 the same way, or the check measures a different property from the
requirement.

#### MC-23 — Stop and expansion budgets

Numeric retry, expansion, and stop budgets are missing. `03c` names an expansion
budget but gives no number, so the stop rule is not computable; a deficit can
loop until it is noticed, and the cost of a slow loop is unbounded. The
`AcceptedMiss` record also has no fields.

**Recommendation:** state the stop rule as a deficit threshold after a fixed
number of expansion rounds, with a hard cap on pool growth; the numbers belong in
the task quota plan. Define the `AcceptedMiss` payload (quota target, remaining
count, reason, owner, plan version) so an accepted miss is data.

#### MC-27 — Transfer overlap and the external benchmark

Q1 is not reconciled with PRD Q7, and the external benchmark input and revision
for R-16 are undefined. Q1 asks how the P1 same-CAD-model check works, but PRD Q7
already resolves P0 (normalized program text) and P1 (AST-normalized hash plus a
shape check), so Q1 is stale. Transfer overlap has no input artifact.

**Recommendation:** retire Q1 in favour of PRD Q7's definition and pin the
external benchmark to one released revision recorded in the manifest. R-16 is
P1, so the first release only needs the P0 exact-text check that `05` already
performs.

#### MC-28 — Review and evaluation material

Human review and evaluation-material ownership is unassigned. R-17 and section
11 name artifacts with no pipeline stage and no writer, so the release can ship
without them. R-17 is P0, and evaluation material is a P0 deliverable.

**Recommendation:** `05` owns a review artifact and a review gate before export;
review does not change a definition, so a failed review rejects the row and
records the reason. `05` also owns the evaluation material: a prompt-only view
plus the scoring instructions derived from the answer columns.

### Technical decisions

#### MC-25 — Prompt template file

The root `prompts.yaml` file and its schema are absent. `04` renders from it, but
the file does not exist, so the convention is documentation without an artifact.

**Recommendation:** add the file with template id, typed placeholders, and
dataset and evaluation namespaces; `04` rejects a missing, extra, or untyped
placeholder.

#### MC-26 — Release manifest and dataset card

The release manifest and dataset card have a writer (`05`) and the release
contract lists the manifest fields, but several contents are still unspecified:
the `release_id` derivation, the `generator_version` value, the upstream
dataset version value, the external-manifest linkage field, and the
dataset-card outline. Evaluation material is owned by `MC-28`. `io-contracts.md` also names
only `ReleaseTable` as the `05` input, although `05` reads the external dataset
manifest and the support tables.

**Recommendation:** keep `05` as the owner; add the missing fields to release
contract section 7 and a dataset-card outline; define `release_id` and
`generator_version`; add the external dataset manifest and the support tables to
the `05` input model.

#### MC-29 — Run-level execution contract

Run-level execution contracts are missing: the run manifest artifact, completion
markers, cache lookup, atomic writes, and resume semantics. The run-level graph
tolerance policy content is specified in `graph-persistence.md`, but the run
manifest that hosts it is not an artifact in `artifacts.md`. Retries and cache
hits are promised without the surrounding contract.

**Recommendation:** put the run contract in `artifacts.md`: one run manifest with
the tolerance policy and its hash, one completion marker per artifact, write to a
temporary path then rename, and a cache key of input hash plus every version that
affects the output. State the resume rule: skip an artifact only when its
completion marker and identity match.

## Closed or merged in the 2026-11-20 pass

- `MC-31` — the slow loop in `03c` includes `01d`; the flow line in `00` was the
  defect and is fixed.
- `MC-32` — the external manifest has no link field; the repo-wide link check
  passes.
- `MC-34` — the implementation README now lists the test contract folder and
  the streamlined folder.
- `MC-19` — merged into `MC-18`; both named the same backfill path.
- `MC-24` — merged into `MC-15`; both named multiple-choice fairness.
- `MC-10` — merged into `MC-09`; identity and provenance are one
  reproducibility contract.
