# Dataset QA Bug/Fix Report

This document records concrete dataset QA failures found while auditing
`runs/current_cadevolve1000_10k_regen_20260613/release_10k/rows.parquet`, plus
the corresponding fixes. It is intentionally example-driven so each fix can be
reviewed against actual malformed rows.

## Current Artifact Status

- `release_10k/rows.parquet`: 10,000 rows, rewritten in place through the
  current resolver/materializer code.
- The rewrite preserves the original 10,000 selected row IDs and 900 source IDs.
- Public-answer QA now passes for the release artifact: no internal entity-ID
  answer contract, no colon-bearing public gold answers, no overwide candidate
  lists, no ambiguous reassigned source-ref answers, and no duplicate prompts.
- Default `release-candidate` validation passes. The stricter
  `benchmark-release` verifier still fails release-scale distribution/evidence
  gates; see "Remaining Benchmark Gates" below.

## Bug 1: Public Rows Asked For Internal Entity IDs

### Example malformed row

Row:
`row:graph:src_0113e9be89285bf2:synth:v3:parameterized_edge_spatial_relation_tie_break_extreme`

Malformed answer:

```text
edge:kernel:snapshot_wp11_edges:964744ac2162c9e6
```

Malformed instruction:

```text
Return exactly one entity_id.
```

### Why this is wrong

The public task asks a model to answer from the CadQuery script. A kernel entity
ID with an internal hash is not recoverable from the script and trains/evaluates
on hidden implementation identifiers instead of CAD reasoning.

### Fix

For public entity targets such as edges, faces, selectors, and path segments, the
resolver now switches to public candidate labels. The prompt exposes a bounded
choice list, and the gold answer is a label such as `A`, not an internal ID.

### Evidence

Row-level QA on the rewritten temp artifact:

```text
entity_id_instruction: 0
colon_gold: 0
```

## Bug 2: Candidate Label Lists Were Too Wide

### Example malformed pattern

Earlier QA found candidate-label rows with more than 26 choices, including rows
with more than 50 choices.

### Why this is wrong

Long ABCD-style lists become their own search task and are not realistic for a
short-answer CAD reasoning benchmark. They also make the prompt expensive and
hard to inspect manually.

### Fix

Public candidate labels are capped at `DEFAULT_MAX_CANDIDATE_LABELS = 7`.
Validation rejects public candidate-label rows above that cap.

### Evidence

Current release artifact candidate-label distribution:

```text
{2: 590, 3: 383, 4: 596, 5: 236, 6: 331, 7: 3014}
over_7_labels: 0
```

## Bug 3: Ranked Candidate Caps Could Contradict The Prompt

### Example malformed row

Row:
`row:graph:src_5ca05f6a3542ab35:synth:v4:parameterized_kernel_edge_selector_count_rank`

The prompt asks for the 4th selector by ascending selected-entity count, but the
visible choices after capping had these selected counts:

```text
G: 20
A: 30
B: 57
C: 60
D: 12  <- gold
E: 12
F: 12
```

If the model orders the visible choices by `selected_count`, the 4th visible
score is `20`, not the gold score `12`.

### Why this is wrong

The resolver ranks over the full pre-final candidate set. If the public bounded
choice list hides enough tied or preceding candidates, the visible list no
longer matches the ranking instruction.

### Fix

The candidate cap now preserves tied rank buckets. For `rank_asc`/`rank_desc`,
the visible list must include enough candidates before/inside the rank bucket
that the requested rank still has the same score, and it must include the gold
tied candidate. If that cannot fit within the public cap, the sampler does not
pretend an arbitrary distractor list is valid.

### Evidence

Regression coverage:

```text
test_candidate_label_rank_choices_preserve_tied_rank_bucket
```

Full rewritten release semantic QA:

```text
semantic_issues: 0
```

## Bug 4: Selector-Expression Choices Collapsed To Duplicates

### Example malformed row

Row:
`row:graph:src_b956c385e28ae807:synth:parameterized_kernel_face_selector_count_rank`

