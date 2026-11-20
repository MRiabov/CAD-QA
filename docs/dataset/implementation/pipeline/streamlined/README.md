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
[`../io-contracts.md`](../io-contracts.md); this block is only the sub-step read
order.

## Canonical per-doc template

Every file uses exactly this shape: one heading per phase, each phase with
exactly three labelled blocks. A single-phase step uses the blocks at top level.
Nothing else.

```markdown
# <sub-step> <name> — <subtitle>

> Authoritative: `../<sub-step>-<name>.md`

## <phase> — <verb>

READ:
- `<artifact or model>` → `<fields used>`

TRANSFORM:
- `<one deterministic rule per line, with the exact formula or constant>`

WRITE:
- `<artifact>` `(<identity>)` → `<fields>`
```

## Rules

1. **Terse and dry.** Every TRANSFORM line is an imperative with the exact
   formula, threshold, or constant. No hedging, no "should".
2. **No why.** The single `> Authoritative:` pointer is the only cross-reference.
   No decision IDs, no status tags, no open or resolved questions.
3. **Names, not definitions.** READ and WRITE name artifacts and models exactly
   as [`../io-contracts.md`](../io-contracts.md) names them. Field names are
   used, never defined.
4. **One file per sub-step.** `04` and `05` have no sub-steps and are one file
   each.
5. **Rejection is data.** A TRANSFORM line that rejects names the failure
   partition it writes. A rejection never crosses a sub-step boundary as an
   exception.
6. **Deterministic.** Same input and version produce the same artifact bytes.

## Docs

| Doc | Sub-step | Authoritative |
|---|---|---|
| [`01a-read-cadevolve-metadata.md`](01a-read-cadevolve-metadata.md) | `01a` read metadata | [`../01a-read-cadevolve-metadata.md`](../01a-read-cadevolve-metadata.md) |
| [`01b-select-program-pool.md`](01b-select-program-pool.md) | `01b` select pool | [`../01b-select-program-pool.md`](../01b-select-program-pool.md) |
| [`01c-fetch-program-pool.md`](01c-fetch-program-pool.md) | `01c` fetch pool | [`../01c-fetch-program-pool.md`](../01c-fetch-program-pool.md) |
| [`01d-normalize-programs.md`](01d-normalize-programs.md) | `01d` normalize | [`../01d-normalize-programs.md`](../01d-normalize-programs.md) |
| [`01e-write-external-dataset-manifest.md`](01e-write-external-dataset-manifest.md) | `01e` write manifest | [`../01e-write-external-dataset-manifest.md`](../01e-write-external-dataset-manifest.md) |
| [`02a-extract-cadquery-ast.md`](02a-extract-cadquery-ast.md) | `02a` extract AST | [`../02a-extract-cadquery-ast.md`](../02a-extract-cadquery-ast.md) |
| [`02b-execute-cadquery.md`](02b-execute-cadquery.md) | `02b` execute CadQuery | [`../02b-execute-cadquery.md`](../02b-execute-cadquery.md) |
| [`02c-build-cad-graph.md`](02c-build-cad-graph.md) | `02c` build graph | [`../02c-build-cad-graph.md`](../02c-build-cad-graph.md) |
| [`03a-allocate-task-quotas.md`](03a-allocate-task-quotas.md) | `03a` allocate quotas | [`../03-task-generation/03a-allocate-task-quotas.md`](../03-task-generation/03a-allocate-task-quotas.md) |
| [`03b-construct-task-definitions.md`](03b-construct-task-definitions.md) | `03b` construct definitions | [`../03-task-generation/03b-construct-task-definitions.md`](../03-task-generation/03b-construct-task-definitions.md) |
| [`03c-resolve-deficits.md`](03c-resolve-deficits.md) | `03c` resolve deficits | [`../03-task-generation/03c-resolve-deficits.md`](../03-task-generation/03c-resolve-deficits.md) |
| [`04-render-prompt-and-choices.md`](04-render-prompt-and-choices.md) | `04` render | [`../04-render-prompt-and-choices.md`](../04-render-prompt-and-choices.md) |
| [`05-validate-and-export-release.md`](05-validate-and-export-release.md) | `05` validate and export | [`../05-validate-and-export-release.md`](../05-validate-and-export-release.md) |
