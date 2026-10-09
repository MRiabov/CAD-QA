# PRD — CAD-QA

**Status:** active, 2026-10-07. Derived from the course paper
(`CA2_Riabov_final.tex`) and the specs (`specs/paper-spec.md`,
`specs/research-experiment-spec.md`, `specs/dataset-spec.md`, `human-paper-spec.md`).

## One sentence

Build a verifiable benchmark for reasoning over procedural CadQuery programs with no
access to CadQuery, show that current language models fail it, show that a small open
LLM model fine-tuned on graph-derived supervision improves substantially, and publish
the result.

## Research questions

Primary:

- How can we improve the raw capability of an LLM model to comprehend CAD code?

Secondary:

- How should a dataset be constructed to improve reasoning over 3D code?
- Does scaling a synthetic training approach improve reasoning on *other* datasets
  (transfer)?
- Is the resulting reasoning concise?

## Research objective and success criteria

**Objective.** Close the multi-hop CAD-reasoning gap for small LLM models on an immutable, tiered,
verifiable slice, relative to base and cost-effective baselines — and show that the capability
transfers.

**Hypotheses (H1–H4), by role and priority:**

| ID | Statement | Role | Priority |
|---|---|---|---|
| **H3** | training on CAD-QA transfers: the LLM model improves on an independent, credible benchmark (BenchCAD `qa_code`, `edit_code`) | transfer (end) | **P0 — headline** |
| **H4** | a given pass rate on the CAD-QA corpora predicts performance on the independent credible benchmark (the dataset is the lever) | means → end | **P0 — strong mechanism** |
| **H2** | graph-derived supervision raises CAD-QA hard-slice accuracy beyond format-only and answer-only controls | reasoning (means) | **P0 — core** |
| **H1** | tool-format SFT raises tool-valid rate | format | P1 — control |

Full statements, designs, and confound controls: `train-and-eval/fine-tuning/training.md`
§1 and `train-and-eval/evaluation/plan.md` §5.1.

**Success criteria (tiered).** `T` is set only after the immutable slice is measured; the gating step is
re-measuring the base, the cost-effective baselines, and 2–3 current frontier LLM models on it.

| Slice | Base | Target `T` |
|---|---|---|
| 1-hop | `[to measure]` | `[to measure]` |
| 2-hop | `[to measure]` | `[to measure]` |
| 3-hop (headline hard slice) | `[to measure]` | `[to measure]` |
| 5-hop | `[to measure]` | `[to measure]` |
| 6–10-hop | — | no target until rows exist |

**Minimum vs strong.** Minimum (a dataset paper): a valid immutable instrument, baselines that fail,
and a graph-derived LLM model that improves the held-out split. Strong: the gain reaches an independent
credible benchmark (H3) and tracks the CAD-QA pass rate (H4).

**Scope.** H1 and H2 are prerequisites; H3 is the peer-review gate; H4 is the mechanism. RL is a
**means** to raise the CAD-QA pass rate on harder tiers (subject to the pass@k accessibility gate),
not a separate claim; conciseness is deferred to future work.

## Claims and contributions

- A synthetic dataset, and an open method for building it, that drives mathematical
  reasoning over a CAD ontology (vertices, faces, selectors, boolean operations).
- The dataset exposes the critical reasoning path, so it can also train conciseness.
- A progressively labelled set (a hop-count curriculum) for curriculum learning.
- Empirical: graph-derived supervision improves a small LLM model's benchmark accuracy.

## Deliverables

| Deliverable | Artifact | Definition |
|---|---|---|
| Benchmark dataset | HuggingFace dataset + card | Immutable, split (train/validation/test), reproducible from the CLI |
| Baselines | `docs/experiments/` record | Cost-effective models on the benchmark, by hop and answer format |
| Fine-tuned LLM model | HuggingFace LLM model + LLM adapter | A small (2–4B) LLM model that beats its base and the baselines on the hard slice |
| Paper | manuscript | Complete main body with real tables and figures |
| Thesis | manuscript + validation appendix | The trust audit becomes the implementation-validation appendix |

## Evaluation contract

- **Primary setting — no access to CadQuery.** Input: CadQuery program plus a
  rule-rendered prompt. Output: a short structured answer, optionally with confidence.
  Score by exact structured-answer accuracy.
- **Primary harness — `numpy`.** The LLM model may run Python in a sandbox with NumPy to
  compute values. This still has no access to CadQuery.
- **Other harnesses (P2).** `no_tools` (pure reasoning) and `cadquery` (full kernel access,
  a single correct tool call suffices) are upper bounds, not the primary score.
- **Targets.** Cost-effective models should score ≤30% on the benchmark; the small trained
  LLM model should improve from roughly 10% to 50–70%.
- **Metrics.** Accuracy; invalid-output rate; missing-response rate; accuracy by hop slice,
  relation family, and measurement scope; static-hop versus geometry-hop breakdown;
  reasoning length; calibration when confidence is requested.

## Scope

- Primary corpus: executable CadQuery programs. Synthetic fixtures are for
  tests and didactic examples only.
- Labels are precomputed offline from the CAD ontology graph and the CadQuery kernel. Evaluation
  needs no kernel and no container.
- Public prompts are rule-rendered from hidden query programs, never translated by an LLM model.
  Language models are not in the trusted generation or grading path.
- `CADEditQA` (constrained edit prediction) is a possible extension, not required for the
  first paper.

## Definition of done

1. The dataset is immutable and published with a card; held-out sources never overlap train.
2. Baselines are recorded by hop and answer format, with every LLM model call logged.
3. A small LLM model is trained and holds a clear, statistically supported improvement on the
   immutable test set over its base and the baselines — not explained by format compliance
   alone.
4. Reasoning is not collapsed: generation entropy, output length, and diversity are
   reported.
5. The manuscript is complete with real numbers, tables, figures, and limitations.
6. The thesis validation appendix (the audit) is complete.

## Non-goals

- State-of-the-art CAD generation or reconstruction.
- A public question DSL.
- Beating frontier models on general 3D reasoning.
- Kernel execution inside the primary harness (which has no access to CadQuery).

## Open questions

See `development-plan.md` and the per-pipeline docs for current open questions.

## Resolved questions

None yet.
