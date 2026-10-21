# Missing contracts

**Status:** ephemeral audit backlog, 2026-10-21. This is not a source of truth.
Each row names an absent contract. When the contract is written into its owner
doc, delete the row. Open questions remain in
[`open-questions.md`](open-questions.md).

## P0

| ID | Owner | Missing contract | Why it blocks |
|---|---|---|---|
| MC-03 | [`01b`](pipeline/01b-select-program-pool.md) | Precedence when collection minima, feature-tag minima, family cap, and the 1,500-program target conflict. | The selection policy can be over-constrained with no stated resolution. |
| MC-04 | [`02a`](pipeline/02a-extract-cadquery-ast.md) | Static expression tree for nested constructors such as `cq.Plane(cq.Vector(...))`; method allowlist; CadQuery selector timing. | “Typed literal values” cannot represent real C-tier programs, and graph coverage depends on the allowlist. |
| MC-06 | [`02c`](pipeline/02c-build-cad-graph.md) | Typed attributes per graph entity category and graph table scope. | The graph attribute schema and table layout are undefined. |
| MC-07 | [`03a`](pipeline/03a-plan-release.md) | Quota allocator equations for marginal cells, step mix, clue occurrences, family capacity, caps, and coverage minima; cell-to-family budget division. | The plan lists steps but no computable allocation. |
| MC-08 | [`03b`](pipeline/03b-construct-task-definitions.md) | Construction grammar: possible-answer sets, target binding order, clue constructors, answer resolvers, sampling order, and support-table derivation. | `03b` currently defines rejection, not construction. |
| MC-09 | [`03b`](pipeline/03b-construct-task-definitions.md) | Canonical serialization and hash inputs for `task_id`, `definition_sha256`, and `answer_sha256`. | Duplicate identity and reproducibility are undefined. |
| MC-10 | [`03b`](pipeline/03b-construct-task-definitions.md) | Provenance needed to reproduce a definition: execution result hash, graph artifact hash, plan version, render seed, and template version. | The definition cannot reproduce its evidence or prompt. |
| MC-11 | [`04`](pipeline/04-render-prompt-and-choices.md) | Program text, render seed, and template file in the input contract. | `04` cannot render the program or choose a template variant from `TaskDefinition` alone. |
| MC-12 | [`04`](pipeline/04-render-prompt-and-choices.md) | Mapping from `TaskDefinition` to release-table fields: `answer_schema_version`, `answer_sha256`, `prompt_sha256`, `evidence_json`, `clue_types`, tolerance, and scoring. | No pipeline stage owns the release projection. |
| MC-13 | [`05`](pipeline/05-validate-and-export-release.md) | Release coverage and balance: step mix, warmup, program floor, format/meaning/clue/target balance, 1% and 25% caps. | The first release can pass the current checks without meeting R-7–R-12. |
| MC-14 | [`05`](pipeline/05-validate-and-export-release.md) | `failures.parquet` schema: columns, identity, dedupe, order, merge from parallel writers, and aggregation. | R-19 is not enforceable and parallel failures cannot be combined safely. |
| MC-15 | [`03b`](pipeline/03b-construct-task-definitions.md), [`05`](pipeline/05-validate-and-export-release.md) | P0 multiple-choice fairness checks: correct choice present, choices unique, same answer space, unit/frame/precision, non-leaking descriptions, deterministic labels. | P0 choices can be invalid even when the choice pool has five entries. |
| MC-16 | [`03a`](pipeline/03a-plan-release.md), [`03b`](pipeline/03b-construct-task-definitions.md) | P0/P1/P2 implementation-scope filter for generation and validation. | Later-scope values can enter the first release. |

## P1

| ID | Owner | Missing contract | Why it matters |
|---|---|---|---|
| MC-17 | [`01`](pipeline/01-external-dataset-etl.md), [`01c`](pipeline/01c-fetch-program-pool.md), [`03c`](pipeline/03c-resolve-deficits.md) | Active/reserve lifecycle: whether reserve programs get graphs, and whether the fast loop can use them. | Current docs assume both, which is contradictory. |
| MC-18 | [`01c`](pipeline/01c-fetch-program-pool.md), [`02`](pipeline/02-execute-cadquery-and-build-graph.md), [`05`](pipeline/05-validate-and-export-release.md) | Program-floor backfill after execution failures. | A 10k-task release can ship with fewer than 1,000 usable programs. |
| MC-19 | [`01c`](pipeline/01c-fetch-program-pool.md) | Post-execution backfill path when the 1,000-program floor is missed. | Fetch-time “usable” is not execution-time usable. |
| MC-20 | [`01b`](pipeline/01b-select-program-pool.md), [`03b`](pipeline/03b-construct-task-definitions.md) | Family/split reconciliation for duplicate normalized text with different family IDs. | Duplicate identity can arbitrarily choose a family and split. |
| MC-21 | [`03a`](pipeline/03a-plan-release.md) | Owner and artifact for program metadata input. | `03a` needs metadata, but `artifacts.md` lists `01b` as the only reader. |
| MC-22 | [`03b`](pipeline/03b-construct-task-definitions.md) | Geometry-required rule for 1-step no-clue tasks, plus the aggregate 95% check. | The current definition marks some geometry-dependent tasks false. |
| MC-23 | [`03c`](pipeline/03c-resolve-deficits.md) | Numeric retry, expansion, and stop budgets. | The loop has no computable stop rule. |
| MC-24 | [`03b`](pipeline/03b-construct-task-definitions.md) | P0 choice fairness beyond pool size. | This overlaps MC-15; the owner split is unclear. |
| MC-25 | [`04`](pipeline/04-render-prompt-and-choices.md) | Root `prompts.yaml` file and schema. | The convention exists in docs, but the artifact does not. |
| MC-26 | [`05`](pipeline/05-validate-and-export-release.md) | Manifest, dataset-card, `release_id`, generator version, upstream version, external-manifest linkage, and evaluation material. | The release contract requires artifacts with no owner or content spec. |
| MC-27 | [`05`](pipeline/05-validate-and-export-release.md) | Reconcile Q1 with PRD Q7 and define the external benchmark input/revision for R-16. | Q1 is stale and transfer overlap has no input. |
| MC-28 | [`05`](pipeline/05-validate-and-export-release.md) | Human review and evaluation-material stage ownership. | R-17 and §11 have no pipeline stage or artifact. |
| MC-29 | [`00`](pipeline/00-end-to-end.md), [`artifacts.md`](artifacts.md) | Run manifest, completion markers, cache lookup, atomic writes, and resume semantics. | Retries and cache hits are promised but not specified. |
| MC-30 | [`02`](pipeline/02-execute-cadquery-and-build-graph.md) | Per-program dependency order `02a → 02b → 02c`; parallel across programs, not across sub-steps. | Current wording can be read as three independent parallel steps. |

## Minor

| ID | Owner | Missing contract |
|---|---|---|
| MC-31 | [`00`](pipeline/00-end-to-end.md) | Slow loop omits `01d`. |
| MC-32 | [`01e`](pipeline/01e-write-external-dataset-manifest.md) | Manifest link path points one directory too shallow. |
| MC-33 | [`03a`](pipeline/03a-plan-release.md) | “Chain depth” conflicts with the terminology rule against “depth” for reasoning. |
| MC-34 | [`README.md`](../README.md) | Does not list `open-questions.md`, `missing-contracts.md`, `testing/`, or `streamlined/`. |
