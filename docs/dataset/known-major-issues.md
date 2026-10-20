# Known major dataset issues — 2026-10-20

**Status:** active, 2026-10-20. This is the issue register for the regenerated
CAD-QA dataset. It records defects and limitations that affect paper, training,
and release claims. It is not a pipeline specification; the generation pipeline
lives in `pipeline/`.

## Scope

The counts below were verified on 2026-10-20 from the Parquet files under
`runs/`, which is local and gitignored.

| Data file | Path | CAD-QA dataset rows |
|---|---|---:|
| Generated pool | `runs/regen_1300_traced_20261019/dataset_shards` | 218,779 |
| Bounded pool | `runs/regen_1300_traced_20261019/dataset_stream_bounded` | 78,988 |
| Release | `runs/regen_1300_traced_20261019/release_10k` | 10,000 |
| Resplit | `runs/regen_1300_traced_20261019/release_10k_resplit_20261020` | 10,000 |

The release is the 2026-10-19 regeneration recorded in
`../experiments/2026-10-19-cadqa-regen-1300.md`. The resplit is not recorded
there; this document is its current record.

## Release summary

| Property | Value |
|---|---|
| Answer formats | `candidate_label` 4,300; `coordinate` 3,569; `text` 2,131 |
| Reasoning hop count | 2: 552; 3: 3,111; 4: 5,409; 5: 928 |
| Distinct CAD models | 980 |
| Release families generated | 42 of 59 |
| Evidence tier | `source_static_or_analytic` on all 10,000 rows |
| `valid_for_release` | false |
| Split in `release_10k` | train 9,741; validation 54; test 205 |
| Split in `release_10k_resplit_20261020` | train 7,000; validation 1,500; test 1,500 |

## Issue register

### M1 — The answer formats are narrower than the paper claims

**Status:** verified; open.

43.0% of rows are `candidate_label`, 35.7% are `coordinate`, and 21.3% are
`text`. The intended set has eight answer formats; `number`, `integer`,
`boolean`, `bbox`, and `json` have zero rows in the release. The full pool is
similar: `candidate_label` 122,287, `coordinate` 55,352, `text` 39,048, and
`number` 2,092, with the other four at zero (`answer-formats.md`).

The paper (`../paper/CA2_Riabov_final.md`) describes seven answer formats. An
examiner who opens the dataset sees three, and 64.3% of the release answers with
a source variable or a candidate label.

**Impact:** the paper's claim does not match the data. This is the largest
credibility risk, independent of the six blocking gates.

**Disposition:** scope the paper to the three instantiated answer formats and
report the full intended set as designed but not instantiated. Add a numeric
answer family only if time remains after the chance and split fixes.

### M2 — The multiple-choice answer distribution creates a 10% chance floor

**Status:** verified; open; highest-priority data defect.

43% of rows are `candidate_label`. The expected random-guess accuracy over the
release is 10.4%, computed as the sum over candidate-label rows of
1 / (presented candidate count), divided by 10,000. Answering `"A"` on every
candidate-label row scores 10.1%. The planned base LLM model rate is about 10%,
so the raw headline is at chance without correction.

Two mechanisms cause this:

- `dataset/query/answers.py::_stable_index` uses `sum(ord(char)) % count`. The
  sum of character codes is not uniform, and the gold label is skewed: `A`
  1,008, `B` 1,063, `C` 784, `D` 579, `E` 380, `F` 295, `G` 191.
- `dataset/query/answers.py::_bounded_candidate_ids` always places the gold
  entity first and permits a presented candidate count as low as 2. Presented
  counts are 2: 519 rows, 3: 527, 4: 995, 5: 374, 6: 487, 7: 1,398.

**Impact:** an examiner can argue that a 10% base rate is chance. A constant
`"A"` answer is competitive with the planned base LLM model.

**Disposition:** report chance-corrected accuracy plus random-guess and
constant-answer baselines, per answer format and presented candidate count; the
PRD already requires chance correction. Then enforce a minimum presented
candidate count and balance label positions, and re-run query synthesis,
materialization, and release export from the cached CAD ontology graphs and
CadQuery program operation traces. Do not retrace or rewrite the
dataset-generation code.

### M3 — Answer entropy is below the benchmark-release threshold

**Status:** verified; accepted for internal use.

Answer entropy is 7.50 bits against a minimum of 8.0. The current answer-format
mix caps entropy at 7.91 bits. Some 100-row families have only 6 or 7 unique
answers because the answer identity is a candidate label; for example
`parameterized_edge_spatial_relation_chain_extreme` and
`parameterized_edge_spatial_relation_chain_rank`.