Malformed choices:

```text
A: `part.faces()`
B: `part.faces()`
```

### Why this is wrong

Both choices render identically, so the prompt asks the model to choose between
indistinguishable public answers. This happened when multiple snapshot selectors
shared the same source-level expression.

### Fix

Ranked selector tasks fall back to descriptive candidate labels instead of
selector-expression choices. Descriptions include selection type, selected count,
and relevant selection geometry measurements.

## Bug 5: Reassigned Source Variables Made Text Answers Ambiguous

### Example malformed row

Row:
`row:graph:src_b956c385e28ae807:synth:parameterized_feature_extreme`

Malformed answer:

```text
part
```

The source script assigns `part = ...` seven times.

### Why this is wrong

Returning `part` does not identify which feature or operation is selected when
the variable is reassigned repeatedly.

### Fix

If a source-ref answer is not publicly unambiguous, the resolver falls back to
candidate labels. Source-like candidate descriptions include source variable,
source line, operation, and query-relevant measurements.

### Evidence

Release artifact QA:

```text
ambiguous_source_ref_rows: 0
```

## Bug 6: Region References Mentioned Zero Volume As Evidence

### Example malformed row

Row:
`row:graph:src_0ea1428289f29a30:synth:v2:parameterized_path_segment_reference_entity_distance_rank`

Malformed clue:

```text
Use as the reference the added-material region with volume 0.0 and centroid coordinates (89.0, 0.0, -78.0).
```

### Why this is wrong

For these region-reference rows, `volume 0.0` is not useful public evidence and
looks like a broken geometry measurement. The centroid coordinates already
identify the reference anchor.

### Fix

Region reference templates now omit volume and describe the reference by
centroid or bounding-box center coordinates.

### Evidence

After rerendering the affected release rows:

```text
zero_volume_region_reference: 0
```

## Bug 7: Near-Zero Metric Values Rounded To `0`

### Example malformed pattern

Source-like candidate labels could show several centroid values as:

```text
centroid y 0
```

even when the resolver was distinguishing tiny nonzero values such as
`1.427843e-14`.

### Why this is wrong

The visible prompt looked tied, so the tie-break instruction could appear to
select a different candidate than the resolver-selected gold.

### Fix

Source-like candidate metric formatting now uses scientific notation when a
nonzero value would otherwise round to `0` at the normal display precision.

## Bug 8: Kernel Floating-Point Noise Could Override Visible Tie-Breaks

### Example malformed row

Row:
`row:graph:src_a674edb7b5a597b0:synth:v3:parameterized_edge_spatial_relation_tie_break_extreme`

Malformed visible choices:

```text
A: midpoint (57.5, 0, -100); length 5
B: midpoint (64, -2.5, -100); length 13
C: midpoint (70.5, 0, -100); length 5
```

Malformed gold answer:

```text
C
```

The prompt said to choose the greatest midpoint Z coordinate, then break ties by
greatest edge length. All visible midpoint Z values are `-100`, so the public
answer should be `B`, not `C`.

### Why this is wrong

The resolver compared raw kernel floats for primary `argmax`/`argmin`. In this
row, `C` had raw midpoint Z `-99.99999999999997` while the other visible choices
had `-100.0`. That difference is invisible at the public prompt precision and
should not beat the stated tie-break.

### Fix

Primary metric aggregation now uses the same `VALUE_MATCH_TOLERANCE` already
used for ranked aggregation and reference-distance aggregation. Display-equivalent
floating-point noise leaves a tied candidate set, then the explicit tie-break
aggregation resolves it.

### Evidence

The row above now resolves to:

```text
gold: B
trace_final: edge:kernel:snapshot_wp18_edges:3bae1c84184e8e95
```

Regression coverage:

```text
test_candidate_label_extreme_uses_tie_break_for_float_noise
```

## Bug 9: Coordinate Answer Exports Used List-Like Text

### Example malformed answer text

Coordinate rows instruct the model to answer with a tuple:

```text
Return exactly one coordinate tuple of the vertex, for example `(0, 1, 3)`.
```

