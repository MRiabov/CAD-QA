# 01b — Select program pool

**Parent:** [`01-external-dataset-etl.md`](01-external-dataset-etl.md).

**Purpose:** choose a deterministic, bounded pool of CadQuery programs for the
release from the external dataset metadata.

## Input / output

- Input: program metadata records from `01a` plus the selection policy.
- Output: a Parquet selection artifact with active and reserve program IDs,
  supplemental deltas, derived `tier`, `cadevolve_program_family_id`, the policy,
  counts, and exclusions.

## Selection policy

For P0/P1, select from C only:

1. Deduplicate by `normalized_source_code_hash` within each collection. Do not
   deduplicate across collections or across P and C. Within each duplicate group,
   keep the record with the lexicographically smallest `source_id`; record the
   discarded IDs and any family conflict. The survivor's family is used.
2. Give each collection a minimum quota of 300 active programs.
3. Allocate the remaining active slots proportionally to collection size.
4. Within each collection, order by `sha256(seed || source_id)`.
5. Cap selection at two programs per `cadevolve_program_family_id`.
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

## Tier derivation

The cache has no `tier` column. Derive it from `source_subtree`:

| `source_subtree` | `tier` |
|---|---|
| `CADEvolve-C` | `C` |
| `CADEvolve-P` | `P` |

Any other value is rejected and recorded as a cache-schema failure. Do not infer
`tier` from the collection name or `generator_id`.

## Family derivation

`cadevolve_program_family_id` is derived from the cache's `path_family` column
only, not from `normalized_archive_member_path` and not from `generator_id`.
`path_family` is populated for every cache row.

1. Take the last component of `path_family`.
2. Remove a trailing `.py`.
3. For `*-core`, remove a trailing `_<digits>` sample suffix, lowercase the
   name, and remove non-alphanumeric characters. Prefix it with `cadevolve:`.
4. For ABC, remove a trailing `_trimesh_<digits>` variant suffix. Prefix the
   remaining mesh identifier with `abc:`.
5. For ShapeNet, keep the last component as the mesh identifier and prefix it
   with `shapenet:`.
6. If the component is empty or the collection is unknown, use
   `unknown:<source_id>` and record the fallback.

P and C versions use the same normalized family name, so they share the group
when the names match. A duplicate group that spans families uses the survivor's
family and records the conflict.

## Behavior

- Derive `tier` and `cadevolve_program_family_id` from the metadata before
  selection.
- Apply the selection policy to the program metadata.
- Use C for P0 and P1. Add P at P2 for scale variation. Do not deduplicate P
  against C; they are separate populations.
- Select 1,500 active C programs for P0 and P1, plus 300–450 reserve IDs
  (20–30%). If fewer are available, select all and record the shortfall.
- Start from a larger metadata shortlist when review needs it; the active and
  reserve sets are the safety pool, not every fetched program.
- Use only metadata columns; do not download program text.
- Assign `cadevolve_program_family_id`: for CADEvolve core, the generator family;
  for CADEvolve-predicted ABC/ShapeNet, the mesh family. P and C versions of one
  family share the group.
- Record the policy, seed, collection counts, CADEvolve program family counts, and
  excluded counts.
- Do not normalize or execute CadQuery.

## Tier decision

P0 and P1 use C only. C is canonical, centered, scaled, and binarized; it keeps
normalization, graph build, and prompt review simpler.

P2 adds P. C scales the longest bounding-box side to 200 units, so absolute scale
does not vary. P preserves the original pose and scale. Adding P at P2 gives the
release scale variation and arbitrary code style.

P and C versions of one generator or mesh family share a program family ID;
P2 must not put one version in train and the other in test.

## Supplemental selection

`03c` sends a `ProgramRequest` when the release plan has a deficit that the
current pool cannot fill. A supplemental selection produces a
`ProgramSelectionDelta`; it does not replace the original selection.

- **Extend:** continue the existing deterministic hash order beyond the active
  and reserve sets.
- **Target:** select programs by missing feature tag, collection, or family.

A targeted request is deterministic for the request, policy version, and seed.
Record the request ID, policy version, added IDs, and reason. The original
selection remains immutable.

The delta must preserve family split assignment: a program in an already assigned
family inherits its split. A new family is assigned in `03a` before generation.

## Resolved questions

- **Program count.** *Resolved 2026-10-21.* Select 1,500 active C programs for P0
  and P1, with 1,000 usable programs as the release floor, plus 300–450 reserve
  IDs. P2 adds a separately sized P pool.
- **Code-rewrite augmentation.** *Resolved 2026-10-21.* Skip it for the first
  release. The release samples a bounded set of families; the 744,780 rewrites
  add code-style variants, not new families, geometry, or task capabilities.
