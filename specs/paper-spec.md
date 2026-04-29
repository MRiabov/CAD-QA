# CAD-QA Paper Specification

This document captures the paper ambition and research narrative for CAD-QA.
For implementation, the canonical specifications are
`specs/benchmark-task-spec.md`, `specs/label_rules.md`, `specs/schema.md`, and
`specs/generation_policy.md`.

## 1. Core Claim

Current language models can often produce plausible CAD code, but they remain
weak at mentally executing the geometry induced by CAD programs. CAD-QA tests
whether models understand construction history, intermediate state, topology,
selectors, coordinate frames, point membership, and feature provenance from
executable CadQuery code.

The benchmark should be framed as controlled CAD program reasoning, not generic
CAD trivia. The central question is:

> Given a CadQuery script, can a model infer the geometry, topology, and
> construction provenance implied by the program without running a CAD kernel?

## 2. Why CAD-QA Is Useful

CAD agents need more than final shape similarity. They need to reason about:

| Capability | Why it matters |
| --- | --- |
| Operation order | Determines construction history and edit locality. |
| Selector semantics | CadQuery modeling heavily depends on selectors. |
| Workplane tracking | Many CAD bugs are coordinate-frame mistakes. |
| Volume and bounding boxes | Basic quantitative geometry reasoning. |
| Topology counts | Faces, edges, vertices, holes, and loops affect manufacturability. |
| Point membership | Needed for collision, fit, supports, and material queries. |
| Feature provenance | Needed to explain and edit model regions. |
| Counterfactual edits | Needed for design assistance rather than passive recognition. |
| Graph-like multi-hop reasoning | Needed to answer questions that compose operation order, feature attributes, and topology references. |
| Spatial distance reasoning | Needed for fit, clearance, centerline, and feature-spacing questions. |
| Region queries | Needed to reason about what changed inside a bounded spatial window. |
| Validity and failure prediction | Needed to anticipate kernel failures and invalid CAD operations. |

The stronger paper claim is that exact trace-derived supervision can improve
LLM reasoning about CAD programs, and that capability should transfer to
better CAD editing and debugging.

## 3. Task Tiers

### Tier A: Static Code Comprehension

Examples:

- How many `.extrude()` operations are in the script?
- Which operation creates the first solid body?
- Which selector is used before the final fillet?
- How many named parameters affect the hole diameter?

These tasks test CadQuery syntax and operation ordering without requiring B-Rep
execution.

### Tier B: Symbolic Geometry

Examples:

- What volume does this rectangular extrusion add?
- What is the bounding box after this translation?
- What is the center of the primitive before subtraction?

These are the cleanest early training signal because labels can often be exact
or kernel-verified.

### Tier C: Topology

Examples:

- How many faces are present after the through-hole cut?
- How many circular edges does the final part contain?
- Which faces share an edge with the top face?

These expose common model weaknesses in B-Rep reasoning.

### Tier D: Feature Provenance

Examples:

- At coordinate `(x, y, z)`, which feature last made this point material?
- Which feature removed material from this region?
- Which feature created the cylindrical wall face of the hole?
- Was this edge inherited, modified, or bounded by a later cut?

This is the most distinctive CAD-QA capability, but it needs careful
many-to-many labels.

### Tier E: Counterfactual CAD Reasoning

Examples:

- If the hole radius changes from 2 mm to 3 mm, how does final volume change?
- If this fillet is removed, how many sharp vertical edges remain?
- Which bounding-box dimension changes if extrusion height doubles?

These tasks connect QA to edit ability.

### Tier F: Graph-Like Multi-Hop CAD Reasoning

Examples:

- Which feature after the second box added the most net volume?
- What is the length of the feature that added the most volume?
- How much volume did cylinder A subtract from box B?

These are later-stage tasks because they require a typed query graph, stable
feature/entity resolution, and deterministic aggregation labels.

### Tier G: Spatial Distance And Region Reasoning

Examples:

- What is the X distance between the first and third holes?
- What is the shortest distance between the first hole centerline and the
  second cylinder centerline?
- Which features added or removed material inside a specified bounding box?

These tasks require stable point, axis, centerline, and spatial-window labels.

### Tier H: Validity And Failure-Mode Reasoning

Examples:

- Will this fillet operation succeed?
- What is the largest valid fillet radius for the selected edges?
- Will this shell thickness produce a valid solid?

These tasks should be treated as a distinct complex family because labels
depend on bounded execution probes and kernel-stability policy.

## 4. CADEvolve As Primary Source

CADEvolve is the practical first source because it provides executable
CadQuery programs at scale. CAD-QA should derive real benchmark examples from
CADEvolve `P` and `C` executable trees, with `G` used for family metadata and
leakage-safe grouping.

Synthetic examples remain necessary for:

- golden tests;
- smoke tests;
- known topology/provenance edge cases;
- exact didactic examples in the paper.

They should not dominate released benchmark counts.

## 5. Dataset Artifact Strategy

The public dataset should be code-plus-label. It should include normalized
source code, prompts, structured answers, raw trace labels, diagnostics,
provenance, split metadata, and hashes. It should not require STEP, mesh,
render, or OpenCascade object artifacts for default training and evaluation.

Optional artifacts may support audit, visualization, or multimodal extensions.

## 6. Counterfactual Groups

Counterfactual examples are central to the paper. They prevent models from
solving tasks by shallow memorization and directly test sensitivity to relevant
source edits.

Useful groups:

- extrusion height perturbations;
- hole radius perturbations;
- selector changes;
- fillet/chamfer radius perturbations;
- operation removal;
- workplane offset changes.

All variants in a counterfactual group must stay in the same split.

## 7. Baselines

Report at least:

- random/majority baselines;
- regex/static-code baselines for operation count tasks;
- simple symbolic baselines for primitive volume tasks;
- AABB-only baseline for point membership;
- AABB-only region-overlap baseline for bounding-box region tasks;
- centroid or AABB distance baselines for spatial-distance tasks;
- operation-order heuristics for graph-like multi-hop tasks;
- majority and kernel-status heuristics for validity/failure tasks;
- selector-name heuristics;
- closed-book LLM zero-shot;
- closed-book LLM few-shot;
- trained answer-only SFT;
- trained reasoning SFT when traces are available.

The paper should separate tasks that static analysis can solve from tasks that
require geometry execution or topology reasoning.

## 8. Reviewer Risks

Likely critiques and responses:

- "Why not just run CadQuery?" The benchmark measures whether models internalize
  CAD program semantics for closed-book reasoning and training; tool use can be
  a separate setting.
- "Feature provenance is not exact." CAD-QA should distinguish exact builder
  history, topology-matched provenance, and ambiguous merged cases instead of
  overclaiming.
- "Topology is kernel-sensitive." Store CadQuery/OCP/OpenCascade versions and
  label policy with every release.
- "Synthetic data may not transfer." Use CADEvolve as the primary source and
  reserve synthetic rows for fixtures and audits.
- "Models can exploit shortcuts." Use held-out generator, operation, topology,
  and counterfactual splits plus shortcut baselines.

## 9. Minimal First Paper

The best first version is:

- CADEvolve-backed code-only CAD-QA;
- exact operation, selector, volume, bbox, topology, point membership, and
  conservative provenance tasks;
- structured answers with deterministic parsing;
- strong split hygiene;
- baseline and SFT experiments;
- a clear error taxonomy showing where models fail.

The highest-value result would be evidence that trace-derived CAD-QA training
improves hard subsets such as selector semantics, workplane tracking, topology,
and point/provenance reasoning more than generic CAD-code training.