But export helpers that used `str(row["gold_answer"])` could emit list-like
assistant answers:

```text
[-47.584951, 0, -127.964585]
```

### Why this is wrong

The parser accepts both list and tuple syntax, but the public prompt asks for a
coordinate tuple. SFT, few-shot examples, reasoning traces, tool-assisted
responses, and oracle responses should train/evaluate the requested public
answer syntax, not an incidental Python/list representation.

### Fix

Gold-answer text now goes through a shared public answer renderer. Coordinate
answers render as tuple text, including when the parquet column stores a
JSON-encoded coordinate internally.

Validation now also rejects malformed public answer contracts for these cases:

```text
coordinate rows without a coordinate-tuple return instruction
coordinate rows whose gold answer is not a 3-number coordinate
source-variable text rows whose gold answer is not assigned in the shown script
source-variable text rows whose gold answer is reassigned in the shown script
```

Current decoded examples from `release_10k/rows.parquet` now render as:

```text
(-47.584951, 0, -127.964585)
(98, 0, 12)
(-68, 27, -22)
```

Regression coverage:

```text
test_sft_exports_coordinate_answers_as_prompt_tuple_text
test_tool_assisted_responses_render_coordinate_tuple_answers
test_request_exports_render_coordinate_tuple_examples_and_oracle_answers
test_validation_rejects_invalid_coordinate_public_answer
test_validation_rejects_coordinate_answer_without_tuple_instruction
test_validation_rejects_missing_source_variable_gold_answer
test_validation_rejects_reassigned_source_variable_gold_answer
```

## Verification Checklist

The rewritten release artifact has passed:

```text
rows: 10000
validate_rows(..., release=True): valid
entity_id_instruction: 0
colon_gold: 0
over_7_labels: 0
ambiguous_source_ref_rows: 0
duplicate_prompt_groups: 0
zero_volume_region_reference: 0
semantic_checked: 4997
semantic_uncheckable: {'missing_metric': 150, 'missing_tie_metric': 3}
semantic_issues: 0
```

## Remaining Benchmark Gates

The default `release-candidate` verifier passes:

```text
valid_for_release: true
blocking_gates: []
preview_evidence: true
```

Preview evidence has been generated for strict benchmark review:

```text
PREVIEW.md
preview_evidence.json
PREVIEW.preview_evidence.json
preview_evidence_valid: true
```

The stricter `benchmark-release` verifier still fails the remaining
distribution/selection gates:

```text
blocking_gates:
- distinct_cad_model_coverage
- answer_entropy
- value_bearing_measurement_coverage
- cross_feature_value_bearing_coverage
- parameter_balance
```

Concrete strict-gate numbers:

```text
distinct_cad_model_count: 900
minimum_distinct_cad_model_count: 1000
unique_answer_count: 2295
minimum_unique_answer_count: 1000
answer_entropy_bits: 6.940893592407393
minimum_answer_entropy_bits: 8.0
value_bearing_measurement_count: 3666
value_bearing_measurement_share: 0.3666
minimum_value_bearing_measurement_share: 0.15
maximum_value_bearing_measurement_share: 0.3
cross_feature_value_bearing_count: 332
cross_feature_value_bearing_share: 0.0332
minimum_cross_feature_value_bearing_share: 0.05
parameter_balance_valid: false
```

Answer-entropy breakdown:

```text
candidate_label rows: 5150
candidate_label unique answers: 7
candidate_label entropy_bits: 2.7273
candidate_label top answers: B=1081, A=1033, C=852, D=731, E=544, G=474, F=435

coordinate rows: 2639
coordinate unique answers: 2215
coordinate entropy_bits: 11.0074

text/source_ref rows: 2211
text/source_ref unique answers: 73
text/source_ref entropy_bits: 5.2005
```

This explains why total answer entropy fails despite having more than the
minimum unique answer count: the public target for candidate-choice questions is
intentionally a small label alphabet, and source-ref answers intentionally reuse
visible source variable names.

