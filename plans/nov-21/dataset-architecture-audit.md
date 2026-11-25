# Dataset architecture audit — 2026-11-21
<!-- dont-say: allow-file: point-in-time audit; findings are quoted and not rewritten -->

**Status:** audit, 2026-11-21. Snapshot: commit `76e56c5` (`docs: flatten the
implementation tree and name stages after the docs`).

This is a review document, not a source of truth. The owner documents remain
authoritative. The findings are pinned to the snapshot above; if `main` has
moved, re-check the owner files named in each finding before acting on it.

**Scope:** `docs/dataset/` — the requirements, the implementation docs, the
feature-wide decisions, and the root `balance.yaml`, `release-checks.yaml`, and
`prompts.yaml`. The audit is read-only; no owner document was changed.

**Question:** before implementation starts, are there major architectural
omissions?

**Verdict:** yes, but fewer than the document count suggests. The CAD and task
core is implementation-ready: the stage DAG, typed artifact ownership, the
AST/runtime extraction split, graph persistence, quota math, canonical
serialization, and failure reconciliation are coherent.

The gaps are at the seams of the pipeline: how a run is executed and resumed,
what the evaluation deliverable is, how the blocking review gate gets geometry,
one answer-equality rule shared by construction and scoring, what `release_id`
actually pins, and what guarantees the test split has. The claim in
`docs/dataset/implementation/missing-contracts.md` that “no P0 technical
contract remains open” is not supported by the documents below.

## Method

- Read the top-level dataset README, the requirements, `decisions.md`, every
  pipeline stage doc, the extraction contracts, the test contracts, the
  streamlined “what” docs, and the three root config files.
- Cross-checked claims across owner documents: dangling references, requirements
  without a check or owner, artifacts without an owner, identity inputs that do
  not cover the content they name, and statements that contradict each other.
- Checked the existing plans and in-flight worktrees so the audit does not
  re-report work already in progress.
- Did not run code and did not change an owner document.

## Findings

| ID | Finding | Severity |
|---|---|---|
| `DA-1` | Run-level execution contract is absent, but three docs depend on it | **Blocks P0** |
| `DA-2` | “Evaluation material” (P0 deliverable) has no owner, artifact, or grader | **Blocks P0** |
| `DA-3` | Review gate has no data path and no renderer | **Blocks P0** |
| `DA-4` | Answer equality (`same_answer`) and scoring tolerance disagree | **Blocks P0 correctness** |
| `DA-5` | `release_id` does not pin the extraction environment or graph content | **Blocks P0 reproducibility** |
| `DA-6` | The test split has no coverage/balance requirement or reporting | **Blocks P0 benchmark claim** |
| `DA-7` | R-5 “no trivial shortcuts” has no check or construction rule | **Blocks P0 requirement** |
| `DA-8` | Cumulative releases do not preserve split assignment | **P1, design now** |
| `DA-9` | No license/attribution for redistributed CADEvolve program text | **Publication blocker** |

The rest of this document gives the evidence, why each finding bites, and a
recommendation. `DA-10` onward are real but second-order; they will cause rework
rather than block the first release on their own.

---

## `DA-1` — Run-level execution contract

**Evidence:** `implementation/missing-contracts.md:78-90` (`MC-29`);
`pipeline/05-validate-and-export-release.md:147`;
`pipeline/extraction/graph-persistence.md:148,255,444`;
`failure-record.md:98`; `artifacts.md` has no run-manifest row.

**What the docs say.** `05` ends with: “Atomic directory replacement is the
run-level execution contract, not this document.” There is no such document.
`extraction/graph-persistence.md` says the run manifest carries the tolerance
policy and its hash, and its validation section requires them to be present.
`failure-record.md` says the run manifest records the versions for the whole run.
`artifacts.md` has no run-manifest row, no cache index, no completion markers,
and no resume rule.

**Why it is a gap.** The pipeline is expensive: 1,500 active programs, 30 seconds
and 2 GiB per execution, and graphs measured at 20,135,608 relations for 1,000
programs. Without a run contract, an interrupted run recomputes hours of work,
and the retries and cache hits promised by `00-end-to-end.md` and `02b` are
unimplementable. `MC-29` records the gap as P1, but every P0 run depends on it.

**Recommendation.** Write a run contract, either as
`implementation/run-contract.md` or as a section of `artifacts.md`, covering:

- a run manifest artifact: run id, generator version, all component versions,
  tolerance policy and hash, and the hashes of the policy files;
- one completion marker per artifact, written through a temporary path and a
  rename;
