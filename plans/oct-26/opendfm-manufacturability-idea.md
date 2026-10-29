# Research idea: `opendfm` — STEP manufacturability analysis and manufacturability-constrained CAD

**Status:** idea, unscreened, 2026-10-26. This is not a plan, and it makes no novelty or
feasibility claim. It records an idea for later evaluation; no prior-art or tooling scan has
been done.

## Idea

An `opendfm` package with two layers:

1. **Checker.** Deterministic, open-source manufacturability analysis of STEP (ISO 10303
   AP214/AP242) B-rep models. It reports per-constraint pass/fail, the measured value, and the
   witness geometry (face, edge, or location), so a result is auditable rather than a scalar
   score.
2. **Benchmark.** Tasks that test whether a CAD model or LLM model can produce or modify a STEP
   model that satisfies stated manufacturability constraints, with the checker as the verifier.

The package is the useful artifact even if the benchmark is not; a benchmark without a trusted
checker is worthless.

## Why this might matter

CAD-QA's own experiments suggest basic CadQuery generation is no longer a discriminating
capability. Manufacturability is a plausible next gate: it is external to syntax, requires
geometry plus process reasoning, has industrial stakes, and admits deterministic scoring when
the constraints are formalized. That is a hypothesis, not evidence.

The user's working assumption is that manufacturability checking is "more or less sorted out."
That may be true for isolated rules in commercial DFM tools. It is unknown whether an open,
STEP-native, process-parameterized checker and a constraint-following benchmark already exist.
The idea only survives if the benchmark/eval layer is missing, not merely the geometric
predicates.

## What the package would contain

- **STEP ingest.** OCCT/OCP read, unit handling, B-rep validity checks, and canonical entity
  extraction.
- **Typed constraint model.** Pydantic constraint specs per process (`CNC3Axis`,
  `InjectionMolding`, `FDM`, `SheetMetal`), parameterized by things such as minimum wall
  thickness, minimum tool radius, maximum aspect ratio, and draft angle. Prefer `StrEnum` for
  process and constraint kinds.
- **Checkers.** One function per constraint class. Each returns a typed result with the
  measurement and witness geometry, not just a boolean.
- **Task harness.** Prompts, expected output schema, deterministic verifier, and recorded
  artifacts (input STEP, output STEP, checker trace, measurements).
- **Artifact retention.** Every model output and checker trace is recorded, as required for
  all LLM calls.

## Candidate task families

- **Audit.** Given a STEP file and a process specification, list violations and their locations.
- **Repair.** Given a STEP file with planted violations, return a valid STEP that preserves
  design intent (volume, bounding box, feature layout).
- **Generate.** Produce a STEP model under constraints from a functional specification.
- **Select.** Choose a process or material for a given geometry.
- **Tradeoff.** Adjust a parameter to satisfy conflicting constraints.

## Evaluation design

- **Synthetic gold.** Procedurally perturb valid models to plant known violations; derive labels
  with the checker. The perturbations must not create degenerate or ambiguous cases.
- **Real gold.** A small hand-audited set of models with expert labels, used to validate the
  checker rather than to train on.
- **Scoring.** Constraint satisfaction rate; false positives and false negatives against planted
  violations; repair validity plus feature preservation; separate tool-call and closed-book
  arms.
- **Contamination.** Generate tasks from private seed models and held-out process parameters;
  do not use public STEP datasets for the test set.
- **Baselines.** A frontier LLM with and without the checker tool, a CAD-specific model, and a
  human.

## Open questions

- **Which process first?** 3-axis CNC is the best candidate: the constraints are geometric and
  checkable. Injection molding adds flow and thermal simulation, FDM is messy, and sheet metal
  is rule-heavy.
- **Binary or scored?** Prefer explicit constraints with pass/fail plus a measurement. Avoid an
  aggregate "manufacturability score" whose weights are arbitrary.
- **Does STEP carry enough information?** B-rep is there, but tolerance, surface finish,
  material, process, and design intent are absent or inconsistent. Tasks must supply process
  parameters; repair tasks need an explicit intent metric.
- **Is the checker's ground truth trusted?** Validate measurements against an independent kernel
  and, on a subset, against a machinist or manufacturing engineer.
- **Is tool use cheating?** Letting the model call the checker and iterate is a legitimate
  capability, but it must be a separate arm from reasoning without the tool.
- **Name collision.** Confirm whether `opendfm` already exists before using the name.

## Minimum viable experiment

1. Prior-art and tooling scan (one to two days): open STEP DFM checkers, commercial tools,
   existing benchmarks, and licenses.
2. Build a 3-axis CNC constraint subset: minimum wall thickness, tool accessibility/undercut,
   hole depth-to-diameter, minimum internal radius, and maximum aspect ratio. Validate the
   measurements against OCCT and a few hand-checked parts.
3. Plant violations in 50–100 valid models and verify that the checker recovers them.
4. Run 100 audit and repair tasks on two or three frontier models, with and without the checker
   tool.
5. Kill the idea if frontier models are near ceiling on audit, the checker cannot produce stable
   labels, or the constraints collapse into existing CAD-QA-style geometric queries with no
   added signal.

## Relation to CAD-QA

This reuses CAD-QA's kernel-backed, auditable-verification philosophy and its typed task/clue
approach, but targets STEP plus manufacturing process constraints instead of CadQuery program
comprehension. If pursued, it should be a separate package and benchmark, not folded into
CAD-QA's release gates without its own PRD.
