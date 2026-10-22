# Open questions

**Status:** ephemeral centralized inventory, 2026-10-22. The owning document is
authoritative; this file mirrors every unresolved question so the whole set can
be reviewed in one place. When a question is resolved, remove it here and in the
owning document. Absent contracts are tracked separately in
[`missing-contracts.md`](missing-contracts.md).

| Owner | ID | Priority | Open question |
|---|---|---|---|
| [`02a`](pipeline/02a-extract-cadquery-ast.md) | — | P2 | Should P2 support arbitrary Python control flow in P-tier programs, or keep the canonical-flat restriction and reject non-flat programs? |
| [`03b`](pipeline/03b-construct-task-definitions.md) | Q6 | P2 | How are plausible, deterministic near-miss choices generated and validated? |
| [`05`](pipeline/05-validate-and-export-release.md) | Q1 | P1 | How is same-CAD-model transfer overlap checked: AST-normalized program hash, CadQuery shape comparison, or both? |

Every pipeline stage not listed above has no open questions in its owning
document. The detailed context, recommendations, and resolution rules stay in
the owning document; this table is the cross-document inventory.