- a cache index keyed by the input hash plus every version that affects the
  output; the `02b` cache key is already defined and can be reused;
- a resume rule: skip an artifact only when its completion marker and identity
  match;
- the CLI entry point, stage selection, parallelism, exit codes, and run
  directory layout;
- partial-run cleanup.

Add the run manifest to `artifacts.md`. `graph-persistence.md` and
`failure-record.md` already treat it as real.

## `DA-2` — Evaluation material and the grader

**Evidence:** `requirements/PRD.md:366`;
`requirements/release-dataset-contract.md:43-45,189-190`;
`prompt-templates.md:20-22`; `file-trees.md` has no evaluation package.

**What the docs say.** The PRD makes “Evaluation material: the correct answers
and instructions needed to score an LLM model” a P0 deliverable. The release
contract says the evaluation harness passes only `prompt` to the model and the
scorer reads the answer columns. `prompts.yaml` has an `evaluation` namespace
“read by the evaluation harness”. No document owns the evaluation artifact, the
harness, the prompt-only view, or the scoring algorithm.

**Why it is a gap.** R-1 and R-2 promise objectively checkable answers, but the
shipped scoring predicate is undefined. `scoring_rule` is an enum
(`exact`, `numeric_tolerance`, `structured_exact`) and `tolerance_json` has one
example, but no contract states how a coordinate or bounding box is compared,
how a multiple-choice label is resolved to its candidate, or how a structured
object is checked. The evaluation namespace has no consumer in the repository.

**Recommendation.** Add an evaluation contract covering:

- the prompt-only view: a file or a column projection, with an owner;
- answer parsing per `answer_format`, including the MC label-to-candidate step;
- tolerance and rounding semantics, including relative versus absolute and
  per-component comparison for coordinates and bounding boxes;
- the grader implementation and its CLI;
- the evaluation prompt, system prompt, and submission instruction;
- where the evaluation material is shipped and who owns it.

If the harness is deliberately external, define the interface it must implement
and state that the repository does not ship it. The deliverable cannot remain
unowned.

## `DA-3` — Review gate has no data path

**Evidence:** `pipeline/05-validate-and-export-release.md:13-21,104-122`;
`requirements/release-dataset-contract.md:82-106`;
`pipeline/03-task-generation/03b-construct-task-definitions.md:92`.

**What the docs say.** `05` must write a visual review pack: one render of the
final solid state with the target and every clue-bound entity highlighted in a
distinct colour and labelled with its clue number. Its declared inputs are
`ReleaseTable`, `RenderConfig`, the support tables, `balance.yaml`,
`release-checks.yaml`, the external manifest, the benchmark set, and the failure
partitions. It does not receive the CAD graph, the `TaskDefinition`s, or the
normalized program text. `05` is Go; the renderer is a Python/CadQuery job.

`05` also says: “The pack reads the bound entity ids from the release row's
evidence, so the release projection must carry them.” The release table has
`answer_evidence_json`, `clue_types`, and `clue_operand_form_profile`, but not
the per-clue `TaskClue.result` that holds the bound entities. `03b` records those
bound entities on each clue, and `04` does not copy them.

**Why it is a gap.** The review gate is P0 and blocks export, but as specified it
cannot run: `05` cannot see the geometry or the per-clue bindings. A renderer
that re-executes CadQuery is outside the `05` input contract and outside its
language boundary.

**Recommendation.** Choose one:

- add a `clue_evidence_json` or `bound_entities` column to the release table and
  the `04` projection, then have `05` call a Python review-pack worker; or
- make the review pack a separate stage or tool that reads `TaskDefinition` and
  the graph artifacts, and have `05` consume its result.

Define the sample size and selection rule. “A sample covering every clue type,
answer meaning, and answer format” is not a sampling contract.

The `docs-visual-review-pack` work landed on 2026-11-21 as
`scripts/manual-verification/README.md`; its renderer deferral is superseded by
`devtools/review-pack.md`. It reduces the renderer question; it does not close
the data path.

## `DA-4` — Answer equality versus scoring tolerance

**Evidence:** `pipeline/03-task-generation/03b-construct-task-definitions.md:315-335`;
`decisions.md` `DS-REQ-15` and `DS-REQ-14`;
`requirements/release-dataset-contract.md:170-172`;
`requirements/terminology.md:54`.

**What the docs say.** `03b` defines `same_answer` as canonical equality at the
answer's stated precision. `DS-REQ-15` says it is “the comparison the release grader
performs, so a task cannot pass build-time uniqueness and fail scoring.” The
release carries `scoring_rule` and `tolerance_json`, and `DS-REQ-14` says grading
uses half a unit in the last stated place unless the task states another
tolerance. Those are different predicates.

