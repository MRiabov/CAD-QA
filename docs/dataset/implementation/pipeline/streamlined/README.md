# Streamlined pipeline docs

> **This folder is the executable spec.** The authoritative pipeline stage docs
> and [`../io-contracts.md`](../io-contracts.md) own the WHY and the contract.
> These files are the WHAT: a dry, flow-ordered DAG of every sub-step, with no
> rationale, no status, and no open decisions. An implementing agent reads this
> folder top-to-bottom and can build the dataset generator; a test reads a
> sub-step and can assert its exact edge.
>
> If this folder and an authoritative doc disagree, the authoritative doc wins,
> and the disagreement is a bug.

## Mirror rule

This folder mirrors the authoritative `../` folder structure exactly. A pipeline stage that is a folder there is a folder here, and its lettered sub-documents
have the same names:

```text
pipeline/03-task-generation/03a-allocate-task-quotas/README.md
pipeline/03-task-generation/03a-allocate-task-quotas/a-support-derivation.md
streamlined/03-task-generation/03a-allocate-task-quotas/README.md
streamlined/03-task-generation/03a-allocate-task-quotas/a-support-derivation.md
```

`tools/ci_cd/check-doc-mirror` enforces the rule for both `streamlined/` and
[`../testing/`](../testing/). `decisions.md`, `algorithm/`, and `extraction/`
are excluded: they own rationale and field mechanics, not a pipeline stage contract.
`models/` is an addition, not a mirror: it owns the typed model declarations
that pipeline stage docs reference.

## Execution order

```text
01a read metadata → 01b select pool → 01c fetch pool → 01d normalize → 01e write manifest

02a extract AST → 02b execute CadQuery → 02c build graph     (per program, from 01d)

03a allocate quotas → 03b construct definitions → 03c resolve deficits
  03c fast loop: 03a → 03b
  03c slow loop: 01b → 01c → 01d → 02a/02b/02c → 03a → 03b

04 render prompt and choices                                   (from 03b + 01d)

05 validate and export release                                 (from 04)
```

The DAG of pipeline stages is owned by
[`../io-contracts.md`](../io-contracts.md); [`00-end-to-end.md`](00-end-to-end.md)
is its executable form. A run is incremental; the run manifest, Parquet parts,
flush rule, cache, and resume rule are in
[`../../run-contract.md`](../../run-contract.md).

## Models

Every typed model in the DAG is declared once under [`models/`](models/README.md),
in the language that owns it: Go structs for Go pipeline stages and Pydantic classes for
the Python worker pipeline stages. The declaration carries the field set, the owner, the
producer, and the consumers. A pipeline stage doc names a typed model and its fields; it never
redefines them.

The typed model files are the hand-checked boundary audit: a READ that names a field
must find it on the typed model the producer writes, and a WRITE must name a field the
typed model declares. A field or typed model that no declaration carries is a missing
contract, not a free choice.

## Canonical per-doc template

Every file uses exactly this shape: one heading per phase, each phase with
exactly three labelled blocks. A single-phase step uses the blocks at top level.
A folder's `README.md` states the boundary for its pipeline stage and links its sub-documents;
the sub-documents carry the phases. Nothing else.

```markdown
# <sub-step> <name> — <subtitle>

> Authoritative: `../../<sub-step>-<name>.md`
> <Sub-document>: `../../<path>.md` (only when the executable rule lives there)
> Models: `models/<stage>.md`

## <phase> — <verb>

READ:

- `<artifact or typed model>` → `<fields used>`

TRANSFORM:

- `<one deterministic rule per line, with the exact formula or constant>`

WRITE:

- `<artifact>` `(<identity>)` → `<fields>`
```

## Rules

1. **Terse and dry.** Every TRANSFORM line is an imperative with the exact
   formula, threshold, or constant. No hedging, no "should".
2. **No why.** Pointer lines name the authoritative doc, the sub-document when
   the executable rule lives there, and the typed model file. Nothing else is a
   cross-reference: no decision IDs, no status tags, no open or resolved
   questions.
3. **Names and declared typed models.** READ and WRITE name artifacts and typed models
   exactly as [`../io-contracts.md`](../io-contracts.md) and
   [`models/`](models/README.md) name them. Field names are used, never defined.
4. **One file per sub-document.** `04` has no sub-documents and is one file.
   `03a`, `03b`, and `05` are folders whose sub-documents match the
   authoritative folder.
