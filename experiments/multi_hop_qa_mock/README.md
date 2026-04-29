# Multi-Hop QA Experiments

This directory contains lightweight design probes for the rule-based
non-feature Multi-Hop CAD-QA architecture. It no longer contains the earlier
LLM translator, OpenRouter request, mock solver, or mock judge artifacts.

The retained experiments ask two planning questions:

```text
1. What does the full ontology clue vocabulary look like in checklist form?
2. Across real CadEvolve scripts, which non-feature entities and relations
   appear often enough to prioritize for the ontology/verifier implementation?
```

## Files

- `build_comprehensive_ontology_preview.py`: deterministic non-LLM preview
  generator for ontology node types, relation types, parameter entry/exit cases,
  and candidate-count gates.
- `preview/comprehensive_ontology_preview.md`: human-readable comprehensive
  ontology clue preview.
- `preview/comprehensive_ontology_preview.json`: machine-readable
  comprehensive ontology clue preview.
- `survey_non_feature_relation_gaps.py`: statically samples CadEvolve source
  scripts, chooses mixed non-feature entities, infers relation opportunities,
  and classifies them as current, spec-only, or missing-but-necessary.
- `preview/non_feature_relation_gap_survey.md`: human-readable survey report.
- `preview/non_feature_relation_gap_survey.json`: machine-readable survey
  report.

## Run

Build the comprehensive ontology clue preview:

```bash
uv run python experiments/multi_hop_qa_mock/build_comprehensive_ontology_preview.py \
  --output-dir experiments/multi_hop_qa_mock/preview
```

Build the non-feature relation gap survey:

```bash
uv run python experiments/multi_hop_qa_mock/survey_non_feature_relation_gaps.py \
  --sources-jsonl data/cadqa_cadevolve_rc_10/sources.jsonl \
  --output-dir experiments/multi_hop_qa_mock/preview \
  --source-count 10 \
  --entities-per-source 5
```

## Interpretation

This is not a benchmark result and does not claim the relations are production
labels. It is a planning probe used to prioritize implementation work.

The current priority matrix is captured in
[`docs/multi-hop-qa-architecture.md`](../../docs/multi-hop-qa-architecture.md):

- P0: profile geometry, workplane frames, profile application effects,
  projection paths, and measurement-scope-aware templates.
- P1: stable selector face IDs, same-face joins, sketch centers, path tangents,
  and nearest path points.
- P2: material regions, void regions, adjacency/opposite relations, and region
  intersection/containment.
