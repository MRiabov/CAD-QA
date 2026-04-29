# Benchmark Family Direction

This repository is CAD-QA-first. The first benchmark family should measure
whether a model can reason over executable CadQuery construction programs,
intermediate modeling states, topology, selectors, coordinates, and feature
provenance without running CAD tools at evaluation time.

The intended future shape is a shared CAD program reasoning benchmark codebase
with sibling task families:

- **CAD-QA**: diagnostic question-answering over a single CadQuery script,
  including static code comprehension, operation traces, topology, selectors,
  workplanes, point membership, volumes, and feature provenance.
- **CADEditQA**: constrained edit and repair tasks over the same source
  programs, traces, label policies, and verifier infrastructure.
- **Multi-Hop CAD-QA**: a future BrowseComp-style CAD reasoning track for
  graph-sampled, answer-first questions that compose operation order,
  parameters, selectors, topology, spatial relations, and provenance. See
  `specs/multi-hop-qa-task-spec.md`.
- **Advanced CAD-QA diagnostics**: later-stage complex QA families over the
  same traces, including feature-level graph diagnostics, point/axis/centerline
  distance questions, bounding-box spatial-window selectors, and operation
  validity or failure-mode prediction.
- **Shared core**: CADEvolve ingestion, source normalization, isolated CadQuery
  execution, operation graph extraction, intermediate-state capture, topology
  measurement, spatial indexes, provenance approximation, split assignment,
  leakage audits, export, evaluation, and verifier/reward logic.

QA and edit tasks should share source IDs, operation IDs, trace IDs,
counterfactual groups, leakage rules, geometry snapshots, and label policies
where the underlying CadQuery program is the same. Task rows may differ, but
they should not fork source provenance or split semantics.

## Migration Sequence

1. Keep `specs/dataset-spec.md` as the project idea and task-family roadmap.
2. Add implementation-facing specifications for CAD-QA task contracts, schema,
   label rules, generation policy, and CADEvolve handling.
3. Implement one narrow CAD-QA vertical slice:
   `operation_count`, `selector_count`, `bbox_after_step`, and
   `signed_volume_delta`.
4. Add trace-backed provenance slices only after statement-by-statement
   execution and intermediate-state capture are reliable.
5. Add CADEditQA slices after the shared verifier can apply bounded edits and
   remeasure the affected scripts.
6. Add advanced CAD-QA diagnostics only after the graph/query IR, spatial
   indexes, and failure-label policies are stable enough for deterministic
   structured answers.
7. Add Multi-Hop CAD-QA only after graph-sampled query programs, evidence-chain
   storage, obfuscation policy, and uniqueness rejection are stable enough to
   avoid hardcoded template expansion.

## Boundary With IntersectionQA

IntersectionQA reasons about two-object assembly relations. CAD-QA reasons
about one construction program and its induced modeling history. Both can share
CADEvolve ingestion, CadQuery isolation, hashing, artifact policies, and
evaluation hygiene, but CAD-QA should not inherit intersection-specific labels
such as pair relation, clearance, or intersection volume as its core task
semantics.
