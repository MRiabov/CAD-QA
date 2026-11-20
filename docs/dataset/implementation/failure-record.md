# Failure record

**Status:** draft, 2026-11-20. Owns the row schema for a rejected program or
task.

**Parent:** [`artifacts.md`](artifacts.md).

**Requirement:** R-19 — every rejected program or task is reported with a
reason, and the counts add up.

## Role

A **failure record** is one row per distinct rejection. Each rejecting
pipeline stage writes its own partition; `05` validate and export release merges
the partitions into `failures.parquet`.

A rejection is data, not an exception across a pipeline stage boundary. A
pipeline stage that cannot process an input records the rejection and continues.

## What is a rejection

A rejection is an input a pipeline stage was asked to process and refused: a
program that fails extraction, or a task definition that fails construction or
release validation.

These are not rejections and get no row:

- a program excluded by `01b` select program pool — it is recorded as an
  exclusion in the program selection artifact;
- a valid candidate definition that does not fill a quota target — it is not an
  input to the release;
- an unmet quota target — it is a deficit in the `DeficitLedger`;
- a plan conflict or a structural infeasibility — also a deficit;
- a missing cache row — it is an integrity error, recorded in the manifest and
  backfilled.

## Writers

| Pipeline stage | Subject | Reason set owner |
|---|---|---|
| `01d` normalize programs | program | `01d` |
| `02a` extract CadQuery AST | program | [`pipeline/extraction/validation.md`](pipeline/extraction/validation.md) AST reasons |
| `02b` execute CadQuery | program | [`pipeline/extraction/validation.md`](pipeline/extraction/validation.md) runtime reasons |
| `02c` build CAD graph | program | [`pipeline/extraction/validation.md`](pipeline/extraction/validation.md) cross-check reasons |
| `03b` construct task definitions | task | `03b` |
| `05` validate and export release | task | `05` |

`04` render prompt and choices does not write a row, because rendering must not
reject a definition.

Each pipeline stage owns its closed reason set. This document does not define a
second list, so a new reason is added in one place.

## Row

| Column | Format | Null | Meaning |
|---|---|---|---|
| `failure_id` | UUID v5 | no | Deterministic identity of the dedupe key. |
| `pipeline_stage` | enum | no | Which pipeline stage rejected the input. |
| `program_id` | string | no | The program the input belongs to. |
| `task_id` | string | yes | The task, when the subject is a task. |
| `input_sha256` | string | yes | The hash a pipeline stage uses for the input: `program_sha256`, `definition_sha256`, or `answer_sha256`. |
| `reason_code` | string | no | One member of the rejecting pipeline stage's reason set. |
| `detail` | string | no | Deterministic message, at most 500 characters. |
| `source_line` | integer | yes | Program line, when known. |
| `source_span` | struct | yes | Start and end column, when known. |
| `occurrence_count` | integer | no | How many times this exact rejection occurred. At least 1. |

The subject is the task when `task_id` is set, and the program otherwise. Every
task belongs to a program, so `program_id` is always present and the two cases
are unambiguous without a discriminator column.

`pipeline_stage` values are pipeline stage names in snake case:
`01d_normalize_programs`, `02a_extract_cadquery_ast`, `02b_execute_cadquery`,
`02c_build_cad_graph`, `03b_construct_task_definitions`, and
`05_validate_and_export_release`.

`failure_id` is `uuid5(namespace, key)` over the canonical JSON of the dedupe
key, using the serialization rules in `03b` construct task definitions. That
keeps it identical across Python and Go.

## Dedupe key

```text
(pipeline_stage, program_id, task_id, input_sha256, reason_code)
```

Two rejections with the same key are the same rejection. `detail`, `source_line`,
and `source_span` are not in the key because they are a function of the key: the
same input rejected for the same reason in the same pipeline stage produces the
same
message. A merge that finds two different details for one key is a defect, not a
new row.

## No run state in a row

A row carries no timestamp, host, attempt index, or stage version. Those make the
export non-reproducible and the dedupe unstable. The run manifest records the
versions for the whole run, and `occurrence_count` carries the repetition.

## Merge and order

Each pipeline stage appends to its own partition and never rewrites it. `05`
merges:

1. group rows by `failure_id`;
2. sum `occurrence_count`;
3. require every other column to agree, and fail the export when it does not;
4. sort by `pipeline_stage`, then `program_id`, then `task_id` with nulls first,
   then `reason_code`.

`05` writes the merged rows once as `failures.parquet`.

## Reconciliation

R-19 requires the counts to add up. `05` checks each chain step: the count
entering the step equals the count leaving it plus the failures recorded at that
step.

| Chain | Steps |
|---|---|
| Programs | selected, fetched, normalized, AST accepted, runtime accepted, graphed |
| Tasks | attempted, constructed, rendered, exported |

A mismatch blocks the export and names the step, the entering count, the leaving
count, and the recorded rejections. `05` cannot write a row for its own missing
rows, so the mismatch is reported in the export failure instead.

## Aggregation

`05` records the rejection counts in `manifest.json`, summed from
`occurrence_count`, by pipeline stage and reason, separately for programs and
tasks. The
counts are computed from `failures.parquet`, so the manifest cannot disagree with
the file.