The verifier now emits this as structured `answer_format_counts` and
`answer_entropy_by_format` fields in `release_balance`.

Value-bearing/cross-feature breakdown:

```text
prompt_families: 60
value_bearing_families: 22
cross_feature_value_bearing_families: 2
```

The release row selection is nearly uniform by prompt family. This makes all 22
value-bearing families contribute 36.66% of rows, above the strict 30% cap, while
the two cross-feature families contribute only 3.32%, below the strict 5% floor.
This is a selection/balancing issue, not a malformed-row issue.

The verifier now emits this as structured
`value_bearing_prompt_family_counts` and
`cross_feature_value_bearing_prompt_family_counts` fields in
`release_balance`.

Parameter-balance breakdown:

```text
parameter_balance_violations: 96
parameter_value_dominates: 86
axis_or_direction_undercovered: 10
top_violating_dimensions:
- rank_direction: 19
- aggregation_metric: 17
- narrowing_predicate_sequence: 14
- aggregation_rank: 8
- equal_measurement_metric: 7
- comparison_operator: 7
- narrowing_mode: 6
- clause_axis: 5
```

Several dominance violations are structural under current families. Examples:
`parameterized_equal_path_segment_metric_extreme` has
`aggregation_metric=midpoint_distance_to_origin` for 100% of rows, and
kernel selector-count families have `narrowing_mode=related_metric_compare` for
nearly all rows. Several undercoverage violations also cite relation values with
no current support in the generated distribution, such as `coaxial_with`.

Generated-pool strict-gate feasibility can be reproduced with:

```bash
uv run python tools/analyze_release_gate_feasibility.py \
  --dataset-stream runs/current_cadevolve1000_10k_regen_20260613/dataset_stream \
  --graph-dir runs/current_cadevolve1000_10k_regen_20260613/graph/graphs \
  --analyze-missing-query-counts \
  --simulate-release-balance \
  --out /tmp/cadqa_release_gate_feasibility.json
```

For a cheaper smoke check, add `--max-missing-query-analysis N`; source
coverage and node-type counts remain complete, while query-count synthesis is
limited to the first `N` missing sources.

Current generated-pool feasibility summary:

```text
pool_row_count: 168987
pool_source_count: 906
graph_source_count: 1000
graph_sources_missing_generated_rows_count: 94
missing_source_query_count_distribution: {"0": 94}
pool_family_count: 60
families_with_at_least_minimum_rows: 60
family_min_available_rows: 272
value_bearing_pool_row_count: 74830
cross_feature_pool_row_count: 33575
minimum_cross_feature_rows_for_release: 500
maximum_value_bearing_rows_for_release: 3000
parameter_balance_full_pool_valid: false
parameter_balance_full_pool_violation_count: 88
```

This means the generated row pool has enough rows to rebalance value-bearing and
cross-feature shares, but it still cannot satisfy the distinct-source gate and
it does not satisfy parameter balance even before release selection.

Generated-pool coverage check:

```text
graph_sources: 1000
sources_with_successful_generated_rows: 906
sources_in_release_10k: 900
sources_with_no_successful_generated_rows: 94
missing_source_current_query_count_distribution: {0: 94}
```

The 94 missing sources have ontology graphs, but the current query-family
synthesis produces zero viable queries for each of them. Therefore the
`distinct_cad_model_coverage` failure cannot be fixed by merely reselecting rows
from the current generated pool.

The missing-source graphs are not empty graph-build failures. Aggregate evidence
over the 94 missing sources includes:

```text
source nodes: 94
parameter nodes: 4293
operation nodes: 3402
feature nodes: 3402
workplane nodes: 810
profile nodes: 512
centroid nodes: 419
solid nodes: 274
sketch nodes: 202
material_region nodes: 189
selector nodes: 154
void_region nodes: 22
face nodes: 35
edge nodes: 6
vertex nodes: 3
origin nodes: 3
```

