# 01b — Select program pool

**Parent:** [`01-external-dataset-etl.md`](01-external-dataset-etl.md).

**Purpose:** choose a deterministic, bounded pool of CadQuery programs for the
release from the external dataset metadata.

## Input / output

- Input: program metadata records from `01a` plus the selection policy.
- Output: a Parquet selection artifact with active and reserve program IDs, the
  policy, counts, and exclusions.

## Behavior

- Apply the selection policy to the program metadata.
- Use C for P0 and P1. Add P at P2 for scale variation. Do not deduplicate P
  against C; they are separate populations.
- Select 1,500 active C programs for P0 and P1, plus 300–450 reserve IDs
  (20–30%). If fewer are available, select all and record the shortfall.
- Start from a larger metadata shortlist when review needs it; the active and
  reserve sets are the safety pool, not every fetched program.
- Use only metadata columns; do not download program text.
- Assign `cadevolve_split_group_id`: for CADEvolve core, the generator family;
  for CADEvolve-predicted ABC/ShapeNet, the mesh family. P and C versions of one
  family share the group.
- Record the policy, seed, collection counts, CADEvolve split group counts, and
  excluded counts.
- Do not normalize or execute CadQuery.

## Tier decision

P0 and P1 use C only. C is canonical, centered, scaled, and binarized; it keeps
normalization, graph build, and prompt review simpler.

P2 adds P. C scales the longest bounding-box side to 200 units, so absolute scale
does not vary. P preserves the original pose and scale. Adding P at P2 gives the
release scale variation and arbitrary code style.

P and C versions of one generator or mesh family share a CADEvolve split group;
P2 must not put one version in train and the other in test.

## Resolved questions

- **Program count.** *Resolved 2026-10-21.* Select 1,500 active C programs for P0
  and P1, with 1,000 usable programs as the release floor, plus 300–450 reserve
  IDs. P2 adds a separately sized P pool.

## Open questions

### Which metadata dimensions drive stratification?

- **Collection** is mandatory: ABC, ShapeNet, and CADEvolve core.
- **Feature tags** are the cheap coverage signal: `void_cut`,
  `kernel_face_selector`, `kernel_edge_selector`, `profile_polyline`,
  `path_curve`, and `kernel_vertex_selector`.
- **Split group** is mandatory for decontamination, but not a quota by itself.
- **CADEvolve `path_family`** is too fine for ABC/ShapeNet; use
  `cadevolve_split_group_id` instead.
- **Generator ID** in the cache is collection-level, not the real generator.

A full collection × tag cross-product is too sparse. Use a minimum per
collection and a minimum for each required tag, then fill the remainder
proportionally. Cap programs per CADEvolve split group so one generator or mesh
family does not dominate.

**Recommendation:** collection + required feature tags, with a per-group cap.

### Does the release need the paper's rewrite diversity?

The cache does not contain the 744,780 code rewrites. They add semantically
equivalent code styles, not new geometry.

- **Skip for the first release:** C is already canonical and template-like, but
  the task prompt is generated from the graph, not from code style alone.
- **Add later:** use the original tar or rewrite artifacts if prompt-style
  diversity becomes a measured problem.

**Recommendation:** defer rewrite diversity to P1. It is not a first-release
blocker.
