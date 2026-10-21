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
- Select within the chosen CADEvolve tier: P, C, or an explicit mix. Do not
  deduplicate P against C; they are separate populations.
- Select at most the target program count for the release.
- Use only metadata columns; do not download program text.
- Assign `split_group_id`: for CADEvolve core, the generator family; for
  ABC/ShapeNet, the mesh family. P and C versions of one family share the group.
- Record the policy, seed, collection counts, split-group counts, and excluded
  counts.
- Do not normalize or execute CadQuery.

## Open questions

- Which tier or tier mix does the first release use: P, C, or both?
- What is the target program count for the first release?
- Which metadata dimensions drive stratification: collection, generator,
  path family, geometry tags, or a combination?
- Should the selection reserve a program pool for later releases?
