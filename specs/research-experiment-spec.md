# Research Experiment Specification

This document specifies the experiment suite for CAD-QA and CADEditQA. The goal
is not only to improve benchmark scores, but to identify which data, training,
prompting, verifier, and evaluation choices improve LLM performance on CAD
program reasoning more broadly.

Canonical task, label, schema, and generation semantics remain in
`benchmark-task-spec.md`, `label_rules.md`, `schema.md`, `generation_policy.md`,
`cadedit-task-spec.md`, and `multi-hop-qa-task-spec.md`. If this document
conflicts with those specifications, the canonical specifications win.

## Goals

The experiment suite should answer:

1. What CAD program reasoning failures do current LLMs have?
2. Which CAD-QA task families are learnable from trace-derived supervision?
3. Which splits reveal true generalization rather than memorization?
4. Does CAD-QA training improve counterfactual and edit-oriented CAD behavior?
5. Which labels are robust enough for public benchmarks and which belong only
   in diagnostic research artifacts?
6. Which later complex task families need separate treatment because their
   graph, spatial, or failure labels introduce new shortcut risks?

## Compute Budgets

Default target budget:

- one small closed-book evaluation suite across frontier and open models;
- one 4B-8B answer-only SFT run;
- one 4B-8B reasoning-SFT run over selected trace rationales;
- focused ablations on data size and task mixture.

Expanded budget:

- model-size scaling;
- counterfactual transfer experiments;
- edit/verifier reward experiments;
- multimodal render augmentation.

All experiments must record:

- GPU type and count;
- wall-clock time;
- approximate cost when rented;
- model, adapter, and tokenizer identifiers;
- exact command line;
- dataset version and split manifest hash;
- prompt template versions;
- random seeds;
- evaluation script commit hash.

## Reporting Rules

Always report:

- overall accuracy;
- per-task accuracy;
- invalid output rate;
- numeric tolerance pass rate;
- split-specific performance;
- performance by `requires` tag;
- near-boundary performance;
- provenance ambiguity performance;
- row counts for every reported slice.

Do not report a headline number without showing task mix and split mix.

## P0: Dataset Characterization

Measure and publish:

- row counts by task type and split;
- source counts by CADEvolve subtree;
- operation count distribution;
- topology count distribution;
- selector expression distribution;
- volume delta distribution;
- point sampling strata;
- provenance relation counts;
- graph-query template and resolution-status counts;
- spatial-reference type counts;
- bounding-box region predicate counts;
- validity failure-type counts;
- failure reasons and rejection rates;
- duplicate and leakage audit results.

## P0: Baselines

Implement:

- majority/random baselines;
- static operation-count parser;
- regex operation-count baseline;
- selector-name heuristic baseline;
- primitive symbolic volume baseline for synthetic fixtures;
- AABB point-membership baseline;
- prompt-only closed-book LLM baseline.

Baselines should expose which task subsets require real geometry reasoning.

## P0: Closed-Book Model Suite

Evaluate representative models with no CAD execution tools. Prompts must tell
the model not to execute code. The evaluation harness should parse only the
structured answer format.

Report separately for:

- static tasks;
- selector tasks;
- numeric geometry tasks;
- topology tasks;
- point membership;
- feature provenance.
- graph-like multi-hop tasks, spatial-distance tasks, bounding-box region
  tasks, and validity/failure-mode tasks when those later families are present.

## P0: Prompting Ablation

Compare:

- minimal prompt;
- prompt with answer schema only;
- prompt with task definitions;
- prompt with CadQuery selector reminders;
- few-shot examples from training split only.

Do not include labels, diagnostics, or hidden trace data in prompts.

## P0: Answer-Only SFT

Train on public prompt and answer pairs only. This establishes the simplest
training baseline.

Ablations:

- all tasks mixed;
- no static tasks;
- no provenance tasks;
- numeric-only;
- topology/selector-only;
- counterfactual-only where available.

## P0: Reasoning-SFT

Use generated rationales only when they can be grounded in trace metadata. Do
not train on hallucinated explanations as if they were ground truth.

Candidate rationale sources:

- operation graph summaries;
- arithmetic traces for simple volume tasks;
- selector evaluation summaries;
- topology before/after summaries;
- point nearest-entity diagnostics;
- conservative provenance evidence.

Evaluate whether reasoning supervision improves hard tasks or merely increases
format compliance.

## P0: Data Scaling

Train at increasing row counts:

```text
1k
5k
15k
50k
full
```

Keep task proportions fixed where possible. Report learning curves by task
family and split.

## P0: Generalization By Split

