# Shortcut resistance

**Status:** proposed, 2026-11-25. P1 requirement spec for R-5.

## Purpose

Define what the dataset checks when it claims R-5 shortcut resistance. The check
is a `03b` quality gate: a definition that fails it is a failure row, not a
persisted task. The examples are in
[`views/shortcut-resistance.md`](views/shortcut-resistance.md).

## Scope

- P1. The P0 release does not claim R-5 and does not run the quality gate.
- Shape-required tasks only: `geometry_required = true`.
- A construction-time quality gate in `03b`, not a release pipeline stage and not a `05` check.
- The LLM-model consequence — that an LLM model cannot answer by shortcut — is
  the Phase 2 baseline, not this check.

## What is checked

### Answer dependency chain

The **answer dependency chain** is the set of distinct operations that produce or
change the measured answer subject:

- the operation that produced the subject's containing state;
- the state chain from the subject's first appearance to the final state;
- every operation that changes the subject's fingerprint.

The chain is resolved from the CAD graph's operation provenance. It is not a
symbolic interpretation of the program, and it does not evaluate geometry.

### Topology dependency

The topology dependency is true when the chain contains an operation from the
closed topology-changing class, or when the subject is a CadQuery selector result over an
entity produced by one. The class is a policy list, versioned with the check.

### Verdict

| Verdict | Condition |
|---|---|
| `not_applicable` | `geometry_required = false`; R-5 does not apply. |
| `unknown` | The subject or chain cannot be resolved, or the chain exceeds `max_dependency_operations`. |
| `fail` | The chain has fewer than `dependency_operation_min` operations and no topology dependency. |
| `pass` | The chain has at least `dependency_operation_min` operations, or a topology dependency. |

`unknown` fails closed: a shape-required definition whose chain cannot be
resolved is rejected with that reason, not accepted.

### Rejection

A `fail` or `unknown` on a shape-required definition rejects the definition. The
failure row names `shortcut_resistance` and records the dependency operation
count, the topology flag, and the reason. The definition is not passed to `04`
and is not persisted. The P1 release report counts the rejections and states the
threshold; the accepted set is all-pass by construction.

A release built without the quality gate (the P0 release) can be measured afterwards by
the same function as a report; that report is a view, not a pipeline stage, and does not
change the release.

## What is not checked

- Whether an LLM model can answer the task. That is the Phase 2 shortcut
  baseline.
- Whether a text-only formula exists for the answer. The check does not build a
  symbolic CAD engine; it measures dependency depth.
- Every possible shortcut. The check is a conservative floor: a multi-operation
  closed form can pass. The P1 report says so; it does not claim a proof.
- The correctness of the graph provenance. That is graph completeness
  ([`../implementation/pipeline/extraction/graph-completeness.md`](../implementation/pipeline/extraction/graph-completeness.md)).
- The correctness or uniqueness of the answer. Those are R-1 and R-2.

## Policy

- `dependency_operation_min` is provisional `3`. It is part of the check version,
  not a PRD constant; the P1 report records the distribution so the threshold
  can move without a graph rebuild.
- `max_dependency_operations` caps the walk. A chain above it is `unknown` with
  reason `closure_cap`.
- The topology-changing operation class is a closed list. Adding an operation is
  a check-version change, not a silent edit.
- The check version also covers the closure rule and the validity detail shape.

## Storage and cost

- The check adds one small validity detail per definition: the dependency
  operation count, the topology flag, the verdict, and a short reason. The chain
  and operation ids are never stored.
- `03b` already reads the `CadGraph`, so the check adds one graph walk per
  candidate definition, linear in the subject's state chain. It does not
  execute CadQuery.
- A rejected definition is a failure row, not a `TaskDefinition`; the P0 release
  schema is unchanged.

## Acceptance

The check is accepted when:

- a shape-required definition with a failing verdict is a failure row naming
  `shortcut_resistance`, not a persisted definition;
- a non-shape definition records `not_applicable` and is not rejected by this
  check;
- `unknown` rejects and is never treated as `pass`;
- the validity detail records the count, the topology flag, the verdict, and the
  reason, and no dependency chain;
- the same definition, graph identity, and check version produce the same
  verdict.

## Open questions

- Is `dependency_operation_min = 3` the right threshold, or should it be set
  from the Phase 2 baseline?
- Which CadQuery methods belong to the closed topology-changing list?
- Does the P1 release report use the rejection count as a release gate, or only report it?
- Does a rejected definition feed back into `03b`'s cover search, or only into
  the deficit ledger? The first changes the accepted set; the second does not.

## Decisions

- `DS-REQ-38` records that R-5 is P1 and that this quality gate is its dataset check.
