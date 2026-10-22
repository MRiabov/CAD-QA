# Scratch experiment: can a frontier LLM model write CadQuery queries, by hop count?

**Status:** plan, 2026-10-22. A disposable experiment, not a dataset release. It decides whether
the kernel-query pivot (`docs/dataset/requirements/PRD.md`, KI1) has headroom, and it tests the
query-chain idea on real CADEvolve programs before any spec is rewritten.

## Question

Given a CadQuery program and a natural-language question, can `deepseek/deepseek-v4.1-flash-1017`
(OpenRouter, $0.30 / $1.20 per million input/output tokens) write a CadQuery query that, run after
the program, produces the right answer? How does accuracy fall as the hop count rises from 1 to 10?

## Scope

- 300 tasks: 30 per hop count, 1–10.
- About 60 programs from the existing 2026-10-19 regeneration (`runs/regen_1300_traced_20261019/`):
  `sources.parquet`, `traces_combined.parquet`, and `graph/graphs/*.parquet`. The extracted data is
  imperfect, so the graph only *proposes* tasks. The CadQuery kernel computes every gold answer.
- One model and one sample per task, with no execution feedback (single shot, one tool call).
- Out of scope: training, other models, release gates, and task-structure spec changes.

## Definitions

**Query chain.** A task is a chain of set operators over CadQuery entities, ending in one
aggregate. Every operator compiles to CadQuery code, so the chain is also the gold query.

**Hop.** One operator in the chain that changes the result. The final aggregate is not a hop.
Sub-chains that resolve a reference entity add their hops to the total. Each hop must be
*necessary*: removing it must change the kernel-computed answer, otherwise the task is rejected.
This makes "hop count" mean "reasoning steps the query actually needs".

### Operators (hops)

| Operator | Meaning, rendered in words | CadQuery form | Graph source used for proposal |
|---|---|---|---|
| `state_of` | the part as it was after a given operation, not the final part | the program variable at that step | `operation`, `before`/`after`, trace snapshots |
| `axis_extreme` | topmost / leftmost / ... | `faces(">Z")`, `edges("<X")` | `selected_by`, bbox measurements |
| `axis_orientation` | vertical / horizontal / facing +Y | `"\|Z"`, `"#Z"`, `"+Y"` | `parallel_to`, `perpendicular_to` |
| `geom_type` | circular / straight / planar / cylindrical | `"%CIRCLE"`, `"%LINE"`, `"%PLANE"` | edge and face kinds |
| `traverse` | edges of / faces bordering / faces adjacent to | `.edges()`, shared-edge filter | `adjacent_to`, `contained_in`, `endpoint_of` |
| `relate_to_ref` | parallel / perpendicular / opposite to a reference entity | normal and direction comparison | `parallel_to`, `perpendicular_to`, `opposite_to` |
| `compare_to_ref` | longer / shorter / same length as a reference | a length or area filter | `longer_than`, `shorter_than`, `same_length_as` |
| `rank` | largest / smallest / nearest to the origin | `max(..., key=...)` | measurements |
| `created_by` | faces made by the operation on line N | before/after state difference by `isSame` | `created_by`, operation effects |

**Aggregates** (exactly one per task, not a hop): count; total length or area; a single
measurement of a size-1 set (area, length, radius, or a centroid coordinate); the minimum distance
between two resolved sets.

**Hop 1–10 construction.** Short chains (1–4) are a target chain only. Longer chains (5–10) add one
or two reference sub-chains (`relate_to_ref`, `compare_to_ref`, distance). Chains are built by a
seeded random walk per program. At each step, the kernel checks that the candidate set is non-empty,
smaller than the previous set (for filters), and at most 50 entities.

## Pipeline (scratch code in `experiments/cq_query_scratch/`)

1. **Select programs** (`select.py`). Pick programs whose trace succeeded and whose final part has
   at least 8 faces. Stratify across CADEvolve-C/P and the ABC/ShapeNet/core collections; 60
   programs, seed 20261022.
2. **Generate tasks** (`chain.py`, `generate.py`). For each hop count, propose chains from graph
   relations and compile each to gold CadQuery. Execute the program once per worker and cache the
   shapes. Keep a task only if:
   - the gold query executes;
   - every hop passes the necessity check;
   - the answer is finite.

   Cap tasks at 5 per program per hop count, and sample 30 per hop count. Where the graph has a
   comparable value, log whether the graph and the kernel agree; this measures graph quality as a
   by-product.
3. **Render the question** from the chain with rule-based templates. The question never contains
   selector strings (`>Z`, `%CIRCLE`) or variable names the model could copy, so the task is not
   string translation. It may cite a line number for `created_by`/`state_of`.
4. **Prompt.**
   - **System prompt:** the role, plus a fixed CadQuery cheat sheet (selector grammar, `.vals()`,
     `Area()`, `Length()`, `radius()`, `Center()`, `distance`). Any later model sees the same sheet.
   - **User prompt:** the program, the question, and the contract. One `submit_query(code: str)`
     tool call; the code runs after the program in the same namespace and must assign a number to
     `answer`.
