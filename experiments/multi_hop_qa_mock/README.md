# Multi-Hop QA Mock Experiment

This directory is a sandbox for seeing how the proposed Multi-Hop CAD-QA
pipeline feels before adding it to the main generator or calling an LLM.

The artifacts are intentionally small and hand-authored. They use
CadEvolve-shaped code and realistic trace/graph concepts, but the hidden graph
labels here are mock labels, not release labels.

## Files

- `mock_sources.jsonl`: realistic source-code inputs and compact mock graph
  summaries.
- `mock_hidden_queries.jsonl`: hidden answer-first query programs with
  `constraint_type` clauses, distractors, and difficulty metadata.
- `ontology_clause_packets.jsonl`: lower-level ontology/trace relation atoms
  before clue text exists.
- `compile_ontology_clues.py`: deterministic mock compiler from ontology atoms
  to canonical clue text.
- `compiled_translator_input_packets.json`: translator packets produced by the
  deterministic compiler.
- `ontology_to_translator_compilation.md`: Markdown view of raw ontology atoms
  and their compiled canonical clues.
- `build_comprehensive_ontology_preview.py`: deterministic preview generator
  for every ontology node type, relation type, and parameter entry/exit case.
- `preview/comprehensive_ontology_preview.md`: Markdown preview with selected
  CadEvolve sources, clue coverage tables, grouped prompts, and individual
  prompt previews.
- `preview/comprehensive_ontology_preview.json`: machine-readable copy of the
  same preview.
- `translator_input_packets.jsonl`: sanitized payloads for the first
  question-translator model call. These are the intended initial OpenRouter
  inputs.
- `translator_input_packets.pretty.json`: pretty-printed copy for review.
- `translator_input_packets.md`: Markdown review copy of the translator
  payloads.
- `openrouter_translator_request_template.json`: disabled-by-default request
  template for the translator call.
- `openrouter_translator_request_template.pretty.json`: pretty-printed copy for
  review.
- `openrouter_translator_request_template.md`: Markdown review copy of the
  translator request template.
- `mock_public_samples.jsonl`: rendered public questions that would be shown to
  a model.
- `mock_public_samples.pretty.json`: pretty-printed copy for review.
- `mock_hidden_queries.pretty.json`: pretty-printed copy of the hidden query
  rows for audit.
- `mock_models.json`: local mock solver and judge definitions, plus optional
  OpenRouter candidate slots for later live calls.
- `openrouter_request_template.json`: disabled-by-default request template for
  later solver or judge calls.
- `mock_model_responses.jsonl`: sample solver/judge outputs for dry-run
  grading and inspection.
- `run_mock_experiment.py`: no-dependency scorer that grades the mock solver
  responses and summarizes judge failures.
- `report.md`: human-readable notes from the first hand-authored sample pass.

## Run

```bash
uv run python experiments/multi_hop_qa_mock/run_mock_experiment.py \
  --samples experiments/multi_hop_qa_mock/mock_public_samples.jsonl \
  --responses experiments/multi_hop_qa_mock/mock_model_responses.jsonl \
  --models experiments/multi_hop_qa_mock/mock_models.json \
  --output-dir runs/multi_hop_qa_mock
```

Build the comprehensive ontology preview:

```bash
uv run python experiments/multi_hop_qa_mock/build_comprehensive_ontology_preview.py \
  --output-dir experiments/multi_hop_qa_mock/preview
```

The comprehensive preview applies an atomic clue breadth gate:

- `MIN_INDIVIDUAL_CANDIDATE_COUNT = 5`
- `MIN_TEMPORAL_SIDE_RANGE = 5`

Any individual clue that narrows the candidate set below five is marked
`reject`, even if it would be correct after composition. This is deliberately
strict: rare clues such as a positive-Y selector or final-union input can become
answer leaks if they are allowed as standalone clues.

The runner writes:

- `runs/multi_hop_qa_mock/solver_summary.json`
- `runs/multi_hop_qa_mock/judge_summary.json`
- `runs/multi_hop_qa_mock/mock_experiment_report.md`

## Interpretation

This experiment is for design pressure only:

- Does the hidden query shape feel auditable?
- Do rendered questions look natural enough to send to an LLM?
- Are distractors plausible?
- Do cheap solver/judge mocks expose obvious ambiguity or leakage issues?
- Which samples should be sent to OpenRouter first?

Do not treat pass rates here as benchmark results. The current responses are
mocked to exercise the grading path.

## Translator Packet Policy

The translator model should receive `translator_input_packets.jsonl`, not
`mock_hidden_queries.jsonl`.

The translator packet includes:

- public source code, because final benchmarked models also see the code;
- answer type and answer-format instruction;
- approved clue meanings with `clause_id` and `constraint_type`;
- allowed CAD terms;
- forbidden strings that must not appear in the question;
- an output schema requiring `question`, `clue_map`, and `self_check`.

The translator packet excludes:

- gold answer;
- executable predicates;
- candidate sets after each clause;
- evidence chains;
- distractor analysis;
- verifier status;
- difficulty internals beyond the target bucket.

This keeps the first LLM call in a rendering role. It can improve phrasing, but
it cannot invent labels, choose the answer, or decide uniqueness.

## Schema To Question Boundary

The intended path is:

```text
trace/schema/ontology atoms
-> deterministic canonical clue compiler
-> sanitized translator packet
-> optional LLM wording
-> deterministic verifier and judges
```

The file `ontology_to_translator_compilation.md` shows this boundary directly.
If the canonical clues are good enough, we can skip the translator and ship a
templated checklist. The point of the translator is only to improve naturalness
or vary phrasing after deterministic clue construction has already succeeded.