**Why it is a gap.** Two values can be distinct at four significant figures but
both inside the tolerance, so the grader accepts either while build-time
uniqueness treated them as distinct. Two values can be equal at four significant
figures but outside a tighter stated tolerance, so build-time uniqueness merges
them while the grader separates them. Either direction breaks the promise that a
task passing construction cannot be ambiguous at scoring.

There are also direct contradictions inside the `same_answer` table:

- material change: “same added and removed volume” versus the resolver's single
  signed volume or count;
- topology change: “same face, edge, and vertex counts, and the same changed
  set” versus the resolver's signed delta for one declared category.

**Recommendation.** Define one answer-equivalence relation, parameterised by the
answer's tolerance and precision, and use it in both `03b` uniqueness and the
grader. Rewrite the material-change and topology-change rows to match the scalar
semantics. State how multiple-choice labels and structured objects compare.

## `DA-5` — `release_id` does not pin the extraction environment

**Evidence:** `requirements/release-dataset-contract.md:248-261,269-289`;
`pipeline/extraction/graph-persistence.md:259-260`; `artifacts.md:20`;
`pipeline/02b-execute-cadquery.md:119-122`.

**What the docs say.** `release_id` is computed over `generator_version`,
`implementation_scope`, `external_dataset_manifest_sha256`,
`balance_policy_sha256`, the prompt template version and hash, and
`release_seed`. The external manifest pins the program pool and the
normalization version, not CadQuery, OCP, `extractor_version`, or
`canonicalization_version`. `generator_version` is a manually bumped constant;
the contract itself says a missed bump is a defect that the release identity
inherits.

`graph-persistence.md` says the tolerance policy is part of the graph artifact
identity, but the graph identity row in `artifacts.md` omits it, and
`release_id` does not include it.

**Why it is a gap.** Two releases can share a `release_id` while one used a
different OCP version and produced different measurements and answers. That
breaks R-18 and makes cross-release comparison unsound.

**Recommendation.** Include in `release_id`:

- the extraction environment: Python, CadQuery, OCP, `extractor_version`, and
  `canonicalization_version`;
- `tolerance_policy_version` and `tolerance_policy_sha256`;
- ideally, a graph-batch identity: `program_id` plus the graph artifact identity
  for every program.

Add a graph-artifact identity check that covers the tolerance policy and the
graph builder version, not only `graph_schema_version`.

## `DA-6` — The test split has no guarantees

**Evidence:** `release-checks.yaml` (only `scope: release` and `scope: per_step`);
`pipeline/05-validate-and-export-release/release-checks.md:109-111`;
`requirements/release-dataset-contract.md:229-231`;
`requirements/PRD.md:335-347`.

**What the docs say.** Coverage and balance checks are scoped `release` or
`per_step`. There is no `per_split` scope. The manifest records `split_counts`
and `program_family_split_counts`, but not the dimension distribution inside
each split. The step-count mix is release-level.

**Why it is a gap.** The test split is the benchmark. At 15% of 10,000 tasks
(about 1,500), it can omit a clue type or an answer meaning, or be dominated by
one answer format, while every release-level check passes. It can also contain
no five-step tasks. A benchmark result then names a step range the test set does
not actually cover.

**Recommendation.** Add per-split coverage at least, and per-split balance for
the test split or a documented tolerance. Report the test distribution in the
manifest and the dataset card. Make the plan split-aware for the benchmark
cells. If the intent is that only the release as a whole is balanced, state that
explicitly and explain why a skewed test split is acceptable; right now the
benchmark claim and the checks measure different things.

## `DA-7` — R-5 has no mechanism

**Evidence:** `requirements/PRD.md:234`; `release-checks.yaml` has no R-5 row;
`pipeline/03-task-generation/03b-construct-task-definitions.md:342-359`;
`requirements/prompt-content.md:170-183`.

**What the docs say.** R-5 is P0: “Trivial shortcuts do not win on
shape-required tasks. For a task that requires the built shape, an LLM model
cannot answer by reading variable names, literal arguments, or operation order
alone.” `release-checks.yaml` has no R-5 row. `03b` has no validity rule for shortcut
resistance. `geometry_required` is a clue-based flag, and `MC-22` already shows
that flag is wrong for one-step tasks.