**Impact:** a blocking gate for a public benchmark release. It does not block an
internal SFT or evaluation experiment.

**Disposition:** accept as a known limitation for the thesis; revisit with the
M2 candidate-breadth fix and, if needed, a numeric answer family.

### M4 — The default SFT export includes validation and test rows

**Status:** verified; open; fix before any reported training result.

`release_10k/sft/answer_sft.jsonl` contains 10,000 rows and only a `messages`
field; it has no split field. `dataset/release/sft.py::default_training_rows`
filters on geometry-critical and calibration status, not on split. The
regeneration record therefore reports 10,000 default SFT rows from a release
whose `release_10k` split has 9,741 train, 54 validation, and 205 test rows.

**Impact:** training on the default file and evaluating on the release split
puts validation and test rows in training. The contamination is 259 rows under
the original split and 3,000 rows under the resplit.

**Disposition:** export SFT from the train split only, or train on the full
release and score a separate immutable confirmation batch drawn from the
remaining bounded pool. Record the chosen boundary before the final run.

### M5 — The original split is too small for the planned analysis

**Status:** verified; resplit exists but is undocumented and not
family-disjoint.

The `release_10k` split is 9,741 train / 54 validation / 205 test. The
evaluation plan's power table assumes 1,159 validation rows and 708 test rows
(`../train-and-eval/evaluation/plan.md`). The validation split is 21 times
smaller than planned, which blocks the dose-response analysis (H4) and the
pre-registered H2 power calculation.

`release_10k_resplit_20261020` re-splits the same 10,000 rows into 7,000 train /
1,500 validation / 1,500 test. No CadQuery program and no split group crosses
splits: 515 / 231 / 234 distinct CAD models and 136 / 29 / 29 split groups. The
directory has no `split_audit.json`, `leakage_audit.json`, or
`dataset_report.json`.

The resplit is not family-disjoint: all 16 relation families and 811
`prompt_template_id` values appear in more than one split. It is
CadQuery-program-disjoint and split-group-disjoint, which is the stronger
leakage control for the thesis, but it does not supply the family-disjoint
confirmation batch named in the evaluation plan.

**Impact:** the resplit is usable for a thesis evaluation with 1,500 test rows,
but its provenance and family-disjointness must be stated.

**Disposition:** rerun the split and leakage audits on the resplit, record the
data file and its checksums, and state the disjointness property in the paper.
Do not use the 54-row validation split for training decisions.

### M6 — Six blocking gates keep the release out of benchmark-release status

**Status:** verified; accepted for internal use.

| Blocking gate | Result | Requirement |
|---|---|---|
| `distinct_cad_model_coverage` | 980 CAD models | 1,000 |
| `prompt_family_balance` | largest family 10.43% | at most 10% |
| `answer_entropy` | 7.50 bits | 8.0 bits |
| `cross_feature_value_bearing_coverage` | 488 rows | 500 rows |
| `intended_family_coverage` | 42 families | 59 |
| `parameter_balance` | 112 violations | 0 |

Root causes are recorded in the regeneration record: 15 of the 17 missing
release families fail `missing_clue_clause_map`;
`parameterized_void_region_volume` fails `geometry_first_prompt_policy`;
`answer_entropy` is structurally capped by the answer-format mix; and CAD model
coverage is 20 short because release balance capping drops representatives.

**Impact:** the release is not a public benchmark. It is accepted for internal
SFT and evaluation experiments.

**Disposition:** report the blocking gates as limitations. Fix only if a public
benchmark release remains a goal after the thesis.

### M7 — The paper claims more than the release contains

**Status:** verified; open.

The paper claims seven answer formats and reasoning depths up to ten hops. The
release has three answer formats and a reasoning hop count of 2 to 5. The
abstract says "We evaluate..." but the manuscript has no results yet.

**Impact:** this is the fastest way to lose marks: the claim contradicts the
data.

**Disposition:** rewrite the claims to the instantiated set, add an explicit
limitations paragraph, and add the results. The methodology can still describe
the intended taxonomy, clearly separated from the instantiated subset.

### M8 — The measurement scopes are skewed toward entity geometry

**Status:** verified; open as a paper-framing issue.

Across the release, `entity_geometry` appears on 6,748 rows,
`relation_metric` on 4,636, `snapshot_state` on 1,412, and
`feature_application_effect` on 506. The 506 feature-effect rows (volume and
topology deltas) are answered as `candidate_label` (407) or `text` (99), never
as `number`.

