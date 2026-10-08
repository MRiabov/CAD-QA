# 04 — Query synthesis and resolver

## Purpose

Generate deterministic Gold query programs from graph evidence, then resolve each one to
a unique gold answer backed by the Query verifier with a recorded answer candidate set trace.

## Inputs / outputs

- **Input:** **graphs** artifact (`pipeline/00-overview.md`).
- **Output artifacts:** **queries** (`queries.parquet`) and **failure_manifest**
  (`failure_manifest.parquet`), matching the contract. Each query record carries
  `graph_id`, `query` (`QueryProgram`), and `resolution` (`QueryResolution`).
- **Sidecar outputs:** `query_report.json`; in compact synthesis mode a `graphs` sidecar so
  each graph is stored once (`dataset/cli.py::_materialize_graph_lookup`).

## Requirement

Given a CAD ontology graph, synthesis must emit only deterministic queries that the
resolver can actually resolve. The resolver must apply ordered Gold query predicates, then
a primary aggregation, then an optional tie-break, and must accept a row only when the
answer candidate set is exactly one under `reject_unless_unique`. The output must include
the answer candidate set trace, the relation families and measurement scopes used, the
Query verifier status, and a gold answer in the answer contract's format. High-hop queries
must keep at least
`min_individual_clause_candidates` distractors through individual Gold query predicates so
a clue does not collapse the set to the answer.

## Current status

**exists.** Smoke queries, the synthesis layer, the family manifest, and the resolver are
present and readable (`dataset/query/synthesis.py::synthesize_graph_hop_queries`,
`dataset/query/resolver.py::smoke_queries`, `::resolve_query`,
`dataset/query/family_manifest.py`, `dataset/cli.py::_cmd_query_synthesize`). No query run was
executed while writing this doc.

## Verification

```bash
# release-oriented graph-hop synthesis (manifest release families by default)
rtk uv run cadqa query synthesize \
  --graph runs/graph/graphs.parquet \
  --out runs/query \
  --max-per-family 3

# small plumbing check that also emits calibration/review rows
rtk uv run cadqa query smoke --graph runs/graph/graphs.parquet --out runs/query_smoke
```

The focused tests are `tests/test_graph_first_pipeline.py::test_query_resolver_argmax_and_reject_unless_unique`,
`::test_query_resolver_uses_tie_break_aggregation`,
`::test_query_resolver_rank_aggregation_and_ambiguity`, and
`::test_low_and_multi_hop_smoke_queries_render_and_materialize`. The self-check command is
`rtk uv run cadqa dataset synthesis-selfcheck --out runs/synthesis_selfcheck`.

## Local decisions

### D1 — Synthesis is a bounded, deterministic family walk, not a search

- **Status:** accepted.
- **Context:** A Cartesian predicate search would explode; families must be parameterized
  but reproducible (`docs/_archive/multi-hop-qa-architecture.md`).
- **Decision:** `synthesize_graph_hop_queries` iterates declared family specs
  (`EXTREME_FAMILY_SPECS`, `RANK_FAMILY_SPECS`, `SELECTOR_COUNT_FAMILY_SPECS`,
  `EQUAL_VALUE_*`, `RELATION_*`, `FEATURE_EFFECT_DELTA_FAMILY_SPECS`, reference-distance
  specs, and `_void_region_volume_queries`) and samples viable choices deterministically
  (`dataset/query/synthesis.py::_sample_viable_choices`,
  `::_stable_choice_index`).
- **Consequences:** A graph produces a reproducible set of queries; family identities are
  parameterized rather than hard-coded axes/directions.

### D2 — The intended-family manifest controls release synthesis

- **Status:** accepted.
- **Context:** Many early families are fixed-axis/review-only and must not leak into release
  exports.
- **Decision:** `dataset/query/family_manifest.py::load_family_manifest` reads
  `dataset/query/family_specs.yaml` (176 family entries; 59 `release`). `query synthesize`
  filters to `release` families unless `--include-review-only` is given
  (`dataset/cli.py::_release_family_ids`).