**Why it is a gap.** Removing variable names from the prompt (`DS-REQ-05`) does not
stop a model from using literal arguments or operation order. The dataset cannot
claim R-5 while no construction rule or release check measures it.

**Recommendation.** Define a measurable proxy, for example: at least one clue or
the answer step depends on a measurement that is not fixed by a literal or by
operation order, or a text-only constructor must fail to produce the answer.
Record the result per task. Alternatively, re-scope R-5 to a P1 evaluation
baseline and remove it from the P0 claim.

## `DA-8` — Cumulative releases do not preserve split assignment

**Evidence:** `requirements/PRD.md:335-338`;
`pipeline/03-task-generation/03a-allocate-task-quotas.md:11-14,305-321`;
`artifacts.md` has no family-to-split registry.

**What the docs say.** The PRD says later releases are cumulative and, when a
later release includes a task from an earlier release, its split assignment is
preserved. `03a` assigns splits by deterministic greedy balancing over the
current family set. The previous plan or release is not an input. Adding P1 or
P2 families changes capacities and greedy order, so a family can move to another
split between releases. No artifact records a durable family-to-split registry.

**Why it is a gap.** A task can be in `train` in release 1 and `test` in release
2, which is exactly the contamination the cumulative rule exists to prevent.
This is a later-release problem, but the registry must exist before the first
release or the first release becomes the migration.

**Recommendation.** Add a durable `family_split_registry` artifact written by
`05` and read by `03a`. `03a` honours existing assignments and assigns only new
families. Add a check that a previously released task keeps its split.

## `DA-9` — License and attribution

**Evidence:** `requirements/release-dataset-contract.md:303-317`;
`requirements/PRD.md:356-368`; no license or attribution statement anywhere
under `docs/dataset/`.

**What the docs say.** The dataset card outline has no license or attribution
section. The release contract has no license field. The release redistributes
normalized CadQuery program text from CADEvolve, which is derived from
ABC/ShapeNet meshes.

**Why it is a gap.** This is a publication blocker, not a code blocker. The
upstream terms need to permit redistribution of the program text and of the
derived task text before a public release.

**Recommendation.** Confirm the CADEvolve and upstream mesh licenses. Add a
License/Attribution section to the dataset card and a license field to the
manifest: license id, upstream terms, required notices, and citation.

---

## Secondary findings

These are real and will cause rework, but they do not block the first release on
their own.

### `DA-10` — Answer-format quota versus task identity

`task_id` and `definition_sha256` exclude `answer_format`
(`03b-construct-task-definitions.md:426-440`), so a numeric and a
multiple-choice version of the same canonical task are duplicates. `03a`
allocates `answer_format` as an independent quota dimension
(`03a-allocate-task-quotas.md:126-148`). One canonical task cannot fill both
targets, which can create deficits and wasted expansion rounds.

**Recommendation.** Treat answer format as a presentation assignment after
canonical task selection, or include it in identity if both variants should
coexist. Adjust the quota model accordingly.

### `DA-11` — Distance pair emission

`requirements/graph-content.md:178-213` says a `selected` or `aggregated`
reference needs no pair row because the comparison is computed from per-entity
measurements. That is false for `distance`, which is kernel-measured
(`graph-content.md:258`). A distance comparison between two selected entities
has no pair row and cannot be evaluated by `03b`.

**Recommendation.** Restrict the claim to derivable relations. Either emit pair
rows for selected or aggregated distance, or mark that combination unsupported
in the support table.

### `DA-12` — Hash coverage

`definition_sha256` omits `answer_format` and `target_category`
(`03b-construct-task-definitions.md:498-505`). `answer_sha256` omits
`answer_format` (`:512-518`). `answer_set_sha256` uses `gold_answer_json`, which
is a label for multiple choice, while `distinct_answer_count` counts the
candidate (`release-dataset-contract.md:293-297` versus
`release-checks.md:61-71`).

**Recommendation.** Include `answer_format` in both hashes. Use one answer
identity for multiple choice, the candidate, in `answer_set_sha256` and in the
distinct-answer check.

### `DA-13` — Support-table contradiction and missing bootstrap

`TG-4` and `MC-48` say `03a` calls the support-table derivation. `file-trees.md`
lines 174-175 and `streamlined/README.md` lines 33-34 say `03a` reads the
tables. The fixtures and `support-table.json` do not exist yet (`MC-44`), so
`03a` cannot run.

**Recommendation.** Fix the two statements. Put the fixture and support-table
bootstrap in the first milestone, not in a later QA pass.

### `DA-14` — Program text cannot be verified from the release