The common pattern is usable operation/profile/region evidence but too little
kernel-backed primitive geometry, plus many repeated or non-unique measurements.
Current release query families lean on unique extremes/ranks and kernel-backed
face/edge/vertex evidence, so these graphs do not yield release queries.

The public-answer fixes are complete. The remaining failures are release-scale
distribution/evidence gates, not row-level public contract bugs.

### Fix: sampled-parameter cap was not wired into release balancing

Bug:

`_cap_sampled_parameter_share_rows` existed and had unit coverage, but
`_cap_release_balance_rows` did not call it. That meant benchmark release export
could cap prompt-family/template/value-bearing slices while still leaving
sampled parameter values over the strict 35% per-family dominance limit.

Example failure mode:

```text
parameterized family rows:
aggregation_axis=x: 14 rows
aggregation_axis=y: 3 rows
aggregation_axis=z: 3 rows

max_parameter_value_share: 0.35
```

The standalone sampled-parameter cap can reduce the `x` dominance while
preserving nonzero `y`/`z` coverage, but the release path previously skipped it.

Fix:

When `profile.enforce_parameter_balance` is enabled, release balancing now calls
`_cap_sampled_parameter_share_rows` inside the capping loop. The loop can then
rerun the other share caps after parameter drops, so value/cross-feature/family
constraints still get a chance to recover if a parameter drop changes the
composition.

Regression coverage:

```text
test_release_balance_wires_sampled_parameter_cap_when_enforced
test_release_export_caps_overrepresented_sampled_parameter_values
```

### Fix: sampled-parameter cap over-dropped correlated dimensions

Bug:

The sampled-parameter cap evaluated each dimension against the original family
rows even after selecting rows to drop. Correlated dimensions could therefore
double-count the same collapse. For example, rows with
`aggregation_axis=x` usually also have `aggregation_metric=centroid_x`; after
dropping enough `x` rows, the cap still evaluated `centroid_x` against the
pre-drop counts and dropped the remaining `x` rows too.

Malformed balancing behavior:

```text
input aggregation_axis counts: x=14, y=3, z=3
old post-cap counts: x=0, y=3, z=3
```

That satisfies the max-share rule numerically, but it destroys representation
for the overrepresented value instead of reducing it to the allowed share.

Fix:

The cap now recomputes each dimension/value group from the still-kept family
rows after every drop batch. The same fixture now keeps a balanced distribution:

```text
new post-cap counts: x=3, y=3, z=3
```

Regression coverage:

```text
test_release_export_caps_overrepresented_sampled_parameter_values
test_release_balance_wires_sampled_parameter_cap_when_enforced
test_release_feasibility_simulates_release_balance_caps
```

### Fix: axis/direction floor applied to non-axis expected values

Bug:

`min_axis_direction_parameter_share` was applied to any manifest
`expected_values` entry. That made relation/rank/selector expected-value lists
use the same 20% per-value floor intended for axis/direction dimensions.

Malformed gate example:

```text
clause_relation expected values:
adjacent_to, parallel_to, perpendicular_to, longer_than, shorter_than,
intersects, coaxial_with, opposite_to, same_length_as

old interpretation:
each relation must be at least 20% of the family
```

That is mathematically impossible for more than five expected values, and it is
not what the benchmark contract says. The spec gate is about sampled
axis/direction values.

Fix:

`parameter_balance_report` now computes expected-value shares for all configured
expected values, but only applies `min_axis_direction_parameter_share` to:

```text
aggregation_axis
clause_axis
extremum_direction
tie_break_axis
tie_break_direction
rank_direction
```

Current measured effect on the generated pool:

```text
full generated pool parameter violations:
before: 142
after: 88

simulated 10K post-balance parameter violations:
before: 185
after: 131
```

The strict parameter-balance gate still does not pass. The remaining failures
are no longer caused by impossible non-axis expected-value floors; they are
dominance and axis/direction coverage failures under current generated
distribution and selector policy.

The feasibility tool now includes compact top-violation fields:

