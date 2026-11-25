# Open questions

**Status:** ephemeral centralized inventory, 2026-10-22. The owning document is
authoritative; this file mirrors every unresolved question so the whole set can
be reviewed in one place. When a question is resolved, remove it here and in the
owning document. Absent contracts are tracked separately in
[`missing-contracts.md`](missing-contracts.md).

| Owner | ID | Priority | Open question |
|---|---|---|---|
| [`02a`](pipeline/02a-extract-cadquery-ast.md) | — | P2 | Should P2 support arbitrary Python control flow in P-tier programs, or keep the canonical-flat restriction and reject non-flat programs? |
| [`03b`](pipeline/03-task-generation/03b-construct-task-definitions/README.md) | Q6 | P2 | How are plausible, deterministic near-miss choices generated and validated? |
| [`02c`](pipeline/02c-build-cad-graph.md#open-questions) | Q1 | P1 | Is `angle` between two edges emitted at all? No reference class names an edge, so the emission rule produces no such row, while `graph-content.md` §4 declares the two-edge angle at P0; the path-tangent angle is P1. |
| [`task-structure.md`](../requirements/task-structure.md#8-open-questions) | — | P1 | Is a count a clue at all? It removes no candidate on its own, so it may belong to the answer meaning rather than to a clue. |
| [`task-structure.md`](../requirements/task-structure.md#8-open-questions) | — | P1 | Which direction words may a rank clue use, and does a set need a stated order before it can be ranked? |
| [`task-structure.md`](../requirements/task-structure.md#8-open-questions) | — | P1 | May a provenance clue point at a second set, or is it always one operation or CadQuery profile? |
| [`task-structure.md`](../requirements/task-structure.md#8-open-questions) | — | P1 | Is `cadquery_workplane` a task target category in the first release? Its answers are a choice label or a frame the program already states, so it does not read the built shape. |
| [`task-structure.md`](../requirements/task-structure.md#8-open-questions) | — | P1 | May a task narrow more than one set, so that a later step joins two narrowed sets? It was done before as `reference_*_distance`; deferred to P1 or P2, undecided. |
| [`task-structure.md`](../requirements/task-structure.md#8-open-questions) | — | P1 | When is the target a scalar value rather than the entity? Both definitions describe a measurement answer and no rule chooses between them. |

Every owning document not listed above has no open questions. The detailed
context, recommendations, and resolution rules stay in the owning document; this
table is the cross-document inventory.
