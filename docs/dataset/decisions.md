# Dataset decisions

**Status:** active, 2026-10-07.

Local decisions for the `dataset_generation` unit, in ADR format
(`../docs-conventions.md#adr`). Decisions scoped to a single stage live in that stage doc's
`Local decisions` section.

---

## DD-01 — Freeze dataset-generation code; document behaviour

- **Status:** accepted.
- **Context:** The dataset-generation pipeline was written by an agent, a prior refactor
  was moot, and the intent behind the current code is (probably) fine
  (`plans/oct-7/restructure-docs.md`).
- **Decision:** Treat `dataset_generation` (today `cad_qa/`) as frozen. New docs describe
  executed behaviour; they do not justify refactors. Change generation code only when a P0
  thesis claim is directly blocked by a verified bug, minimally, on a branch.
- **Consequences:** Doc/code mismatches become recorded findings (open question / local
  decision), not silent fixes. The audit (Phase 0) is where behaviour becomes `verified`.

## DD-02 — These docs supersede `specs/` for the dataset

- **Status:** accepted.
- **Context:** `specs/` and `docs/` grew independently and drifted; `specs/` states intent
  but nothing demonstrates behaviour (`plans/oct-7/restructure-docs.md`, D2).
- **Decision:** Fold `specs/` semantics into `docs/dataset/`; treat `specs/dataset-spec.md`,
  `specs/benchmark-task-spec.md`, `specs/multi-hop-qa-task-spec.md`,
  `specs/generation_policy.md`, and `specs/schema.md` as input material. `specs/` is left
  as a pointer or removed by the migration.
- **Consequences:** Where a spec and the code disagree, the code wins and the discrepancy
  is recorded (for example `specs/schema.md` omitting `TraceRecord.selector_results`).

## DD-03 — Deterministic trusted path; no LLM in generation or grading

- **Status:** accepted.
- **Context:** `specs/generation_policy.md` fixes the trusted generation chain as
  `source -> graph -> query -> verifier -> prompt -> row`.
- **Decision:** LLMs are not trusted generators or judges. They may be used only for
  optional wording experiments or external LLM model evaluation.
- **Consequences:** Prompts are rule-rendered (`cad_qa/prompts/render.py::render_prompt`);
  gold answers come from the resolver, not an LLM model.

## DD-04 — Public/private split is the release boundary

- **Status:** accepted.
- **Context:** Rows are code-plus-label internally, but the public benchmark surface must be
  answer-free (`specs/dataset-spec.md`).
- **Decision:** Export two views: `public` (answer-free LLM model input) and `private`
  (gold answer, hidden Gold query program, answer candidate set trace, clue map). The split
  is defined by
  `cad_qa/dataset/public.py::PUBLIC_FIELDS` and `::PRIVATE_FIELDS`; a hidden-field leak is
  an audit error.
- **Consequences:** Grading uses `public` + `private`; `public_private_report.json` records
  row-count parity and leak checks.

## DD-05 — Release tiers; only `benchmark-release` supports public claims

- **Status:** accepted.
- **Context:** `specs/dataset-spec.md` defines `smoke`, `release-candidate`, and
  `benchmark-release`, and warns that weaker tiers must never be described as
  benchmark-release ready.
- **Decision:** `benchmark-release` is the canonical bar, expressed as
  `cad_qa/dataset/release_report.py::BENCHMARK_RELEASE_PROFILE`. The default CLI tier is
  `release-candidate`.
- **Consequences:** Release/SFT reports gate on explicit per-tier thresholds; passing smoke
  or release-candidate gates is a development checkpoint only.

## DD-06 — Parquet-preferred record artifacts with JSONL fallback

- **Status:** accepted.
- **Context:** Large graph/query/dataset payloads (hundreds of MB as JSONL) motivated a
  compact columnar default (`docs/_archive/implementation_status.md`).
- **Decision:** `cad_qa/io.py` writes records as Parquet when the path ends in `.parquet`
  and JSONL for `.jsonl`, and `record_artifact_path` prefers Parquet. Readers remain
  backward-compatible with legacy `record_json` Parquet and with JSONL.
- **Consequences:** Downstream stages accept either format; compact query artifacts may
  store a `graphs` sidecar instead of embedding a graph per query record
  (`cad_qa/cli.py::_materialize_graph_lookup`).

## DD-07 — CadQuery program operation trace is optional for low-hop rows, required for release-grade geometry