The release row carries `program_sha256`, but the only copy of the program is
embedded in `prompt`, and `05` has no `NormalizedProgram` input. A renderer bug
could pair the wrong program with a definition and still pass every existing
check.

**Recommendation.** Add a `program_text_sha256` column, or a small program
table, and check in `05` that the embedded program matches the hash.

### `DA-15` — `MC-22` is a P0 product defect

`geometry_required` is defined as “at least one task clue depends on the built
shape”, so every one-step task with no clue is false. The 95% built-shape check
is enforced, and one-step tasks are exactly 5% of the release, so the first
release sits exactly at the boundary. `MC-22` records this as P1, but R-4 is P0.

**Recommendation.** Fix R-4 and `geometry_required` before the first release.
The recommended definition is “the answer cannot be computed from the program
text alone”.

### `DA-16` — Stale terminology statements

`TERM-1` says the terminology “is still a proposal”; the terminology document is
approved. The terminology table says the program capability census “is a
by-product of graph construction”; `TG-9` says it is derived, not emitted.
These are small, but code names follow the glossary, so stale text can produce a
stale name.

**Recommendation.** Fix both statements in the same change that touches the
glossary.

---

## In-flight work at the snapshot

- `.worktrees/run-contract` is at `76e56c5` with no changes yet. `DA-1` is the
  contract it should write.
- `docs-visual-review-pack` landed on 2026-11-21 (`scripts/manual-verification/`).
  It reduces the `DA-3` renderer question but does not add the missing release
  columns or the graph input.
- The other worktrees at the snapshot are unrelated to these findings.

If either branch lands before implementation starts, re-check `DA-1` and `DA-3`
against the new text.

## What is strong

- Stage boundaries and typed artifact ownership are clear. “Failure is data” is
  consistent across extraction, graph build, and task construction.
- The extraction contract separates AST facts from runtime facts, defines stable
  entity IDs, and rejects ambiguous topology instead of guessing.
- Graph persistence is concrete and measured: three typed Parquet tables,
  UUIDv5 identity, a tolerance policy, evidence fields, and performance numbers.
- The quota math is specified down to integer arithmetic, with one conditional
  share implementation shared by `03a` and `05`.
- The support-table and superseded-bound logic handles coverage floors that make
  a balance bound impossible, rather than silently dropping coverage.

## Recommended pre-implementation order

1. Write the run/cache/resume contract and add the run manifest to
   `artifacts.md` (`DA-1`).
2. Define the evaluation material and the grader (`DA-2`).
3. Give the review gate a data path and a renderer (`DA-3`).
4. Unify `same_answer` and scoring tolerance (`DA-4`).
5. Extend `release_id` to pin the extraction environment and graph identity
   (`DA-5`).
6. Add per-split coverage and balance, at least for test (`DA-6`).
7. Define R-5's measurable proxy or re-scope it (`DA-7`).
8. Add the family-to-split registry before the first release (`DA-8`).
9. Resolve license and attribution (`DA-9`).
10. Fix the secondary contradictions before coding the affected stages
    (`DA-10` to `DA-16`).

## Proposed entries for `missing-contracts.md`

If these findings are accepted, the audit backlog should gain the following
entries. The IDs continue after `MC-49`.

| Proposed ID | Entry | Priority |
|---|---|---|
| `MC-50` | Run contract: run manifest, completion markers, cache, atomic writes, resume, CLI | P0 |
| `MC-51` | Evaluation material and grader: prompt-only view, parsing, tolerance, scoring CLI | P0 |
| `MC-52` | Review pack data path: per-clue bound entities and graph input to the renderer | P0 |
| `MC-53` | One answer-equivalence relation used by construction and scoring | P0 |
| `MC-54` | `release_id` pins the extraction environment, tolerance policy, and graph identity | P0 |
| `MC-55` | Per-split coverage and balance, with the test distribution in the manifest | P0 |
| `MC-56` | R-5 shortcut-resistance rule or an explicit re-scope | P0 |
| `MC-57` | Durable family-to-split registry for cumulative releases | P1 |
| `MC-58` | License and attribution in the dataset card and manifest | Publication |
| `MC-59` | Answer-format identity and quota interaction | P1 |
| `MC-60` | Distance pair emission for selected and aggregated endpoints | P1 |
| `MC-61` | `answer_format` in the definition and answer hashes; one MC answer identity | P1 |
| `MC-62` | Support-table wording and fixture bootstrap | P1 |

`MC-29` should be promoted from P1 to P0 and closed by `MC-50` rather than kept
as a separate run-level entry.