```text
parameter_balance_full_pool_top_violations
simulated_release_balance.parameter_balance_top_violations
simulated_release_balance.parameter_balance_violation_classification_counts
simulated_release_balance.parameter_balance_violation_classification_reason_counts
simulated_release_balance.parameter_balance_top_violation_classification_counts
simulated_release_balance.parameter_balance_top_violation_pool_context
```

The pool-context field compares each top simulated violation against the full
generated pool for the same family/dimension. This separates selection-induced
problems from pool-level generation limits.

Example from the current generated pool:

```text
family: parameterized_contained_endpoint_metric_extreme
dimension: aggregation_metric
value: distance_to_origin

full pool: 831 / 2920 = 28.46%
simulated 10K selection: 56 / 100 = 56.0%
maximum allowed largest share: 35%
```

That specific violation is not a generated-pool impossibility; the current
selector made a balanced-enough pool slice unbalanced in the final 10K sample.
Other examples remain pool-level, such as `clause_relation=endpoint_of` at 50%
both before and after selection. Use the context fields to decide whether the
next fix should be a selector-balancing algorithm change or family-specific
manifest/query-policy adjustment.

The feasibility tool also estimates per-violation replacement capacity:

```text
simulated_release_balance.parameter_balance_violation_individual_replacement_capacity_counts
simulated_release_balance.parameter_balance_violation_classification_replacement_capacity_counts
simulated_release_balance.parameter_balance_top_violation_individual_replacement_capacity_counts
```

This is an independent per-violation estimate, not proof that all replacements
can be made simultaneously while preserving every other release gate.

Current top-25 simulated violation classification:

```text
selection_regressed: 17
pool_already_violates: 8
```

Current all-violation simulated classification:

```text
selection_regressed: 60
pool_already_violates: 67
pool_undercovered: 3
mixed_pool_and_selection: 1
```

By reason:

```text
selection_regressed:axis_or_direction_undercovered: 40
selection_regressed:parameter_value_dominates: 20
pool_already_violates:parameter_value_dominates: 67
pool_undercovered:axis_or_direction_undercovered: 3
mixed_pool_and_selection:axis_or_direction_undercovered: 1
```

Current individual replacement-capacity estimate:

```text
appears_individually_fixable: 120
not_individually_fixable: 11
```

By classification:

```text
selection_regressed:appears_individually_fixable: 60
pool_already_violates:appears_individually_fixable: 56
pool_already_violates:not_individually_fixable: 11
pool_undercovered:appears_individually_fixable: 3
mixed_pool_and_selection:appears_individually_fixable: 1
```

Interpretation:

- `selection_regressed` means the generated pool has enough diversity for the
  cited value/dimension, but the simulated 10K selector lost it.
- `pool_already_violates` means the full generated pool is skewed for that
  family/dimension. It may still be individually fixable by selecting a more
  balanced subset if enough alternative rows exist.
- `not_individually_fixable` is the stronger signal that a selector-only change
  probably cannot fix the cited violation.

Regression coverage:

```text
test_parameter_balance_min_expected_share_only_applies_to_axis_direction_dimensions
```

### Diagnostic: same-family parameter repair is not enough by itself

Bug:

The feasibility tool could classify parameter-balance violations and estimate
independent replacement capacity, but it did not test whether simple replacement
swaps could actually improve the simulated 10K release while preserving the
other release gates. A first diagnostic implementation also recomputed the
family manifest and sampled-parameter normalization repeatedly, making the
bounded dry run too slow for interactive QA.

Fix:

The feasibility tool now has an opt-in dry-run repair simulation:

```bash
uv run python tools/analyze_release_gate_feasibility.py \
  --dataset-stream runs/current_cadevolve1000_10k_regen_20260613/dataset_stream \
  --simulate-release-balance \
  --simulate-parameter-repair \
  --max-parameter-repair-swaps 50 \
  --out /tmp/cadqa_release_gate_feasibility_repair50.json
```

The dry run performs same-family replacements only. That preserves row count and
prompt-family distribution, then rechecks prompt-template, value-bearing, and
cross-feature gates after the swaps. It also caches the loaded family manifest
and private sampled-parameter metadata on rows so repeated diagnostic reports do
not spend most of their time reparsing YAML/query metadata.

