# 01b — Select program pool

**Parent:** [`01-external-dataset-etl.md`](01-external-dataset-etl.md).

**Purpose:** choose a deterministic, bounded pool of CadQuery programs for the
release from the external dataset metadata.

## Input / output

- Input: program metadata records from `01a` plus the selection policy.
- Output: a Parquet selection artifact with selected program IDs, the policy,
  counts, and exclusions.

## Behavior

- Apply the selection policy to the program metadata.
- Use C for P0 and P1. Add P at P2 for scale variation. Do not deduplicate P
  against C; they are separate populations.
- Select at most the target program count for the release.
- Use only metadata columns; do not download program text.
- Assign `split_group_id`: for CADEvolve core, the generator family; for
  ABC/ShapeNet, the mesh family. P and C versions of one family share the group.
- Record the policy, seed, collection counts, split-group counts, and excluded
  counts.
- Do not normalize or execute CadQuery.

## Tier decision

P0 and P1 use C only. C is canonical, centered, scaled, and binarized; it keeps
normalization, graph build, and prompt review simpler.

P2 adds P. C scales the longest bounding-box side to 200 units, so absolute scale
does not vary. P preserves the original pose and scale. Adding P at P2 gives the
release scale variation and arbitrary code style.

P and C versions of one generator or mesh family share a split group; P2 must
not put one version in train and the other in test.

## Open questions

### What is the target program count?

The last regeneration used 1,300 programs and produced 10,000 tasks. That is
about 7.7 tasks per program, so 1,000 programs is too close to the release floor.

- **1,300:** proven once, but little headroom for execution or task-generation
  failures.
- **1,500:** about 11.5k expected tasks, leaving room for rejects and split
  balance.
- **2,000+:** more diversity, but more download, normalization, execution, and
  graph work for no clear first-release benefit.
- **Full cache:** excessive.

**Recommendation:** select 1,500 C programs for P0/P1, with 1,000 usable
programs as the floor. Keep a reserve for failures. P2 adds a separately sized P
pool.

### Which metadata dimensions drive stratification?

- **Collection** is mandatory: ABC, ShapeNet, and CADEvolve core.
- **Feature tags** are the cheap coverage signal: `void_cut`,
  `kernel_face_selector`, `kernel_edge_selector`, `profile_polyline`,
  `path_curve`, and `kernel_vertex_selector`.
- **Split group** is mandatory for decontamination, but not a quota by itself.
- **Path family** is too fine for ABC/ShapeNet; use the split group instead.
- **Generator ID** in the cache is collection-level, not the real generator.

A full collection × tag cross-product is too sparse. Use a minimum per
collection and a minimum for each required tag, then fill the remainder
proportionally. Cap programs per split group so one generator or mesh family
does not dominate.

**Recommendation:** collection + required feature tags, with a per-group cap.

### Should the selection reserve a program pool for later releases?

- **No reserve:** smallest pool, but execution or task-generation failures can
  force a new selection.
- **Reserve 20–30%:** selection is metadata-only, so reserving IDs is cheap.
  Fetch, normalize, and execute reserved programs only if needed.
- **Reserve a full later slice:** more planning now, but later releases may want
  a different tier or coverage.

**Recommendation:** reserve 20–30% of IDs now; do not fetch or normalize them
until needed.

### Does the release need the paper's rewrite diversity?

The cache does not contain the 744,780 code rewrites. They add semantically
equivalent code styles, not new geometry.

- **Skip for the first release:** C is already canonical and template-like, but
  the task prompt is generated from the graph, not from code style alone.
- **Add later:** use the original tar or rewrite artifacts if prompt-style
  diversity becomes a measured problem.

**Recommendation:** defer rewrite diversity to P1. It is not a first-release
blocker.
