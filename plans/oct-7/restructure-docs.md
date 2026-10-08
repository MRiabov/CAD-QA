# Restructure docs — plan (2026-10-07)

**Status:** active. This is the only file in `plans/oct-7/`.

It plans a documentation restructure: author clearer, canonical docs under `docs/` that
capture intent (PRD), per-stage requirements, development context, and the plan to
completion. The docs themselves are written in later threads; this file is the plan and
the handoff. It is intentionally a plan, not the docs.

## Progress log

**2026-10-07** — first full draft of the doc set authored (primary checkout, D1/D9):

- Foundational: `docs/docs-conventions.md`, `docs/README.md`,
  `docs/development-context.md`, `docs/PRD.md`, `docs/glossary.md` (seeded; legacy-term
  audit pending).
- Plan-level: `docs/development-plan.md`, `docs/prior-art.md` (seed).
- Pipeline: `docs/dataset/**` (11 files), `docs/fine-tuning/**` (11 files),
  `docs/evaluation/**` (3 files) — drafted by subagents, each step status-tagged with a
  verification command.
- Owner checklist: `docs/_audit/owner-audit-todo.md`.

Notable findings from drafting, to feed the audit: environment pins are untracked and
conflict with the narrative; no tracked code produces the **merged model**; GRPO loads the
base model, not the SFT adapter; the reward and the eval grader diverge; `json`/`number`
teacher coverage is zero; most shortcut baselines are pre-graph-first and stale.

Next: owner review, then close the audit items before Phase 1.

**2026-10-07 (later)** — all pre-restructure docs moved to `docs/_archive/` (status log,
handoffs, RL records, runbooks, analysis reports, the paper draft, trace previews); all
references in the new docs and this plan rewired to `_archive/` paths. `docs/experiments/`
stays in place (the designated home for dated records).

**2026-10-08** — Don't-say checker implemented (`tools/check_dont_say.py` + tests), ported
and simplified from product-launch `redo/check-dont-say.py`; pydantic added as a dev dep.
Ported the placis exclusion mechanisms: `(home)` tree annotations, `ALLOWLIST`,
`dont-say: allow` / `home` markers; code is scanned (identifier-shaped tokens); a hit-count
ratchet (`tools/dont_say_baseline.txt`) is enforced by `tests/test_dont_say_ratchet.py`.
Current: 353 hits, all in `docs/`; code is clean because the documented `In code:`
identifiers are exempted per tree. Worklist and findings in `_audit/dont-say-worklist.md`.
D8 partially satisfied: Don't-say checker done and gated; docs-structure / ADR / decisions
linters, `rumdl`, and pre-commit/CI wiring still pending.

Note (2026-10-08, later): the "code is clean" claim above was wrong — the checker matched
only identifier-shaped tokens, so single-word terms in code comments/docstrings were never
scanned. See the entry below.

**2026-10-08 (later)** — terminology sweep, checker hardening, prior-art findings.

- The Don't-say checker now scans code **comments and docstrings** as prose; the sweep took
  prose hits to **0** (`tools/dont_say_baseline.txt` = 0).
- An opt-in identifier mode (`--identifiers`) records the code name collisions: **5,339** hits
  across 63 files, parked as the **P2 clean-code** requirement
  (`tools/dont_say_identifiers_baseline.txt`, `development-plan.md` Phase 6).
- Glossary renames landed (CadQuery program operation trace, dataset file, LLM harness mode,
  CAD feature-added/removed region, CAD-QA dataset row column sets, …).
- Prior-art findings recorded (`docs/prior-art.md`): LFM2.5/`liquid-finetune` and external
  small-LLM-model fine-tuning evidence with a candidate base shortlist; **D11** (the
  base-pipeline ADR) is still owed.