- **Status:** accepted.
- **Context:** `specs/schema.md::TraceRecord` marks CadQuery program operation trace records
  optional for low-hop static rows but required for release-grade geometry, topology,
  CadQuery selector, material, and validity rows.
- **Decision:** `cad_qa/ontology/extract.py::build_graph` accepts an optional
  CadQuery program operation trace; graph construction is AST-based and enriches from
  its evidence when present.
- **Consequences:** Smoke runs can build graphs without CadQuery; release-grade geometry
  claims require a CadQuery program operation trace.

## DD-08 — `reject_unless_unique` is the default Query verifier policy

- **Status:** accepted.
- **Context:** `specs/generation_policy.md` requires the full clue set to resolve exactly one
  answer for main rows.
- **Decision:** `cad_qa/query/ir.py::QueryProgram.reject_unless_unique` defaults to
  `True`; the resolver fails a query whose answer candidate set is empty or not exactly one.
- **Consequences:** Ties are rejected unless a query explicitly opts out; failures land in
  the failure manifest.

## DD-09 — Keep conservative or surrogate-backed rows non-release-ready instead of silent drop

- **Status:** accepted.
- **Context:** Conservative material/void-region projections and CadQuery-selector surrogate
  face identities can exercise the stack end to end but are not release-grade
  (`specs/dataset-spec.md#quarantine-policy`).
- **Decision:** `cad_qa/dataset/materialize.py::_evidence_policy` assigns an evidence tier
  and `release_ready=false` with `quarantine_reasons`; release export excludes them and the
  non-release-ready report counts them.
- **Consequences:** No silent data loss: rejected and non-release-ready rows are reported.

## DD-10 — Default SFT export is geometry-critical only

- **Status:** accepted.
- **Context:** Benchmark value comes from geometry-derived reasoning, not syntax lookup
  (`specs/benchmark-task-spec.md#geometry-first-benchmark-policy`).
- **Decision:** `cad_qa/dataset/sft.py::default_training_rows` keeps geometry-critical,
  non-calibration, non-quarantined rows; syntax-only calibration is excluded unless
  `--include-calibration` is passed.
- **Consequences:** Default training reports enforce geometry-critical dominance and a zero
  syntax-only cap; calibration exports are review artifacts only.

## DD-11 — Sampled parameters are private metadata for balance gates

- **Status:** accepted.
- **Context:** Release-grade families must sample avoidable choices rather than bake them in;
  release reports must measure coverage (`specs/generation_policy.md#maximal-parameter-sampling`).
- **Decision:** Serialize normalized `sampled_parameters` on each row
  (`cad_qa/query/parameters.py::sampled_parameters_from_query`), including rendered
  prompt/clue template IDs added at materialization
  (`cad_qa/dataset/materialize.py::_query_to_dict`).
- **Consequences:** Benchmark-release parameter-balance gates read private metadata;
  full synthesis-layer sampling coverage remains open work.

## DD-12 — Group-safe splits over protected leakage labels

- **Status:** accepted.
- **Context:** Splits must be safe by true leakage groups, not by broad corpus provenance
  (`specs/dataset-spec.md#splits`).
- **Decision:** `cad_qa/dataset/split.py` unions sources that share protected labels
  (`split_group`, `counterfactual_group`, `source_family`, `family_id`, `template_id`, and
  path-derived family) and assigns a deterministic ~70/15/15 split across groups; broad
  `generator_id`/`generator` are reported but not merged.
- **Consequences:** All rows sharing a protected group stay in one split; CadQuery-program-only
  datasets collapse to `train` and are reported as not multi-split.

## DD-13 — Doc/code conflicts are findings, not silent fixes

- **Status:** accepted.
- **Context:** The restructure plan and the working agreement make conflicts findings.
- **Decision:** When a doc and the frozen code disagree, document the actual behaviour and
  record the discrepancy as a local decision or open question.
- **Consequences:** This file and the step docs carry explicit known mismatches (see
  `pipeline/00-overview.md#open-questions`).

## Open questions

- DD-14 — **Terminology ratchet.** Several load-bearing dataset terms are absent from
  `../glossary.md` (task family, prompt family, answer spec/contract, sampled parameters,
  evidence tier, prompt template, clue map, release-ready, split group, geometry-critical,
  shortcut resistance). They are used here because the code and existing specs use them;
  the glossary should absorb them during the legacy-term audit. This doc does not edit the
  glossary.

## Resolved questions

_(none yet)_

## Extra deliverables - P2

_(none)_