The paper promises volume and span computation. The release computes those
quantities to rank or select an entity, but it does not ask for the quantity as
the public answer.

**Impact:** an examiner can reasonably say the benchmark measures entity
resolution, not quantitative geometry.

**Disposition:** either reframe the contribution as entity-grounded multi-hop
geometry reasoning, or add one numeric answer family. Do not claim numeric
volume or span answers until they exist.

### M9 — The evidence-tier label is uniform

**Status:** verified; limitation.

All 10,000 release rows have `evidence_tier = source_static_or_analytic`. The
release has no row in a stronger kernel-backed tier. Kernel-derived relation
families are present (`has_kernel_stable_edge_id` 3,016 rows,
`has_kernel_stable_vertex_id` 1,298 rows), but the tier label does not
distinguish them.

**Impact:** the release cannot support a claim that every answer is backed by a
kernel measurement. The paper should not imply that it is.

**Disposition:** describe the tier accurately, and sample-audit gold answers
against the CadQuery program operation trace before the final result.

## What the dataset is sufficient for

| Use | Sufficient? | Condition |
|---|---|---|
| Internal SFT | yes | train on the train split only (M4) |
| H3 transfer to BenchCAD | yes | report the three-format scope (M1) |
| H4 dose-response | yes, with the resplit | use 1,500 validation / 1,500 test and state the family-disjointness gap (M5) |
| P0 H2 hard-slice result | yes, with chance correction | report chance-corrected accuracy and the 10.4% chance floor (M2) |
| Public benchmark-release claim | no | six blocking gates (M6) |
| Paper claims as written on 2026-10-20 | no | claims exceed the release (M1, M7) |

## Recommended order of work

1. Fix M4: export SFT from the train split only.
2. Fix M2: report the chance floor and add the candidate-breadth and
   label-balance changes; re-run from cached CAD ontology graphs.
3. Adopt M5: run the split and leakage audits on the resplit and record it.
4. Fix M7 and M8 in the paper: claim only what the release contains.
5. Add one numeric answer family only if steps 1-4 are complete and time
   remains.

A ground-up rewrite is not required for any item above. The limiting defects are
localized to answer-format assignment, release selection, SFT export, and paper
wording.

## How to reproduce the counts

```bash
uv run python - <<'PY'
import collections
import json

import pyarrow.parquet as pq

path = "runs/regen_1300_traced_20261019/release_10k_resplit_20261020/rows.parquet"
rows = pq.read_table(path).to_pydict()
total = len(rows["answer_format"])

print("answer formats", collections.Counter(rows["answer_format"]))
print("reasoning hop count", collections.Counter(rows["logical_hop_count"]))
print("split", collections.Counter(rows["split"]))

candidate_counts = collections.Counter()
expected_random = 0.0
always_a = 0
for answer_format, query, gold in zip(
    rows["answer_format"], rows["query_program"], rows["gold_answer"]
):
    if answer_format != "candidate_label":
        continue
    if isinstance(query, str):
        query = json.loads(query)
    labels = ((query or {}).get("answer_spec") or {}).get("candidate_labels") or {}
    candidate_counts[len(labels)] += 1
    expected_random += 1.0 / len(labels)
    always_a += str(gold).strip('"') == "A"

print("presented candidate count", dict(sorted(candidate_counts.items())))
print("expected random-guess accuracy", round(expected_random / total, 4))
print("always-A accuracy", round(always_a / total, 4))
PY
```

## Open questions

- **Q1.** Is `release_10k_resplit_20261020` the evaluation split for the thesis,
  or should the thesis draw a fresh confirmation batch from the bounded pool?
- **Q2.** Should the minimum presented candidate count be 5 or 7? The higher
  value lowers the chance floor but removes more generated rows.
- **Q3.** Which numeric answer family should be added first: `integer` topology
  counts or `number` volume deltas?
- **Q4.** Is a public benchmark release still a goal after the thesis, or does
  the thesis close the dataset topic?

## Resolved questions

None yet.

## Related docs

- `answer-formats.md` — intended answer formats and the history of the cut
  formats.
- `pipeline/04-query-synthesis-resolver.md` — Gold query program synthesis and
  the Query verifier.
- `pipeline/06-materialize-validate-release.md` — materialization, splits, and
  release gates.
- `../experiments/2026-10-19-cadqa-regen-1300.md` — regeneration record and
  blocking gates.
- `../train-and-eval/evaluation/plan.md` — H1-H4 analysis plan and power table.
- `../paper/CA2_Riabov_final.md` — manuscript claims.
