# CadQuery-query scratch: one-shot and agentic query accuracy by step count

Date: 2026-10-22 · Status: completed for one LLM model, partial coverage. The run graded
198 of 300 planned tasks: steps 1, 3, and 9 are complete, step 5 has 18 of 60,
and step 7 was not run.

## Purpose

Test the kernel-query pivot (`docs/dataset/requirements/PRD.md`, KI1): given the
program text and a task, can an LLM model write a CadQuery query that returns the
gold answer? And how does accuracy change with the task reasoning step count?

## Setup

- LLM model: `deepseek/deepseek-v4.1-flash-1017` through Merge Gateway, reasoning
  effort `high`, temperature 0, one sample per task.
- Tasks: 300 planned at step counts 1, 3, 5, 7, and 9 (60 each). The run graded
  60 at step 1, 60 at step 3, 18 at step 5, and 60 at step 9.
- One-shot arm: no execution feedback; the LLM model makes one tool call and is
  graded on it.
- Agentic arm (step 9 only): up to 8 `run_code` calls that execute the query
  after the program, then a submit turn.
- Grading: integers exact; numbers and coordinates at `1e-3` relative with
  `1e-6` absolute fallback.
- Environment: Python 3.12.13, CadQuery 2.7.0, OCP 7.8.1.1, ruff 0.15.12;
  seed `cadqa-cq-scratch-20261022`; 80-program pool; `prompts.yaml` sha256
  `712c1bafde7732a2a124618a53f40ab7e78f26b5d65b988c3199f4230e4dfd9d`.
- Commands: `uv run python -m experiments.old.cq_query_scratch.cli pool`,
  `... generate --step-counts 1 3 5 7 9 --quota 60`, `... eval --step-counts ...`,
  `... report`.

## Results, one-shot arm

| Step count | Graded | Correct | Accuracy | Other outcomes |
|---|---|---|---|---|
| 1 | 60 | 60 | 100% | - |
| 3 | 60 | 60 | 100% | - |
| 5 | 18 | 18 | 100% | - |
| 9 | 60 | 38 | 63.3% | 19 `no_tool_call`, 1 `wrong`, 1 `exec_error`, 1 `timeout` |
| Total | 198 | 176 | 88.9% | |

Cost was $0.91 for 198 tasks: 306,479 prompt tokens and 1,699,138 completion
tokens.

## Agentic step-9 rerun

With up to 8 execution turns, step 9 reached 56/60 (93.3%): 2 `wrong` and
2 `exec_error`, no `no_tool_call`. Cost was $0.19 for 60 tasks.

## Interpretation

- **Steps 1, 3, and 5 saturate in the one-shot setting.** All 138 graded tasks at
  these levels were correct.
- **The one-shot step-9 drop is mostly submission discipline, not query
  writing.** 19 of the 22 failures at step 9 are `no_tool_call`: the LLM model did
  not emit a parseable tool call in one turn. The agentic rerun removed every
  one of those failures.
- **The remaining agentic failures are entity-selection errors.** Two wrong
  answers and two execution errors out of 60.
- This supports the view that the query task is easy for this LLM model at the
  graded levels, and that the interesting failures at high step counts are
  comprehension of the clue chain, not CadQuery API use.

## Limitations

- One LLM model, one sample per task, and a partial run: step 7 was not run and step
  5 has 18 of 60 tasks.
- The 80-program pool was selected with the old-graph final-face filter for
  comparability with the earlier experiment, so it over-represents flat,
  multi-face programs. The accuracy is not a random CADEvolve-C sample.
- The task construction grammar is local (`MC-08` is missing), so difficulty
  partly reflects the scratch grammar.
- The gold answers and the task facts come from the same extraction; an
  extraction bug propagates to both.
- The CadQuery arm uses process isolation, not a security sandbox.
- Wall clock is not a benchmark: kernel children are throttled to four.

## Artifacts

- One-shot: `runs/cq_query_scratch_20261022/` (`calls.jsonl`, `grades.jsonl`,
  `generation_stats.json`, `manifest.json`, `review.html`).
- Agentic step-9: `runs/cq_query_scratch_20261022/agentic_high/`.
- Abandoned OpenRouter partial: `runs/cq_query_scratch_20261022/archive_openrouter_partial/`
  (65 calls, 33 `api_error`; not used).
- Code: `experiments/old/cq_query_scratch/`.
- Plan: `plans/oct-22/cq-query-scratch-experiment.md`.

## Next steps (planned, not run)

1. Run step 7 and the remaining step-5 tasks.
2. Add a second API model and the small-LLM model panel.
3. Pair the query task against the no-kernel answer task on the same tasks
   (done separately for step 9 in
   [`2026-10-22-new-dataset-step9-eval.md`](2026-10-22-new-dataset-step9-eval.md)).