5. **Call the model** (`run_eval.py`). Reuse `train_and_eval/teacher.py::TeacherClient` with
   `model="deepseek/deepseek-v4.1-flash-1017"`, temperature 1.0 and top-p 0.95 (model card), and a
   native `tools=[submit_query]`. Check `balance()` before each stage. Write one JSONL record per
   call holding the reasoning, the visible content, the raw tool calls, tokens, cost and latency.
   Resume by `task_id`.
6. **Execute and grade.** Run `program + query` in a subprocess with CadQuery, a 60 s timeout, a
   memory rlimit, and no network. Grade with 1e-3 relative / 1e-6 absolute tolerance for floats and
   an exact match for counts. Flag `literal_answer` when an AST check shows `answer` assigned a bare
   number. The outcome is one of: `no_tool_call`, `exec_error`, `timeout`, `literal_answer`, `wrong`,
   `correct`.
7. **Report** (`report.py`). Produce a funnel per hop count:
   - generated → gold-verified → sampled → tool call returned → executed → correct;
   - accuracy with a Wilson 95% CI;
   - reasoning tokens, cost, and the `exec_error` subtypes (hallucinated API, selector syntax,
     other).

## Staged run (difficulty gates)

Each stage runs only after the previous one passes. A failed gate means: fix the generator, prompt,
or harness, then rerun the same stage.

| Stage | Tasks | Purpose |
|---|---|---|
| 0. Smoke | 5 tasks at hop 1 | End-to-end plumbing; about $0.01 |
| A | 30 at hop 3 | First real level |
| B | 30 at hop 5 | |
| C | 30 at hop 7 | |
| D | the remaining 210 (hops 1, 2, 4, 6, 8, 9, 10) | Fill in the full curve |

**Gate for stages A–C (a level "passes adequately"):**

- 30/30 gold queries verified, and all hops necessary.
- At least 95% of calls return a parseable tool call.
- Every failed task is triaged as a model error, a harness bug, or a gold/prompt bug. Zero harness
  or gold/prompt bugs may remain, since those are fixed and the level rerun.
- A manual read of 10 questions at this level finds them unambiguous.
- Model accuracy is **at least 50%**. This is the starting assumption; adjust it after stage A. If
  accuracy is below 50%, stop and check whether the failures come from question ambiguity or real
  difficulty before raising the hop count.

## Cost and time

About 300 calls × (~3k input + ~4k output tokens) ≈ $2 in total, with a hard stop at $5. Kernel
execution is CPU-only: about 600 subprocess runs (gold plus model), well under an hour on 8 cores.
Monitor the long runs every 3–5 minutes, not continuously.

## Code rules

Use typed Pydantic models: `ChainStep`, `QueryTask`, `ModelCall`, `GradeResult`, with `Field()`
constraints. Use StrEnums for `OperatorKind`, `AggregateKind` and `Outcome`, and stdlib `logging`
(the repo has no structlog). Keep modules under 800 lines. Read inputs with `dataset/io.py` record
readers. The scratch code is not imported by `dataset/` or `train_and_eval/`.

**E2E test** (`tests/test_cq_query_scratch.py`). Use a small fixture program and real CadQuery,
with only the LLM mocked. The test covers:

- generating chains at hops 1/3/5;
- the necessity check rejecting a no-op hop;
- the gold query grading `correct`;
- a literal answer grading `literal_answer`;
- the report funnel counts.

## Outputs

- Data (gitignored): `runs/cq_query_scratch_20261022/` holding `programs.parquet`, `tasks.jsonl`,
  `calls.jsonl`, `grades.jsonl`, and `report.md`.
- Record: `docs/experiments/2026-10-22-cq-query-scratch.md`, containing:
  - the funnel and accuracy tables per hop;
  - the failure taxonomy;
  - graph–kernel agreement;
  - cost;
  - five example tasks with model outputs;
  - a headroom verdict for the pivot.

## Decision this informs

- **Accuracy is high (≥ 90%) through hop 10:** writing queries is not the bottleneck. The pivot needs
  harder grounding (descriptive references, provenance) or becomes a dataset-only paper.
- **Accuracy falls steadily with hop count:** there is headroom, and the hop axis is a valid
  difficulty measure. Proceed to the spike in
  `~/.claude/plans/product-thesis-decision-and-a-rustling-snowflake.md` (base small model, more
  frontier models).
- **Accuracy is low already at hop 3:** check question wording and the cheat sheet before
  concluding anything.

## Known limitations

- 30 tasks per level gives a ±~18 percentage-point CI; this is enough to see a trend, not to
  separate close levels.
- One model, one sample.
- Rule-rendered questions are stilted.
- Model code runs in a subprocess, not a hardened sandbox; that is acceptable for a scratch run
  with a hosted model.
- No perturbation (test-suite) grading yet, so a coincidental correct answer can pass. The literal
  check covers only the cheapest cheat.