Current 50-swap result on the simulated 10K release:

```text
input_selected_row_count: 10000
output_row_count: 10000
swap_count: 50
stopped_reason: iteration_limit
attempted_violation_count: 72
successful_violation_count: 50
failed_violation_count: 22
swap_reason_counts:
  axis_or_direction_undercovered: 16
  parameter_value_dominates: 34

pre_parameter_balance_valid: false
pre_parameter_balance_violation_count: 131
pre_parameter_balance_reason_counts:
  axis_or_direction_undercovered: 44
  parameter_value_dominates: 87

post_parameter_balance_valid: false
post_parameter_balance_violation_count: 128
post_parameter_balance_reason_counts:
  axis_or_direction_undercovered: 41
  parameter_value_dominates: 87

post_passes_prompt_family_balance: true
post_passes_prompt_template_balance: true
post_passes_value_bearing_measurement_coverage: true
post_value_bearing_measurement_share: 0.247
post_passes_cross_feature_value_bearing_coverage: true
post_cross_feature_value_bearing_share: 0.05
```

Interpretation:

This is not a sufficient production repair strategy. It proves that same-family
swaps can preserve the other gates, but 50 swaps only reduce parameter-balance
violations from 131 to 128. The remaining parameter issue needs release
selection to optimize parameter diversity directly, or family/query changes that
make the generated pool less skewed before selection.

Regression coverage:

```text
test_parameter_repair_simulation_runs_same_family_swaps
```

### QA note: duplicate visible candidate descriptions

Manual prompt inspection found candidate-label rows where two or more distractor
choices have identical rendered descriptions. This happens mostly for symmetric
kernel faces/edges where the currently rendered public metrics do not separate
every visible candidate.

Current audit over `release_10k/rows.parquet`:

```text
candidate_label_rows: 5150
rows_with_duplicate_visible_candidate_text: 1326
rows_where_gold_text_is_duplicated: 0
```

Top affected families:

```text
parameterized_kernel_face_rank: 116
parameterized_face_spatial_relation_rank: 115
parameterized_edge_spatial_relation_rank: 106
parameterized_kernel_edge_rank: 105
parameterized_face_spatial_relation_chain_rank: 93
parameterized_equal_edge_metric_rank: 90
parameterized_equal_face_metric_rank: 84
```

Interpretation:

This is currently a noise issue, not a confirmed malformed-gold issue, because
the gold label is never part of a duplicated visible-description group in the
current release. Validation now treats duplicated gold candidate descriptions as
a hard public-answer error: if a future candidate-label row has the gold label in
a duplicated description group, the public answer is not recoverable without
extra evidence or an explicit tie-break. The same validation path also rejects
candidate-label rows whose rendered prompt has no candidate list, or whose gold
label is not present in the rendered candidate list.

Regression coverage:

```text
test_validation_rejects_duplicated_gold_candidate_description
test_validation_rejects_missing_rendered_candidate_labels
test_validation_rejects_unrendered_gold_candidate_label
```

Current next-step classification:

```text
requires new usable graph/query coverage, then regeneration or backfill:
- distinct_cad_model_coverage

requires selection/balancing work over generated rows:
- parameter_balance

now feasible in simulated release balancing after selector fixes:
- value_bearing_measurement_coverage
- cross_feature_value_bearing_coverage

requires a benchmark-policy decision:
- answer_entropy, because public candidate-label answers intentionally collapse
  many entity-ID answers to labels A-G; the verifier now reports this as
  `source_scoped_for_entity_id_raw_public_answer_otherwise`
```

The current production parameter-balance cap is drop-only: it removes
overrepresented rows when doing so preserves release floors, but it does not
swap in underrepresented alternatives from the generated pool. The remaining
parameter-balance failures therefore need either a coordinated swap-based
selector/optimizer, or query-family/generation changes that make the pool less
skewed before selection. A small cap-order tweak is unlikely to be sufficient.
