# 01b — Select program pool

**Parent:** [`01-external-dataset-etl.md`](01-external-dataset-etl.md).

**Purpose:** choose a deterministic, bounded pool of CadQuery programs for the
release from the external dataset metadata.

## Input / output

- Input: program metadata records from `01a` plus the selection policy.
- Output: a Parquet selection artifact with active and reserve program IDs,
  supplemental deltas, derived `tier`, `cadevolve_program_family_id`,
  `policy_version`, `seed`, the policy values, counts, and exclusions.

## Selection policy

`SelectionPolicy` carries every number the selection uses, so a test or a smaller
run can inject its own:

| Field | Default | Meaning |
|---|---|---|
| `scope` | C | In-scope tiers and collections. |
| `seed` | required | Deterministic ordering seed. |
| `active_count` | 1,500 | Active programs to select. |
| `reserve_count` | 300–450 | Reserve programs to select. |
| `family_cap` | 2 | Active programs per `cadevolve_program_family_id`. |
| `collection_minimum` | 300 | Active programs per in-scope collection. |
| `feature_tag_minimum` | 50 | Active programs per required feature tag. |
| `tag_list` | `void_cut`, `kernel_face_selector`, `kernel_edge_selector`, `profile_polyline`, `path_curve` | Feature tags that carry a minimum. |
| `usable_floor` | 1,000 | Usable active programs a run needs. |

For P0/P1, the in-scope set is C only: `ABC-C`, `CADEvolve-C-core`, and
`ShapeNet-C`. P2 adds P as a separately sized pool; this policy applies inside
each tier pool, not across a combined C+P total.

Within the in-scope pool:

1. Deduplicate by `normalized_source_code_hash` within each collection. Do not
   deduplicate across collections or across P and C. Within each duplicate group,
   keep the record with the lexicographically smallest `source_id`; record the
   discarded IDs and any family conflict. The survivor's family is used.
2. Apply the hard family cap: at most two active programs per
   `cadevolve_program_family_id`. The cap counts active programs; a family at the
   cap can still supply reserve rows.
3. Reserve at least 50 active seats for each required feature tag:
   `void_cut`, `kernel_face_selector`, `kernel_edge_selector`,
   `profile_polyline`, and `path_curve`. A program may satisfy several tags.
4. Give each in-scope collection a target minimum of 300 active programs. Tag
   reservations count toward this minimum.
5. Allocate the remaining active slots proportionally to collection size.
6. Within each collection, order by `sha256(seed || source_id)`.
7. Select 1,500 active C programs for P0/P1. Select the next 300–450 by the same
   policy as reserve.

## Constraint precedence

The order is:

1. Scope, deduplication, and the hard family cap.
2. The hard 1,500-program cap.
3. Feature-tag minima, because they preserve task capability.
4. Collection minima, because they preserve collection diversity.
5. Proportional fill.

A program may count toward a tag minimum and a collection minimum at the same
time. If a tag has fewer than 50 eligible programs after the family cap, select
all eligible and record the shortfall. If a collection cannot reach 300 after the
family cap, tag reservations, and the hard cap, record the shortfall. Never
exceed the hard cap to satisfy a lower-priority target.

The three C collections need 900 programs at their minimum, within the 1,500 cap.
P2 does not combine six collections under one 1,500 cap; its P pool is sized
separately.

The policy is deterministic for a given cache revision, seed, and metadata
schema. It records unmet quotas instead of silently under-filling.

The cache also has a rare `kernel_vertex_selector` tag. It is diagnostic, not a
quota: only 89 C records carry it, and requiring a fixed minimum would consume
almost all of them.

## Exclusions

An exclusion row records the excluded `source_id`, its collection, and one
reason. The set is closed:

| Reason | Meaning |
|---|---|
| `duplicate_hash` | Another record in the same collection has the same `normalized_source_code_hash` and a smaller `source_id`. |
| `family_cap` | The program's `cadevolve_program_family_id` already holds its two active programs. |
| `out_of_scope_tier` | The program's tier is not in the selection policy. |
| `not_selected` | The program is eligible but outside the active and reserve sets. |

The counts reconcile: cache rows equal active, plus reserve, plus exclusions.
An exclusion is not a failure record; [`failure-record.md`](../failure-record.md)
says so.

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

`03c` sends a `ProgramRequest` when the task quota plan has a deficit that the
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
