# Shortcut resistance view

**Status:** derived view, 2026-11-25; reviewed by the owner 2026-11-25. The
conservative passes and the threshold examples are accepted.

A worked table of what the `03b` shortcut-resistance check accepts and rejects.
Every rule here comes from
[`../shortcut-resistance.md`](../shortcut-resistance.md); the implementation is
the P1 quality gate in
[`../../implementation/pipeline/03-task-generation/03b-construct-task-definitions/a-construction.md`](../../implementation/pipeline/03-task-generation/03b-construct-task-definitions/a-construction.md).

This view owns no rule and no open question. If it disagrees with the
requirements doc, the requirements doc is right. A missing example is a question
for the requirements doc, not a rule to add here.

The check is a **floor**, not a proof. A `pass` means the answer depends on an
operation chain or a topology predicate; it does not mean an LLM model cannot
answer. The Phase 2 baseline measures that.

## How to read a row

| Column | Meaning |
|---|---|
| Chain | The operations that produce or change the measured subject, in program order. |
| Count | The number of distinct operations in the chain. |
| Topology | Whether the chain contains a topology-changing operation, or the subject is a CadQuery selector result over one. |
| Verdict | `pass`, `fail`, `not_applicable`, or `unknown`. |

`dependency_operation_min` is provisionally 3. `unknown` fails closed.

## Examples

| Example | Program (abbreviated) | Answer | Chain | Count | Topology | Verdict | Why |
|---|---|---|---|---|---|---|---|
| Box volume | `box(10, 20, 5)` | volume `1000` | `box` | 1 | no | `fail` | One operation; the literals determine the answer. |
| Box face area | `box(10, 20, 5)`, face facing +z | area `200` | `box` | 1 | no | `fail` | One operation; the face area is a literal product. |
| Cylinder volume | `cylinder(2, 10)` | volume `125.66` | `cylinder` | 1 | no | `fail` | One primitive; closed form from the arguments. |
| Translated box volume | `box(10, 20, 5).translate((5, 0, 0))` | volume `1000` | `box`, `translate` | 2 | no | `fail` | A move does not change topology; the volume is still literal. |
| Box with a hole, volume | `box(10, 20, 5).faces(">Z").hole(2)` | volume `937.17` | `box`, `hole` | 2 | yes | `pass` | The removed material changes topology, so the floor passes it. The volume is still closed-form; the Phase 2 baseline is the real test. |
| Box with a hole, circular edge length | `box(10, 20, 5).faces(">Z").hole(2)`, circular edge | length `12.57` | `box`, `hole` | 2 | yes | `pass` | Same reason: the hole is a topology change. This is a known false pass of the floor. |
| Boolean chain volume | five stacked cuts and unions | volume | the five operations | 5 | yes | `pass` | The answer depends on the chain and the topology changes. |
| Face count after cuts | `box(...).cut(...).cut(...)`, face count | count | the three operations | 3 | yes | `pass` | A topology count is not in the text. |
| Translation chain volume | three `translate` calls after a box | volume `1000` | `box`, `translate`, `translate` | 3 | no | `pass` | Depth alone reaches the threshold. This is a known conservative pass. |
| Operation count | any program, "how many cuts?" | count | no shape subject | — | — | `not_applicable` | `geometry_required` is false; R-5 does not apply. |
| Provenance identity | any program, "which operation is last?" | identity | no shape subject | — | — | `not_applicable` | The answer is operation order, not the built shape. |
| Missing provenance | a shape-required task whose subject has no operation id | measurement | unresolved | — | — | `unknown` | Fail closed; this is a miss, not a pass. |
| Closure cap | a chain above `max_dependency_operations` | measurement | truncated | cap | — | `unknown` | Fail closed; the chain is not stored. |

## What the examples show

- A single primitive, or a move-only chain below the threshold, fails.
- A topology change passes even when the answer is a closed form. That is the
  deliberate conservatism: the dependency walk cannot tell `2π·2` from a
  topology count without becoming a symbolic engine.
- The threshold is visible. Two moves fail; three moves pass. That is why the
  threshold is a policy constant and the P1 report records the distribution.
- Non-shape tasks are out of scope, not failures.
- An unresolved chain rejects. The check never treats missing provenance as
  evidence of shortcut resistance.

## What this view does not decide

- Whether the threshold should stay at 3. The requirements doc owns that.
- Whether a P1 release uses the rejection count as a release gate. The plan owns that.
- Whether an LLM model can derive a `pass`. The Phase 2 baseline owns that.
