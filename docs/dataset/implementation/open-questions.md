# Open questions

**Status:** ephemeral developer index, 2026-10-21. This file only links to the
owning docs. Each question is resolved in its owning doc; remove the entry here
when it is resolved. Absent contracts are tracked separately in
[`missing-contracts.md`](missing-contracts.md).

## 02a — Extract CadQuery AST

- [ ] CadQuery method allowlist — [open questions](pipeline/02a-extract-cadquery-ast.md#open-questions).
- [ ] P2 control flow in P-tier programs — [open questions](pipeline/02a-extract-cadquery-ast.md#open-questions).
- [ ] Reject or defer unresolved CadQuery selector strings — [open questions](pipeline/02a-extract-cadquery-ast.md#open-questions).

## 02b — Execute CadQuery

- [ ] Timeout and memory limits — [open questions](pipeline/02b-execute-cadquery.md#open-questions).
- [ ] Kernel handle stability — [open questions](pipeline/02b-execute-cadquery.md#open-questions).
- [ ] CadQuery selector failure behavior — [open questions](pipeline/02b-execute-cadquery.md#open-questions).

## 02c — Build CAD graph

- [ ] Typed `attributes` schema per graph node type — [open questions](pipeline/02c-build-cad-graph.md#open-questions).
- [ ] Entity node ID strategy — [open questions](pipeline/02c-build-cad-graph.md#open-questions).
- [ ] Unmapped CadQuery selector result behavior — [open questions](pipeline/02c-build-cad-graph.md#open-questions).

## 03b — Construct task definitions

- [ ] P2 near-miss choice generation and validation — [open questions](pipeline/03b-construct-task-definitions.md#open-questions).

## 05 — Validate and export release

- [ ] P1 same-CAD-model transfer-overlap check — [open questions](pipeline/05-validate-and-export-release.md#open-questions).

## None

- `01`, `03a`, `03c`, and `04` have no open questions. They do have missing
  contracts, tracked in [`missing-contracts.md`](missing-contracts.md).
