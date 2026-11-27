# Support and capability derivations

**Parent:** [`README.md`](README.md).

## Program capability census

`03a` derives the [program capability census](../algorithm/program-capability-census.md)
from the graphs it already reads. The census is not an input and not an artifact:
it is one function, called here and in `03b` construct task definitions.

For each active program the census answers which target categories, clue
constructors, clue reduction forms, measurements, answer meanings, and point probes
the graph has. `03a` derives it once per graph batch, stores the per-program
census in `program_census` and the union per family in `family_profiles`, and
assigns quota targets from that projection. `03b` reads the program's entry
rather than deriving the census again.

A fast-loop replan does not derive the census again: the graph batch has not
changed and both `program_census` and `family_profiles` are already in the plan. A
slow-loop round derives it only for the programs the round adds. `03c` resolve
deficits reads `family_profiles` rather than the census.

## Support-table derivation

`03a` derives and writes the single task reasoning step support table; it does
not read the table as a planning input (`TG-4`). The derivation is defined in
[`../../../task-step-support.md`](../../../task-step-support.md).

- `supported_values(task_reasoning_step_count, quota_dimension)` is the
  support-table derivation's output. `03a` derives it in-process before it
  allocates quotas, writes the table, and records its schema version and hash in
  `TaskQuotaPlan`; `05` validate and export release reads the written table and
  verifies both. There is one derivation, not a scope file plus a grammar model.
  The derivation takes `implementation_scope` from the requirement marks, so a
  value above the release scope has no row.

## Producer and artifact

`03a` writes one Parquet table to
`<run>/03a-allocate-task-quotas/support/support.parquet`, one row per dimension
value and task reasoning step count, with the row schema in
[`../../../task-step-support.md`](../../../task-step-support.md#the-produced-table).

- The fixture programs are pool programs, so their graphs are part of the `02c`
  output. A fixture with no accepted graph fails `03a` and names the fixture.
  It is not marked unsupported, because a rejected program must not look like a
  grammar limit.
- The table is filtered to the run's `implementation_scope`; no row above the
  scope is written.
- `03a` writes the table and records `support_schema_version` and
  `support_table_sha256` in `TaskQuotaPlan`.
- The table is not copied into the release. It is a run input to the coverage and
  balance checks, and their rows carry `supported_cell` and `reason_code`.

## What the census cannot see

The census answers what one accepted graph offers. A capability the extraction
contract declares and no accepted graph realizes has no census entry, so it also
has no quota target and no support-table row: the constructor produces no
definition for it, the support table marks that dimension value unsupported with
`no_valid_construction`, and the per-step coverage checks read it as
`not_applicable`. The plan and the release then agree, and both are wrong.

That loss is not this derivation's to catch. `implementation_scope` comes from the
requirement marks, not from the graphs, so a value inside the scope stays in the
derivation even when the corpus never produces it. The release gate is
`extraction_capability_coverage`
([`release-checks.md`](../../05-validate-and-export-release/release-checks.md#extraction-capability-coverage)),
which compares the contract's declared capability cells with the cells the
accepted graphs realize. `no_valid_construction` does not distinguish a grammar
limit from a graph capability no fixture carries; that distinction belongs to the
capability set, not to a support-table reason code.