Evaluate at least:

- random split;
- generator-held-out;
- source-subtree-held-out;
- operation-held-out;
- topology-held-out;
- near-boundary;
- counterfactual-held-out group.

Held-out split performance is more important than random split performance for
paper claims.

## P1: Counterfactual Sensitivity

Use paired prompts where one source parameter or operation changes. Measure:

- answer flip accuracy;
- magnitude error for changed numeric labels;
- false invariance rate;
- false sensitivity rate.

This directly tests whether models track the relevant code.

## P1: Task Transfer Matrix

Train on one family or family subset and evaluate across all families:

- static -> selector/topology;
- numeric -> topology;
- selector -> workplane;
- point membership -> provenance;
- QA -> edit.
- scalar/topology/provenance -> graph-query;
- point/workplane -> spatial-distance;
- provenance/topology -> bounding-box region;
- topology/selector -> validity/failure prediction.

The key research question is whether trace-derived supervision transfers beyond
the exact answer type.

## P1: CADEditQA Evaluation

After edit rows exist, evaluate whether CAD-QA-trained models improve:

- choosing an edit direction;
- predicting a parameter change;
- identifying which feature to edit;
- satisfying verifier constraints.

Use verifier-derived metrics, not natural-language judgment.

## P2: Complex CAD-QA Diagnostics

Evaluate complex later task families separately from MVP CAD-QA scores:

- feature-level graph diagnostics;
- point-to-point, feature-to-feature, axis, and centerline distance QA;
- bounding-box-as-selector region QA;
- validity and failure-mode QA.

Report each family with its own row counts, parse rates, reference-resolution
failure rates, and ambiguity/quarantine rates. Do not merge these scores into a
single CAD-QA headline number until their task mix and shortcut baselines are
stable.

Recommended baselines:

- graph-query oracle over stored IR as an upper bound;
- shallow operation-order and keyword baselines for graph queries;
- centroid/AABB distance baselines for spatial-distance tasks;
- AABB-only region-overlap baseline for bounding-box region tasks;
- majority failure-type and kernel-status heuristic baselines for validity
  tasks.

## P2: Multi-Hop CAD-QA Track

Evaluate BrowseComp-style Multi-Hop CAD-QA as a separate track once
graph-sampled query programs, evidence-chain storage, obfuscation policy, and
uniqueness rejection are available.

Report separately from CAD-QA Core:

- graph hop counts;
- static/text-derived hop counts;
- geometry/trace-derived hop counts;
- static-hop ratio;
- distractor counts;
- obfuscation type;
- answer uniqueness and ambiguity margins;
- reference-resolution failure rates;
- performance by `mhqa_level_1_direct_0_1_hops`,
  `mhqa_level_2_bridge_2_hops`, `mhqa_level_3_complex_4_5_hops`,
  `mhqa_level_4_hard_6_8_hops`, and
  `mhqa_level_5_extreme_9_10_hops`;
- closed-book, graph-summary, and tool-allowed modes.

Do not merge this track into a single CAD-QA headline number until shortcut
baselines and human audit pass rates are stable.

## P1: Bounded RL Or Rejection Sampling

Use verifier rewards only after SFT is stable. Candidate rewards:

- exact structured-answer parse;
- numeric tolerance pass;
- point classification correctness;
- topology count correctness;
- edit verifier success.

Keep RL experiments bounded and report reward hacking failures explicitly.

## P2: Multimodal Augmentation

Optional render or geometry previews can be tested as an extension. The default
CAD-QA benchmark remains code-only unless a separate multimodal track is
defined.

## Error Taxonomy

Annotate or automatically classify errors:

- CadQuery syntax misunderstanding;
- selector semantics error;
- workplane/local-global frame error;
- arithmetic error;
- boolean operation sign error;
- topology count error;
- boundary tolerance error;
- provenance over-attribution;
- graph-reference resolution error;
- multi-hop aggregation error;
- spatial-reference or centerline extraction error;
- bounding-box region predicate error;
- validity/failure-mode overgeneralization;
- invalid answer format;
- shortcut reliance.

## Artifact Requirements

Release or archive:

- dataset metadata and split manifests;
- generation reports;
- failure manifests;
- evaluation scripts;
- baseline predictions;
- model predictions;
- prompt templates;
- training configs;
- exact commands;
- paper table source data.

## Non-Goals

- Free-form design generation as the primary benchmark.
- Grading natural-language explanations as the main metric.
- Public release requiring CAD kernel execution.
- Claiming exact human design intent from CADEvolve variable names.
- Treating ambiguous provenance as a single forced label.