- New canonical trees: `docs/research/` (external study notes) and `docs/paper/` (the
  manuscript; excluded from the Don't-say lint).
- Repo-structure decision corrected (D13): the generation package is `dataset/` (the repo is
  CAD-QA), a sibling of `train_and_eval/`; **all** eval logic — `cad_qa/evaluation/`, the eval
  CLI, and the Harbor runner/grader — belongs in `train_and_eval/`, and `dataset/` is
  generation only.
- Still outstanding: `docs/adr/` absent; `specs/` not folded; only the Don't-say checker of D8
  exists; Phase 0a rename not started.

---

## 0. Working agreement

- Plans live in `plans/<mon-dd>/` and stay in the primary checkout.
- Repo / code / doc changes go in a worktree feature branch. We are **not
  parallelising** right now, so this is deferred; revisit when parallel work resumes.
- Docs describe intent. Where docs and code disagree, the conflict is recorded and one
  of them is fixed — never silently ignored.
- Every load-bearing claim gets a reproducible verification command.
- Every LLM call records reasoning + user-visible output + tool calls distinctly.
- Long GPU / API jobs are monitored every ~3–5 minutes; artifacts are preserved before
  teardown.

## Code-change policy

- **Dataset generation (`cad_qa/`) is frozen.** We abstain from editing it as much as
  possible: the intent behind the pipeline already exists and is (probably) fine, and a
  past refactor attempt was moot. The new docs *describe* it; they do not justify a
  refactor.
- On a doc/code mismatch in `cad_qa/`: default to documenting the actual behaviour and
  recording the discrepancy. Change generation code only when a P0 thesis claim is
  directly blocked by a verified bug, then minimally, on a branch, with the audit as the
  justification.
- **The fine-tuning/eval stack (`train_and_eval/`) is not frozen.** It is the active
  research surface and will be rewritten (reasoning-preserving pipeline).

## Priority tiers and standards

The project has two standards, and we track both explicitly:

- **P0 — Thesis critical path (blocking).** Without this the Master's thesis does not
  stand: a frozen, verified dataset; a small-model result that is real and not collapsed;
  the core claims supported by tracked artifacts.
- **P1 — Thesis important (should-have).** Strengthens the thesis but is not strictly
  blocking: a second model, transfer eval, richer ablations, the mode-3 harness.
- **P2 — Good-venue publication extras.** The higher bar for a strong venue, explicitly
  optional and potentially never executed: the ≥10,000-row `benchmark-release` tier, full
  ontology coverage, the `no_tools`/mode-3 baseline matrix, the conciseness study,
  multimodal future work, exhaustive citation work, reviewer-proof ablations.

Default: a doc, task, or phase is P0/P1 only if **the thesis** needs it. Anything that
exists to satisfy a publication reviewer rather than the thesis is P2.

Convention: every doc and every plan section may carry a trailing block, as we go:

```text
## Extra deliverables - P2

### <item>
...
```

P2 blocks are **collected, not promised** — a parking lot for the more ambitious version
of the work. Something is executed as P2 only if the P0/P1 path is green and time remains.

## Doc standards and conventions

Treat this as an LLM training project at a lab (OpenAI / DeepSeek-style rigour). The
expected artifact set and quality bar are those of an LLM lab, not a course project.
These conventions are **normative** and are (eventually) enforced by a lint checker, in
the spirit of the product-launch repo.

### Artifact set

- **PRD** (`docs/PRD.md`) — research questions, claims, deliverables, evaluation contract,
  definition of done.
- **Design rationale** — lives in ADRs (`docs/adr/`) and each pipeline's
  `00-overview.md`, not a separate methods doc (D4 dropped).
- **Dated experiment records** (`docs/experiments/YYYY-MM-DD-*.md`) — purpose, hypothesis,
  dataset/splits, config/commands, hardware, outcomes, failures, artifact paths.
- **Dataset card** and **model card** — published alongside the HF artifacts.
- **Run manifest** — env pin, seed, dataset revision, exact command, checksums.
- **Evaluation report** — metrics by hop/format/mode.

### Evidence and reproducibility

- **Cite stable anchors, not lines.** When you cite code or another doc for evidence, use
  `path::symbol`, a heading/anchor (e.g. `docs/fine-tuning/pipeline/04-sft.md#requirement`),
  a stable id (`(ADR-0NNN)`), or an artifact path — never line numbers. The logic docs
  themselves describe behaviour in words; they do not mirror code or cite per sentence.
- **Reproducibility.** Every result names its environment pin, seed, dataset revision, and
  exact command.
- **No silent data loss.** Rejected/filtered rows and failed runs are recorded.
- **Assumptions are marked** (`[unknown]`, `[unverified — needs <env>]`), never asserted.

### ADRs

- `docs/adr/NNNN-slug.md`, one decision per file, status/context/decision/consequences.
- Referenced inline everywhere as `(ADR-0NNN)`; grep must find the reference.
- Adopted from product-launch: high ROI, keeps docs from sprawling and always
  referenceable. ADRs are the durable *why*; pipeline docs point at them instead of
  restating rationale.
- **ADRs are forward-looking.** Do not retrofit a clean architecture onto vibecoded code.
  Record decisions we actually make. For the frozen dataset generator, document behaviour
  *descriptively* in the pipeline docs; the only ADRs there are "we freeze X" and
  deliberate keep-as-is choices. For fine-tuning (being revised), write ADRs as new
  decisions land. Where existing intent is genuinely unknown, mark `[unknown]` — never
  invent a rationale.

### Local decisions (`decisions.md`)

- Smaller-scope units keep a local `decisions.md` recording that unit's decisions in the
  **same format as ADRs**.
- For `pipeline/` steps, the local decision record lives **in the step file itself**, in
  ADR format, and is linted by the same checker as `decisions.md` and `docs/adr/`.

### Glossary

- `docs/glossary.md` — canonical term → meaning (+ optional why-used), plus a **Don't-say**
  table of banned/vague terms (a ratchet: seeded, then trimmed only by engineering the term
  out of docs and code). Enforced: terms used in docs must be defined; no invented
  synonyms; bad terms fail lint.
- Aligns with the ubiquitous-language practice; CAD-QA/CADEdit ontology terms get entries.
- A **legacy-term audit** (see terminology discipline) enumerates the misleading terms in
  the existing docs/code and resolves each: a real glossary entry, a rename, or a
  Don't-say.

### Terminology discipline (human readability)

The existing docs and code were written by an agent prone to *sloppy* naming: terms
mislabeled, overclaimed, incorrect, conflated, or unspecific, applied to many different
objects. The owner could not read the docs without stopping to ask "what is this?", and
internalizing that language made thinking clearly about the project harder. This is a
primary reason for the restructure. The bar is blunt: **the owner reads a doc without
pausing to ask what a term means.**

Rules:

- **One concept, one word.** A term names exactly one thing; a thing has exactly one term.
  Two concepts sharing a word → split it; one concept with two words → pick one.
- **Precise and scoped.** No unspecific placeholders ("the object", "the value",
  "the pipeline") where a named concept exists.
- **No overclaiming.** Describe what is verified, or mark it (`exists`, `[unverified]`).
  Never assert behaviour a check has not confirmed.
- **No conflation.** Do not reuse a term for a related-but-different concept; name the
  distinction. Model: product-launch `00-stage-interfaces.md`'s "the two failing-units are
  different and both named".
- **Defined or banned.** Every load-bearing term has a glossary entry; every bad term is on
  the Don't-say list and fails lint.
- **A term that needs a follow-up question is a defect** — reported like a bug, not
  tolerated.

### Docs conventions

- `docs/docs-conventions.md` — the meta doc encoding the whole structure: directories,
  filenames, required sections, ADR/decisions/glossary rules, status and priority markers,
  and what the lint enforces.
- Modeled on `~/Work/business/placis/.../docs-conventions.md` (that repo is a CRUD API and
  does not transfer directly; the *conventions doc* idea does).
- Cross-references name the target by heading/anchor or stable id
  (`.../04-sft.md#requirement`, `(ADR-0NNN)`) — never by line number, so links survive
  edits. Headings are therefore part of the interface: rename deliberately, and keep
  anchors stable.
- Markdown is formatter-enforced (`rumdl`; see lint above), so docs stay consistently
  shaped and diffs stay clean.

### Workstreams

- Multiple workstreams get **separate PRDs**. CAD-QA is the main workstream; CADEditQA (if
  alive — see D7) gets `docs/research-scopes/cadedit/PRD.md` (product-launch precedent:
  `research-scopes/` held distinct research styles).
- Otherwise keep docs lean: one PRD per workstream, not per idea.

### Pipeline ↔ code mapping

- Pipeline docs are numbered steps (`NN-<slug>.md`, optionally `NNx`) and must map 1:1 to a
  code stage (product-launch `manual-workbook/` precedent: a code-experimentation folder
  mapped numbered pipeline steps to runnable scripts — very useful).
- A doc step with no code, or code with no doc, is a finding.
- Where a runnable mapping helps, keep a code-experimentation folder whose scripts mirror
  the step numbers.

### Document layers and single-source rule

Docs are layered by role — not deduplicated into nothing. Following the `redo/` convention
(`pipeline/` = authoritative WHY; `pipeline/streamlined/` = terse executable WHAT;
`00-stage-interfaces.md` = the IO contract):

- **WHY / authoritative** — rationale, decisions, constraints, known holes. Lives in
  `docs/adr/` and each step doc's decision sections.
- **WHAT / mechanics** — a terse, flow-ordered description of how a step behaves
  (Purpose / IO / Requirement, or `READ → TRANSFORM → WRITE`). This *is* a deliberate
  restatement of behaviour, and it is valuable: an implementing agent can follow it and a
  test can assert it. Do not fear restating behaviour; fear uncontrolled duplication.
- **CONTRACT / IO** — one stage-interface doc per pipeline is the single source for what
  flows between steps (artifact + field names); step docs must match it (redo
  `00-stage-interfaces.md`).
- **STATUS** — `verified` / `exists` / `missing` / `stale` tags plus verification commands.

The single-source rule: every fact has exactly one home. Step docs may restate behaviour,
but they point at ADRs for the *why* and at the IO contract for names — they never copy
rationale or redefine field names. Where two docs overlap, one is the source and the other
links.

Whether CAD-QA needs a separate terse WHAT layer (a `streamlined/`-style folder) or the
step-doc template already covers it is open — see D14.

### Writing method

Keep it simple. Authoritative docs describe **logic and decisions** (like product-launch
`pipeline/`), not code: code churns, and by the end only the logic and the decisions still
matter. So:

1. **Describe.** Write what the step does and why, in domain terms. Cite a `path::symbol`
   or heading only when it genuinely helps; never mirror code or cite per sentence. Mark
   anything unconfirmed with a status tag (`exists` / `missing` / `stale` /
   `[unverified — needs <env>]`).
2. **Verify is the audit, not the writing pass.** The heavy checks (oracle, parity,
   sandbox, CLI) are Phase 0. Passing upgrades a tag to `verified`; failing records a `bug`
   with a reproduction.
3. **Conflicts are findings.** A doc/code disagreement is recorded; fix whichever is wrong
   (ADR / local decision).

Boundary: no silent intent changes; plausibility ≠ correctness; research semantics are the
owner's; delegated exploration, directly-verified load-bearing claims.

### Open and resolved questions

- Every doc that carries uncertainty has `## Open questions` and, once something is
  settled, `## Resolved questions`.
- Resolving a question **moves** it from Open to Resolved with the resolution and date; it
  is never deleted. State only moves forward.

### Lint and ratchets (D8)

- Port the product-launch linters: docs, glossary, ADR/decisions, and code — plus ratchets
  (monotonic thresholds that only improve). They did their job and gave high ROI.
- The doc/glossary/ADR/decisions linters are in scope. Code lint and ratchets apply where
  they do not fight the `cad_qa/` freeze: documentation and the `train_and_eval/` surface
  first; heavy linting of the frozen dataset-generation code is deferred.
- **Markdown formatting.** Adopt a formatter for all docs — `rumdl` (preferred: stricter
  and faster) or `mdformat`. Committed config; runs in the same gate as the linters. No
  Markdown formatter or CI config exists in the repo today, so this is created from
  scratch.

## Prior-art code mining

Literature review is done (see the paper). What is missing is **code/implementation prior
art**: many researchers have already built efficient LLM training / RL pipelines and open
reasoning datasets. We should mine those rather than hand-roll.

- Before writing or rewriting the fine-tuning pipeline, survey established open-source
  training stacks and pick one to learn from / build on, rather than starting from our
  vLLM-hack + hand-rolled GRPO.
- Candidate sources to evaluate (verify current state): HuggingFace `trl` examples,
  `alignment-handbook`, `smol-course`; `Open-R1` (R1 reproduction); `open-instruct` /
  Tulu 3; `OpenThoughts` / `Bespoke-Stratos` reasoning-data pipelines; `unsloth`
  notebooks; `Axolotl`; `LLaMA-Factory`; `torchtune`; `verl` (RL).
- Record findings in `docs/prior-art.md`: per source, what they do, what we adopt, and
  what we deliberately reject (with an ADR for the base-pipeline choice, D11).
- Goal: a correct, efficient, reasoning-preserving pipeline we understand — not the
  fastest way to a number.

## Repo and code structure

CAD-QA is the paper, and the repo *is* CAD-QA, so all code nests here; the generation package
is `dataset/` (not `cad_qa/`, which would repeat the paper name). Two top-level code packages,
coupled one way only by the rows I/O contract:

- `dataset/` — **generation only** (rename of today's frozen `cad_qa/`): `source.py`,
  `trace.py`, `ontology/`, `query/`, `prompts/`, and the materialize→validate→release→export
  subpackage. See Code-change policy.
- `train_and_eval/` — **all** training and evaluation logic (being revised), including the
  answer grader and the Harbor runner/grader.

Rules:

- **The move is P1** — do it now.
- **Folder fan-out CI is P2** — a "no directory > ~10 entries" check, ratcheted down, built
  only if the tree actually needs it.
- File length: aim small and split by responsibility. The 800-line rule is advisory here
  ("to hell with 800 lines"), not blocking.
- Coupling is one-way: `train_and_eval/` consumes `dataset/` outputs through the documented
  rows I/O contract (the rows artifact + answer contract) only; `dataset/` never imports
  `train_and_eval/`.
- Naming: code package directories use underscores (`dataset`, `train_and_eval`) — Python
  import names. Hyphens are for docs only (`docs/fine-tuning/`).

Moves:

- `cad_qa/` → `dataset/` (package rename; the `cadqa = cad_qa.cli:main` entrypoint and every
  `cad_qa.*` import rewired).
- `cad_qa/evaluation/` → `train_and_eval/grading/` — it is eval logic (`grade`/`parse`/
  `baselines`/`requests`/`tool_assisted`/`closed_book`), and the generation pipeline never
  imports it.
- `cad_qa/dataset/` → a clearer name than `dataset/dataset/` (it is the release/export stage):
  `dataset/release/`, or split `materialize/` + `release/`.
- Eval CLI and the Harbor runner/grader move to `train_and_eval/`; the Harbor *task export*
  stays in `dataset/`. The `cadqa` CLI becomes a cross-package orchestrator (or a train/eval
  CLI is added).
- Open: `query/` is vague — consider `gold_query/` or `query_synthesis/`.

The move is mechanical (move + import fixes), so it does not violate the dataset-generation
freeze: it changes where code lives, not what it computes. Precedent: the RunAudit
`docs-restructure` plan
(`RunAudit/.worktrees/docs-restructure/runaudit/plans/clarify-docs-structure.md`).

## 1. The problem this restructure fixes

Two documentation trees grew independently and now overlap and drift:

- `specs/` — normative intent (`paper-spec.md`, `dataset-spec.md`,
  `benchmark-task-spec.md`, `cadedit-*.md`, `research-experiment-spec.md`, …).
- `docs/` — status, runbooks, experiments
  (`implementation_status.md` is 1,774 lines; `agent_handoff_2026-08-09.md`; RL
  checkpoints; `harbor.md`; `text_finetune_runbook.md`; `experiments/`).

Neither tree states, in one place, **what each pipeline step must do and whether it
currently does it**. The codebase is undocumented as *executed behaviour*: `specs/`
describes intent, but nothing demonstrates behaviour. For a Master's thesis we need four
things the current docs do not separate cleanly:

1. **Intent** (PRD): research questions, claims, deliverables, evaluation contract.
2. **Requirements per pipeline step**: purpose, inputs/outputs, the requirement, and
   intended-vs-verified status with a verification command.
3. **Development context**: history and the as-of snapshot (proven vs assumed).
4. **Development plan**: the phased route to completion.

## 2. Target `docs/` structure

```text
docs/
  README.md                     # doc map + how to use it
  docs-conventions.md           # the meta doc (see conventions above)
  PRD.md                        # product/research requirements
  glossary.md                   # canonical terms (enforced)
  development-context.md        # history + as-of snapshot (proven vs assumed)
  development-plan.md           # phased plan to completion
  prior-art.md                  # mined open-source training/RL/data pipelines
  research/
    README.md                   # external study notes + citations
    YYYY-<slug>.md
  paper/
    CA2_Riabov_final.{md,tex}   # the manuscript (excluded from the Don't-say lint)
  adr/
    NNNN-<slug>.md              # one decision per file; `(ADR-0NNN)` referenced inline
  research-scopes/
    cadedit/PRD.md              # only if CADEditQA is alive (D7)
  dataset/
    README.md
    requirements.md             # intended-vs-verified tabular summary
    decisions.md                # local decisions (ADR format)
    pipeline/
      00-overview.md
      01-source-ingestion.md    # split into subletters when a stage grows (01a, 01b, …)
      02-trace-snapshot.md
      03-ontology-graph.md
      04-query-synthesis-resolver.md
      05-prompt-rendering.md
      06-materialize-validate-release.md
      07-exports-harbor-sft.md
  fine-tuning/
    README.md
    requirements.md
    decisions.md                # local decisions (ADR format)
    pipeline/
      00-overview.md
      01-rows-loader.md
      02-teacher-sampling.md
      03-trace-normalization.md
      04-sft.md
      05-grpo.md
      06-harness-modes.md
      07-serving-vllm.md
  evaluation/
    README.md
    harness.md
    baselines.md
```

Notes:

- **`specs/` is superseded (D2).** Split its contents into the new `docs/` structure per
  these conventions (semantics → PRD/pipeline docs, terms → `glossary.md`, decisions →
  `adr/`), then leave `specs/` as a pointer or remove it.
- **`implementation_status.md` is removed (D3).** It was a vibecoded status log with no
  ongoing purpose; the new docs replace it. Handoffs and runbooks are kept as raw
  material and superseded with a pointer at the top of each.
- Design rationale lives in ADRs and each pipeline's `00-overview.md`, not a separate
  methods doc (D4).
- Pipeline stages use `NN-<slug>.md` and may split into subletters when a stage grows
  (`01a`, `01b`, `04c`, `04d`, …). A stage that is one file needs no letter; a stage that
  splits keeps the numeric prefix and adds a letter per part.
- Per the priority-tier rule, any doc may carry a trailing `## Extra deliverables - P2`
  block for the good-venue version of that step.

## 3. Doc specifications

### `docs/README.md`
- Doc map, how to navigate, and where to start for a new contributor.

### `docs/docs-conventions.md`
- Encodes §2 + the conventions section: naming, required sections, ADR/decisions/glossary
  rules, Open/Resolved question handling, priority/status markers, anchor-based
  cross-references, the Markdown formatter (`rumdl`), and the lint/ratchet target list.
  Written first, because everything else follows it.

### `docs/PRD.md` (product / research requirements)
- One-sentence intent; primary + secondary research questions; claims/contributions;
  deliverables; evaluation contract (closed-book primary, three harnesses, metrics,
  targets); scope boundaries; definition of done; non-goals.
- Source material: `CA2_Riabov_final.tex`, `specs/paper-spec.md`,
  `specs/research-experiment-spec.md`, `human-paper-spec.md`.

### `docs/glossary.md`
- Canonical terms used across PRD / pipeline docs (e.g. hop count, selector, workplane,
  material/void region, candidate trace, harness mode, rejection sampling). Enforced by
  the same lint as ADRs/decisions.

### `docs/development-context.md`
- The as-of snapshot + history, plus a proven-vs-assumed list. Content is drafted in §6
  below; it should be essentially ready to write.

### `docs/development-plan.md`
- The phased route to completion; derived from the plan in §7.

### `docs/prior-art.md`
- Code/implementation prior art: established training / RL / data pipelines, what we adopt
  and what we reject. Feeds `docs/fine-tuning/` and the base-pipeline ADR (D11).

### `docs/adr/`
- Created on demand as decisions land. First ADR candidates: dataset scope (D6), model
  choice, reasoning-preserving training design, ADR/decisions/glossary lint adoption.

### `docs/research-scopes/`
- Per-workstream PRDs. Only CADEditQA is a candidate today (D7).

### Per-pipeline docs
Each pipeline step doc follows the same template (§4) and is grounded in code refs.
- `00-overview.md` per pipeline holds the DAG and the **stage IO contract** — the single
  source for artifact/field names between steps; step docs must match it (redo
  `00-stage-interfaces.md` convention).
- Dataset pipeline: A1–A7 (source → trace → graph → query → prompts → materialize →
  exports).
- Fine-tuning pipeline: B1–B7 (rows → teacher → normalize → SFT → GRPO → harness →
  serving).
- Evaluation: `harness.md` (three modes + Harbor; primary = `numpy`), `baselines.md`
  (big-model runs).

## 4. Pipeline doc template

Every `pipeline/` stage doc (named `NN-*.md` or `NNx-*.md`, e.g. `01-rows-loader.md`,
`04a-*.md`) must contain, in order:

1. **Purpose** — one sentence.
2. **Inputs / outputs** — typed artifacts (name + producer); must match the
   `00-overview.md` stage IO contract exactly.
3. **Requirement** — what must be true for the downstream claim to hold.
4. **Current status** — `verified` | `exists` | `missing` | `stale`, with evidence
   (`path::symbol`, artifact path).
5. **Verification** — the exact command that would make it `verified`.
6. **Local decisions** — decisions scoped to this step, in ADR format (linted by the same
   checker as `decisions.md` and `docs/adr/`).
7. **Open questions** — unknowns, decisions, blockers.
8. **Resolved questions** — settled items moved here with resolution + date (never
   deleted).
9. **Extra deliverables - P2** (optional) — the more ambitious version of this step.

## 5. Source material to migrate

| New doc | Primary sources |
|---|---|
| `docs/PRD.md` | `.tex`, `specs/paper-spec.md`, `specs/research-experiment-spec.md`, `specs/dataset-spec.md`, `human-paper-spec.md` |
| `docs/glossary.md` | `specs/*.md`, the paper, `cad_qa/` ontology/query modules |
| `docs/development-context.md` | §6 below; `docs/_archive/agent_handoff_2026-08-09.md`, `docs/_archive/rl_*.md`, `docs/experiments/2026-08-08-*` |
| `docs/development-plan.md` | §7 below |
| `docs/prior-art.md` | External — open-source training / RL / data pipelines (mined, cited) |
| `docs/dataset/*` | `docs/_archive/implementation_status.md`, `specs/dataset-spec.md`, `specs/benchmark-task-spec.md`, `specs/multi-hop-qa-task-spec.md`, `README.md`, `docs/_archive/experiment_execution_runbook.md`, `cad_qa/` |
| `docs/fine-tuning/*` | `docs/_archive/agent_handoff_2026-08-09.md`, `docs/_archive/rl_*.md`, `docs/_archive/text_finetune_runbook.md`, `train_and_eval/` |
| `docs/evaluation/*` | `docs/_archive/harbor.md`, `cad_qa/harbor.py`, `cad_qa/evaluation/`, `docs/experiments/2026-08-08-gemma-e2b-bench.md` |

## 6. Development context (draft; becomes `docs/development-context.md`)

**Repo identity.** Remote `https://github.com/MRiabov/CAD-QA.git`. Primary checkout on
`main` at `512a514` (2026-08-09). **Local `main` is ahead of `origin/main` (`e89838d`,
2026-08-08)** — the entire Aug 8–9 RL/SFT push is committed locally but never pushed.

**History (condensed).**

| When | What | Artifact |
|---|---|---|
| 2026-04-29 | Graph-first reset; one ontology + deterministic query/verifier | `overnight-task.md`, rewritten `specs/`, `epics-and-stories.yaml` |
| 2026-05→06 | Dataset builder: source, trace, graph, query, prompts, release gates | `cad_qa/`, `docs/_archive/implementation_status.md` |
| 2026-06→07 | Harbor export, Daytona, provider pinning | `cad_qa/harbor.py`, `docs/_archive/harbor.md` |
| 2026-08-08 | gemma-4-E2B baseline: rc10 (0-hop) 30%, release10k (2–5 hop) 14% | `docs/experiments/2026-08-08-gemma-e2b-bench.md` |
| 2026-08-08/09 | Teacher sampling, SFT, native format fix, 1-hop bridge, `run_code`, harness modes, vLLM | `train_and_eval/`, `docs/_archive/rl_*.md`, `docs/_archive/agent_handoff_2026-08-09.md` |
| 2026-08-09 | Last commit | `512a514` |

**Components.** Dataset/benchmark stack in `cad_qa/` (source, trace, ontology, query,
prompts, dataset, harbor, cli). Fine-tuning stack in `train_and_eval/` (rows_loader,
tool_calls, teacher, rejection_sample, normalize_traces, sft_train, grpo_train,
eval_bench, convert_for_vllm). HF data `MRiabov/cadqa-rl-2000`: `v2/v3_curriculum` (1,445
rows), `sft_traces_v1` (275), `sft_traces_v2` (308).

**Proven.** Base gemma-4-E2B rc10 30/100, release10k 14/100. Native-format SFT 50% acc /
58.3% tool-valid on 12 held-out rows (non-native 16.7% on the same rows). Post-fix re-run
41.7% / 75% on the same 12 rows. Big-model Harbor rc10 clean-100: Mimo 65% / DeepSeek 63%
/ Kimi 59% (0-hop, easy).

**Assumed / unverified.** vLLM "solved" (loads a hand-converted checkpoint; no
transformers-vs-vLLM parity check). SFT reasoning-preserving (4 epochs, 268 traces, no
masking evidence; eval over-generated, GRPO went to 2-token completions, entropy ≈ 0).
Grader correctness beyond the oracle path. `run_code` sandbox isolation. The 1,445-row
curriculum as "ready" (it does not pass the repo's `benchmark-release` gates). Hard-slice
(3+ hop) big-model numbers meeting the ≤30% target.

**Gaps / risks.** Trust gap (primary); dataset scale vs spec's 10,000; reasoning
collapse; serving correctness; missing orchestrator (`scripts/`/`configs/` absent at
HEAD, so the run-experiments skill is stale); environment rot; paper has no results.

**Environment.** No live GPU box; last box and checkpoints gone `[assumed]`. `uv` +
Python 3.12 (`uv.lock`). `.env` local `[assumed]` OpenRouter key.

## 7. Development plan (draft; becomes `docs/development-plan.md`)

Phases are ordered so no GPU budget is spent before verification. Each has a gate, and a
priority (`P0`/`P1`/`P2`) per the tier rule above.

- **Phase 0 — Trust audit (no GPU). [P0]** Audit every pipeline step in §5; write a
  pass/fail + verification command for each. Priority: grader/oracle, `run_code` sandbox,
  vLLM parity, SFT masking, rows loader. Consolidate one runnable command per stage.
  Re-run the 12-row SFT eval. Gate: every load-bearing component is `verified` or
  explicitly `blocked`.
- **Phase 0a — Repo structure (mechanical). [P1; fan-out check P2]** Rename `cad_qa/` →
  `dataset/`; move `cad_qa/evaluation/` → `train_and_eval/grading/`; rename the inner
  `cad_qa/dataset/` (it is the release/export stage); move the eval CLI and the Harbor
  runner/grader to `train_and_eval/`. Keep the rows I/O contract as the only coupling. Folder
  fan-out CI is P2.
- **Phase 0b — Prior-art code mining. [P1]** Survey established open-source training / RL /
  data pipelines; record findings in `docs/prior-art.md`; pick a base pipeline to build on
  (ADR, D11). Gate: adoption decision recorded before Phase 3 design.
- **Phase 1 — Freeze the benchmark. [P0; the ≥10k tier is P2]** Decide dataset scope
  (freeze 1,445 + new held-out test, or regenerate ≥10,000); build/freeze a group-safe
  held-out test; close the 0/1-hop synthesis gap; fix json/number teacher coverage;
  publish with tagged revision hashes.
- **Phase 2 — Refresh baselines. [P1; only the primary `numpy` harness, `no_tools`/mode-3
  are P2]** Big models on the primary `numpy` harness on the hard slice; log every call;
  grade with the audited grader.
- **Phase 3 — Reasoning-preserving training. [SFT P0; GRPO P1]** Design first (an ADR +
  the pipeline `00-overview.md`): constrained decoding for format, prompt-masked SFT if
  used, on-policy RL with shaped reward and a 0→1→2→3→5 curriculum. Canary before scale;
  monitor entropy/length/reward.
- **Phase 4 — Evaluation and analysis. [core P0; P2 modes optional]** base/SFT/RL on the
  primary `numpy` harness × hop/format (plus `no_tools`/mode-3 as P2); learning curve;
  error taxonomy.
- **Phase 5 — Write. [thesis P0; venue-grade paper P2]** Fill the `.tex` with real numbers;
  verify citations; add the audit as the thesis validation appendix.

## 8. Decisions / open questions

Priority tiers (P0/P1/P2) are defined above. Questions move from Open to Resolved when
settled (same rule as the per-doc sections).

### Resolved

- **D1 — Work surface.** This docs thread works in the **primary checkout** (sequential and
  blocking, so no worktree spam). General rule: D9.
- **D2 — `specs/`.** **Supersede and split.** Fold `specs/` into `docs/` per these
  conventions; leave a pointer (or remove).
- **D3 — `implementation_status.md`.** **Remove.** No ongoing purpose; the new docs
  replace it.
- **D4 — `methods.md`.** **Dropped for now.** Design rationale lives in ADRs and each
  pipeline's `00-overview.md`; reintroduce a methods doc only if a real need appears.
- **D5 — Doc style reference.** Use the **`redo/` folder** (and `plans/`), not all of
  `math.nyle.ai` — the rest of that repo's docs are dirty; `redo/` is the clean exemplar.
- **D6 — Priority of the ≥10k tier.** **P2.** Whether we build it depends on how optimal
  inference/fine-tuning turns out.
- **D7 — CADEditQA.** **P2 either way.** Confirm whether it is actually alive; if alive it
  gets `docs/research-scopes/cadedit/PRD.md`.
- **D8 — Lint.** **Port** the product-launch linters (docs, glossary, ADR/decisions, code)
  and ratchets; add a Markdown formatter (`rumdl` preferred, else `mdformat`). No
  formatter or CI config exists in the repo today.
- **D9 — Delivery.** The owner states the mode when needed; there is no standing policy.
  Default is worktrees; **blocking work (like this docs thread) stays in `main`**.
  Worktrees are a means to an end, not important in themselves.
- **D10 — Harness priorities.** **`numpy` is the primary harness (P0)**; `no_tools` and
  full-CadQuery ("mode-3") are both **P2** (strict-reasoning and tool-assisted upper
  bounds). Mode-3 is implemented nowhere yet.
- **D13 — Repo/code structure.** CAD-QA is the paper and the repo is CAD-QA, so the generation
  package is **`dataset/`** (rename of `cad_qa/`; not `cad_qa/` or `dataset_generation/`), a
  sibling of **`train_and_eval/`**. `dataset/` is **generation only**; **all** training and
  eval logic — `cad_qa/evaluation/` → `train_and_eval/grading/`, the eval CLI, and the Harbor
  runner/grader — moves to `train_and_eval/`. Coupling is one-way: `train_and_eval/` consumes
  `dataset/` through the rows I/O contract; `dataset/` never imports `train_and_eval/`. Folder
  fan-out CI and file-length rules are **P2**.

### Open

- **D11 — Base pipeline to adopt.** Which established open-source stack do we build the
  fine-tuning pipeline on (TRL / Open-R1 / unsloth / `liquid-finetune` / verl / other), after
  prior-art mining? Findings are recorded (`docs/prior-art.md`); the adoption **ADR is still
  owed**.
- **D12 — Writing method.** Confirm the evidence-first, two-pass writing method and the
  status-tag vocabulary in "Doc standards and conventions" (writing vs verifying vs the
  owner's research judgement).
- **D14 — WHAT layer.** Add a terse, runnable WHAT layer per pipeline (a
  `streamlined/`-style folder: DAG + `READ/TRANSFORM/WRITE`, no rationale), or is the
  step-doc template sufficient?

## 9. Acceptance criteria for this restructure

1. `docs/` has the structure in §2, with a `docs/README.md` map and a
   `docs/docs-conventions.md`.
2. Every pipeline step has a doc with the §4 template, including a status, a verification
   command, a local-decisions section, and Open/Resolved questions.
3. `docs/PRD.md`, `docs/glossary.md`, `docs/development-context.md`,
   `docs/development-plan.md` exist and are consistent with each other.
4. ADRs exist for the landed decisions and are referenced inline as `(ADR-0NNN)`.
5. Superseded docs carry a pointer to their replacement (`specs/` folded; 
   `implementation_status.md` removed).
6. The docs contain no unmarked assumptions: everything is evidence or `[unverified]`;
   evidence cites `path::symbol`, never line numbers.
7. P2 extras are collected in per-doc `## Extra deliverables - P2` blocks and are never
   treated as P0/P1 commitments.
8. Resolved questions are moved, not deleted, in every doc that had an Open section.
9. The ported lint (docs / glossary / ADR / decisions + ratchets) runs and gates changes.
10. `docs/prior-art.md` records the surveyed pipelines and the base-pipeline adoption
    decision (ADR, D11).
11. **Readability:** the owner can read a doc without pausing to ask what a term means;
    every load-bearing term is defined or on the Don't-say list; no term names two concepts.

**Status (2026-10-08).** Met: 1, 2, 3, 7, 8. Partial: 5 (`implementation_status.md` removed,
`specs/` not folded), 6, 10 (findings recorded; D11 ADR pending), 11 (prose swept to 0;
identifier backlog parked as P2). Not met: 4 (`docs/adr/` absent), 9 (only the Don't-say
checker/ratchet of D8 exists).

## 10. Immediate next step

Write `docs/docs-conventions.md` first (everything else follows it), then `docs/README.md`,
`docs/PRD.md`, `docs/glossary.md` (with the legacy-term audit and Don't-say seed — it lands
early because terminology gates every later doc), and `docs/development-context.md`; then
the dataset pipeline docs, then fine-tuning.
