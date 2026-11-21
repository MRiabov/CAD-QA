# Visual review pack

**Status:** deferred, 2026-11-20. The review contract is in `05`; the renderer
lands after the first release. This is not a decision.

**Related:**
`docs/dataset/implementation/pipeline/05-validate-and-export-release.md`,
`docs/dataset/requirements/PRD.md` (R-17), `tools/dataset_explorer.py`.

## What it is

A pack of rendered tasks for human review. Each task carries the prompt text, a
render of the final solid state with the target and every clue-bound entity
highlighted in a distinct colour and labelled with its clue number, and the gold
answer.

The renderer does the work that re-deriving the task would otherwise take. The
reviewer checks that each highlight is the entity the clue names, that the answer
matches the geometry, and that the wording is clear.

The sample covers every task reasoning step count 1–10. For 6–10, it uses at
least 30 tasks per tier, or every task if the tier has fewer; that is the same
review the dataset PRD section 6.1 release gate requires.

## Why it is deferred

The pack reads the bound entity ids from the release row's evidence. That
projection is still moving (`MC-12`), so building the renderer now would be
against a schema that will change. The first release also gives a real sample to
render against instead of synthetic tasks.

## How it works

- The `node_id` of a CAD graph entity is a hash of the state and a geometric
  fingerprint: face centroid, area, normal, and bounding box; edge endpoints and
  length; vertex point.
- The renderer runs the program, tessellates each face separately, and matches
  the fingerprint to the shape.
- Faces become coloured cells, edges coloured tubes, vertices coloured spheres.
- Two entities with the same fingerprint are rejected at graph build, so the
  match is unique.
- The renderer extends `tools/dataset_explorer.py`, which already renders a
  program's `result` to a cached PNG with CadQuery and VTK.

## First-release fallback

Until the pack exists, the review uses the explorer's per-program render plus the
prompt and answer text. Tasks that need a closer look are flagged in the review
record.

## Acceptance

A sampled task renders with the target and every clue-bound entity visible and
distinct, and the reviewer can confirm the task without re-deriving it.
