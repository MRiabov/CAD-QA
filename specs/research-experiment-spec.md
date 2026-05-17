# CAD-QA Research Experiment Specification

Experiments should evaluate one graph-first benchmark, grouped by hop count,
relation family, and measurement scope.

## Primary Setting

Closed-book CAD reasoning:

- input: public CadQuery source and rule-rendered prompt;
- prohibited: calling CadQuery or external CAD kernels;
- output: short structured answer plus optional confidence.

Tool-assisted execution is an upper-bound setting, not the main score.

The primary benchmark/training setting must be geometry-first. Rows that can be
answered from assignment names, operation order, literal arguments, or simple
source-pattern matching are calibration rows. They may be reported separately,
but they must not dominate headline fine-tuning or benchmark numbers.

## Metrics

- exact structured-answer accuracy;
- invalid output rate;
- calibration when confidence is requested;
- accuracy by hop slice;
- accuracy by relation family;
- accuracy by measurement scope;
- static-hop versus geometry-hop breakdown;
- prompt-family distribution and syntax-only calibration quota;
- verifier failure and quarantine taxonomy.

## Baselines

- random and majority;
- regex/static syntax;
- selector-name heuristic;
- operation-order heuristic;
- symbolic primitive geometry;
- AABB-only point, distance, and region baselines;
- graph resolver oracle.

## Model Runs

Report closed-book zero-shot, few-shot, answer-only SFT, and candidate-trace
reasoning SFT when artifacts exist and pass geometry-first quality gates. The
central hypothesis is that graph-derived CAD-QA supervision improves CAD
editing and debugging by teaching models to resolve entities, traverse
relations, compare metrics, and reject ambiguous answers.

The current CLI supports parser-backed grading for response JSONL records with
`row_id` and `answer`, simple oracle, first-candidate, and null baselines,
zero-shot and few-shot request export, and one-command smoke orchestration.
Provider submission adapters and remote/GPU orchestration remain follow-up
layers.
