# 01b — Select program pool

**Parent:** [`01-external-dataset-etl.md`](01-external-dataset-etl.md).

**Purpose:** choose a deterministic, bounded pool of CadQuery programs for the
release from the external dataset metadata.

## Input / output

- Input: program metadata records from `01a` plus the selection policy.
- Output: a Parquet selection artifact with active and reserve program IDs, the
  policy, counts, and exclusions.

## Selection policy

For P0/P1, select from C only:

1. Deduplicate by `normalized_source_code_hash`.
2. Give each collection a minimum quota of 300 active programs.
3. Allocate the remaining active slots proportionally to collection size.
4. Within each collection, order by `sha256(seed || source_id)`.
5. Cap selection at two programs per `cadevolve_split_group_id`.
6. Ensure at least 50 active programs for each required feature tag:
   `void_cut`, `kernel_face_selector`, `kernel_edge_selector`,
   `profile_polyline`, and `path_curve`. Select all available if a tag has fewer
   than 50.
7. Select 1,500 active programs. Select the next 300–450 by the same policy as
   reserve.

The policy is deterministic for a given cache revision, seed, and metadata
schema. It records unmet quotas instead of silently under-filling.

The cache also has a rare `kernel_vertex_selector` tag. It is diagnostic, not a
quota: only 89 C records carry it, and requiring a fixed minimum would consume
almost all of them.

## Split group derivation

`cadevolve_split_group_id` is derived from the CADEvolve cache path, not from
the cache's collection-level `generator_id`.

1. Take the last component of `path_family` or
   `normalized_archive_member_path`.
2. Remove a trailing `.py`.
3. For CADEvolve core, remove a trailing `_<digits>` sample suffix, lowercase
   the name, and remove non-alphanumeric characters. The result is the generator
   family, prefixed with `cadevolve:`.
4. For ABC, remove a trailing `_trimesh_<digits>` variant suffix and prefix the
   ABC mesh identifier with `abc:`.
5. For ShapeNet, keep the ShapeNet mesh identifier and prefix it with
   `shapenet:`.
6. If the path cannot be parsed, use `unknown:<source_id>` and record the
   fallback.

P and C versions use the same normalized family name, so they share the group
when the names match.

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
- **Code-rewrite augmentation.** *Resolved 2026-10-21.* Skip it for the first
  release. The release samples a bounded set of families; the 744,780 rewrites
  add code-style variants, not new families, geometry, or task capabilities.
