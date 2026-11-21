"""Build a markdown report for the step-9 no-kernel evaluation."""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from experiments.old.new_dataset_eval_scratch.models import AnswerCall, AnswerGrade, Step9Outcome, TaskDefinition


def _pct(n: int, d: int) -> str:
    return f"{100.0 * n / d:.1f}%" if d else "n/a"


def _table(headers: list[str], rows: list[list[object]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    lines += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(lines)


def build_report(tasks: list[TaskDefinition], grades: list[AnswerGrade], calls: list[AnswerCall],
                 leaks: dict[str, str] | None = None) -> str:
    by_id = {t.task_id: t for t in tasks}
    grade_by_id = {g.task_id: g for g in grades}
    leaks = leaks or {}
    model = calls[0].model if calls else "unknown"
    provider = calls[0].provider if calls else "unknown"
    harness = calls[0].harness if calls else "unknown"
    total = len(grades)
    correct = sum(g.outcome == Step9Outcome.CORRECT for g in grades)
    outcomes = Counter(g.outcome.value for g in grades)
    cost = sum(c.cost_usd for c in calls)
    prompt_tokens = sum(c.prompt_tokens for c in calls)
    completion_tokens = sum(c.completion_tokens for c in calls)
    reasoning_tokens = sum(c.reasoning_tokens for c in calls)

    lines = [
        f"# Step-9 evaluation (`{harness}`): `{model}`",
        "",
        f"- Provider: `{provider}`",
        f"- Harness: `{harness}`",
        f"- Tasks graded: {total}",
        f"- Correct: {correct} ({_pct(correct, total)})",
        f"- Outcomes: {dict(sorted(outcomes.items()))}",
        f"- Tokens: {prompt_tokens} input, {completion_tokens} output, {reasoning_tokens} reasoning",
        f"- Reported cost: ${cost:.4f}",
        "",
        "## Accuracy by task target category",
        "",
    ]

    def grouped(key) -> list[list[object]]:
        groups: dict[str, list[bool]] = defaultdict(list)
        for g in grades:
            t = by_id[g.task_id]
            groups[str(key(t))].append(g.outcome == Step9Outcome.CORRECT)
        return [[name, len(vals), sum(vals), _pct(sum(vals), len(vals))]
                for name, vals in sorted(groups.items())]

    lines.append(_table(["Task target category", "Tasks", "Correct", "Accuracy"],
                        grouped(lambda t: t.target_category.value)))
    lines += ["", "## Accuracy by answer meaning", ""]
    lines.append(_table(["Answer meaning", "Tasks", "Correct", "Accuracy"],
                        grouped(lambda t: t.answer_meaning.value)))
    lines += ["", "## Accuracy by answer format", ""]
    lines.append(_table(["Answer format", "Tasks", "Correct", "Accuracy"],
                        grouped(lambda t: t.native_answer_format.value)))

    clean = [g for g in grades if g.task_id not in leaks]
    leaked = [g for g in grades if g.task_id in leaks]
    lines += ["", "## Literal-match subset", "",
              f"Tasks with a numeric literal matching the gold answer: {len(leaks)}. "
              "Counts are not flagged because small integers appear throughout the programs.",
              "",
              _table(["Subset", "Tasks", "Correct", "Accuracy"], [
                  ["All", len(grades), correct, _pct(correct, len(grades))],
                  ["No literal match", len(clean), sum(g.outcome == Step9Outcome.CORRECT for g in clean),
                   _pct(sum(g.outcome == Step9Outcome.CORRECT for g in clean), len(clean))],
                  ["Literal match", len(leaked), sum(g.outcome == Step9Outcome.CORRECT for g in leaked),
                   _pct(sum(g.outcome == Step9Outcome.CORRECT for g in leaked), len(leaked))],
              ])]

    clue_groups: dict[str, list[bool]] = defaultdict(list)
    for g in grades:
        t = by_id[g.task_id]
        for clue_type in sorted({c.clue_type.value for s in t.segments for c in s.clues}):
            clue_groups[clue_type].append(g.outcome == Step9Outcome.CORRECT)
    lines += ["", "## Task accuracy for tasks containing each clue type", ""]
    lines.append(_table(["Clue type", "Tasks", "Correct", "Accuracy"],
                        [[name, len(vals), sum(vals), _pct(sum(vals), len(vals))]
                         for name, vals in sorted(clue_groups.items())]))

    failures = [g for g in grades if g.outcome != Step9Outcome.CORRECT]
    lines += ["", "## Failures", ""]
    if not failures:
        lines.append("None.")
    else:
        rows = []
        for g in failures:
            t = by_id[g.task_id]
            rows.append([g.task_id, g.outcome.value, t.target_category.value, t.answer_meaning.value,
                         g.model_answer if g.model_answer is not None else "", g.gold_answer,
                         (g.message or g.error_type or "")[:120]])
        lines.append(_table(["Task", "Outcome", "Target", "Meaning", "Model answer", "Gold", "Detail"], rows))

    return "\n".join(lines) + "\n"


def read_report_inputs(tasks_path: Path, run_dir: Path):
    tasks = [TaskDefinition.model_validate_json(line)
             for line in tasks_path.read_text().splitlines() if line.strip()]
    grades = [AnswerGrade.model_validate_json(line)
              for line in (run_dir / "grades.jsonl").read_text().splitlines() if line.strip()]
    calls = []
    for path in [run_dir / "calls_round1.jsonl", run_dir / "calls.jsonl"]:
        if path.exists():
            calls += [AnswerCall.model_validate_json(line)
                      for line in path.read_text().splitlines() if line.strip()]
    return tasks, grades, calls