5. **Rejection is data.** A TRANSFORM line that rejects names the failure
   partition it writes, or states that the defect stops the run before the
   artifact is written. A rejection never crosses a sub-step boundary as an
   exception.
6. **Deterministic.** Same input and version produce the same artifact bytes.

## Docs

| Doc | Sub-step | Authoritative |
|---|---|---|
| [`00-end-to-end.md`](00-end-to-end.md) | The whole DAG. | [`../00-end-to-end.md`](../00-end-to-end.md) |
| [`01a-read-cadevolve-metadata.md`](01a-read-cadevolve-metadata.md) | `01a` read metadata | [`../01a-read-cadevolve-metadata.md`](../01a-read-cadevolve-metadata.md) |
| [`01b-select-program-pool.md`](01b-select-program-pool.md) | `01b` select pool | [`../01b-select-program-pool.md`](../01b-select-program-pool.md) |
| [`01c-fetch-program-pool.md`](01c-fetch-program-pool.md) | `01c` fetch pool | [`../01c-fetch-program-pool.md`](../01c-fetch-program-pool.md) |
| [`01d-normalize-programs.md`](01d-normalize-programs.md) | `01d` normalize | [`../01d-normalize-programs.md`](../01d-normalize-programs.md) |
| [`01e-write-external-dataset-manifest.md`](01e-write-external-dataset-manifest.md) | `01e` write manifest | [`../01e-write-external-dataset-manifest.md`](../01e-write-external-dataset-manifest.md) |
| [`02a-extract-cadquery-ast.md`](02a-extract-cadquery-ast.md) | `02a` extract AST | [`../02a-extract-cadquery-ast.md`](../02a-extract-cadquery-ast.md) |
| [`02b-execute-cadquery.md`](02b-execute-cadquery.md) | `02b` execute CadQuery | [`../02b-execute-cadquery.md`](../02b-execute-cadquery.md) |
| [`02c-build-cad-graph.md`](02c-build-cad-graph.md) | `02c` build graph | [`../02c-build-cad-graph.md`](../02c-build-cad-graph.md) |
| [`03-task-generation/03a-allocate-task-quotas/README.md`](03-task-generation/03a-allocate-task-quotas/README.md) | `03a` allocate quotas | [`../03-task-generation/03a-allocate-task-quotas/README.md`](../03-task-generation/03a-allocate-task-quotas/README.md) |
| [`03-task-generation/03b-construct-task-definitions/README.md`](03-task-generation/03b-construct-task-definitions/README.md) | `03b` construct definitions | [`../03-task-generation/03b-construct-task-definitions/README.md`](../03-task-generation/03b-construct-task-definitions/README.md) |
| [`03-task-generation/03c-resolve-deficits.md`](03-task-generation/03c-resolve-deficits.md) | `03c` resolve deficits | [`../03-task-generation/03c-resolve-deficits.md`](../03-task-generation/03c-resolve-deficits.md) |
| [`04-render-prompt-and-choices.md`](04-render-prompt-and-choices.md) | `04` render | [`../04-render-prompt-and-choices.md`](../04-render-prompt-and-choices.md) |
| [`05-validate-and-export-release.md`](05-validate-and-export-release.md) | `05` validate and export | [`../05-validate-and-export-release.md`](../05-validate-and-export-release.md) |

## Typed model declarations

| Doc | Pipeline stage |
|---|---|
| [`models/README.md`](models/README.md) | Registry, ownership, and boundary audit. |
| [`models/01-external-dataset-etl.md`](models/01-external-dataset-etl.md) | `01` typed models. |
| [`models/02-execute-cadquery-and-build-graph.md`](models/02-execute-cadquery-and-build-graph.md) | `02a` and `02b` typed models. |
| [`models/02c-build-cad-graph.md`](models/02c-build-cad-graph.md) | `02c` typed models. |
| [`models/03-task-generation.md`](models/03-task-generation.md) | `03` typed models. |
| [`models/04-render-prompt-and-choices.md`](models/04-render-prompt-and-choices.md) | `04` typed models. |
| [`models/05-validate-and-export-release.md`](models/05-validate-and-export-release.md) | `05` typed models. |
| [`models/cross-cutting.md`](models/cross-cutting.md) | Failure record, run manifest, pipeline stage marker, tolerance policy. |