- **Consequences:** Review-only/calibration families are demoted, not deleted; benchmark
  release reports block them if they appear in release rows.

### D3 — Resolver order is clauses → aggregation → tie-break

- **Status:** accepted.
- **Context:** A query is a narrowing program with a final CadQuery selector, then a tie-break.
- **Decision:** `dataset/query/resolver.py::resolve_query` applies each Gold query predicate
  in order (`_apply_clause`), then the primary aggregation (`_apply_primary_aggregation`),
  then the tie-break aggregation when the primary leaves more than one candidate
  (`_apply_metric_aggregation`). Each step is appended to the answer candidate set trace.
- **Consequences:** Materialized traces show exactly how the answer candidate set narrowed and
  where uniqueness came from.

### D4 — The answer contract (`AnswerSpec`) is the single authority for answer format

- **Status:** accepted.
- **Context:** Prompt wording, gold-answer value, public recoverability, and grading must
  agree (`docs/_archive/multi-hop-qa-architecture.md`).
- **Decision:** `dataset/query/answers.py::AnswerSpec` (mode + answer format + metric +
  candidate labels) drives prompt instruction, gold formatting
  (`format_gold_answer`), and candidate-line rendering. When a `source_ref` answer is not
  publicly unambiguous, the resolver falls back to `candidate_label`
  (`dataset/query/resolver.py::resolve_query` with
  `source_ref_is_publicly_unambiguous`).
- **Consequences:** Closed-book rows never require colon-delimited internal `entity_id`
  answers; CadQuery selector-expression choices are derived from real measured candidates
  (`answer_spec_with_selector_expression_choices`).

### D5 — Candidate labels are bounded to 7

- **Status:** accepted.
- **Context:** A public candidate list must stay short and always include the gold target
  (`specs/dataset-spec.md#answer-formats`).
- **Decision:** `DEFAULT_MAX_CANDIDATE_LABELS = 7`; `answer_spec_with_candidate_labels`
  bounds and rotates the displayed set.
- **Consequences:** Validation rejects overwide public label lists
  (`dataset/release/validate.py::public_candidate_label_issues`).

### D6 — High-hop hint: minimum distractors per Gold query predicate

- **Status:** accepted.
- **Context:** A single clue that identifies the answer makes a high-hop row fake.
- **Decision:** `QueryProgram.min_individual_clause_candidates` (default 3) causes the
  resolver to fail a hop≥3 query whose intermediate answer candidate set drops below the threshold
  (`dataset/query/resolver.py::resolve_query`).
- **Consequences:** Collapsed high-hop clues become `clue_too_narrow` failures rather than
  benchmark rows.

## Open questions

- **0/1-hop synthesis gap (documented).** `synthesis.py` floors every synthesized row at
  hop≥2, so no release 0-hop or 1-hop families exist; `difficulty_for_hops`
  (`dataset/query/difficulty.py`) is effectively dead on the synthesis path, which sets
  `difficulty` directly. The implementation status log records this as open work
  (`docs/_archive/implementation_status.md#open-work`, 2026-08-09). A clean 0→1→2→3 curriculum is not
  generatable end-to-end today.
- **Doc/code mismatch.** `specs/schema.md::QueryProgram` omits `answer_spec` and
  `aggregation_rank`, and `specs/benchmark-task-spec.md#query-requirements` describes
  aggregation only in prose. The code is authoritative.
- **`_void_region_volume_queries` special case.** This one family is hand-built rather than
  produced by a family spec; whether it should be a manifest family is `[unknown]`.

## Resolved questions

_(none yet)_

## Extra deliverables - P2

- A bounded beam-search synthesis pass (depth 1–3 narrow clauses with a small predicate
  beam) as described in `docs/_archive/multi-hop-qa-architecture.md`, replacing the current
  family-by-family walk.
