"""Static HTML review page: one card per step-9 task, with both harness arms."""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from pathlib import Path

from experiments.old.new_dataset_eval_scratch.load import load_step9
from experiments.old.new_dataset_eval_scratch.models import AnswerCall, AnswerGrade, TaskDefinition

MAX_REASONING_CHARS = 20000
MAX_TOOL_RESULT_CHARS = 4000

STYLE = """
body{font-family:system-ui,sans-serif;margin:0;background:#f6f6f4;color:#222}
header{position:sticky;top:0;background:#fff;border-bottom:1px solid #ddd;padding:10px 16px;z-index:1}
header label{margin-right:10px;font-size:13px}
main{padding:12px 16px;max-width:1600px}
.card{background:#fff;border:1px solid #ddd;border-radius:6px;margin:10px 0;padding:10px 14px}
.card h3{margin:0 0 6px;font-size:15px;font-weight:600}
.badge{display:inline-block;padding:1px 7px;border-radius:9px;font-size:12px;margin-left:6px;color:#fff}
.correct{background:#2e7d32}.wrong{background:#c62828}.no_tool_call,.api_error{background:#546e7a}
.parse_error{background:#ef6c00}.ungraded{background:#9e9e9e}
.cols{display:grid;grid-template-columns:minmax(340px,1fr) minmax(500px,1.4fr);gap:14px}
.arms{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.arm{border:1px solid #e6e6e6;border-radius:5px;padding:8px;background:#fcfcfb}
.arm h4{margin:0 0 6px;font-size:14px}
pre{background:#fafafa;border:1px solid #eee;padding:8px;overflow:auto;font-size:12px;white-space:pre-wrap;margin:4px 0}
.kv{font-size:13px;margin:2px 0}.kv b{display:inline-block;min-width:96px}
details summary{cursor:pointer;font-size:13px;color:#555;margin:4px 0}
.meta{font-size:12px;color:#777}
.tool{border-left:3px solid #cfd8dc;padding-left:8px;margin:6px 0}
@media(max-width:1100px){.cols{grid-template-columns:1fr}.arms{grid-template-columns:1fr}}
"""

SCRIPT = """
function apply(){
  const outs=[...document.querySelectorAll('.f-out:checked')].map(e=>e.value);
  const steps=[...document.querySelectorAll('.f-step:checked')].map(e=>e.value);
  const q=document.getElementById('q').value.toLowerCase();
  let n=0;
  document.querySelectorAll('.card').forEach(c=>{
    const cardOuts=(c.dataset.outcomes||'').split(',').filter(Boolean);
    const stepOk=steps.length===0||steps.includes(c.dataset.step);
    const ok=stepOk&&(outs.length===0||cardOuts.some(o=>outs.includes(o)))&&(!q||c.dataset.search.includes(q));
    c.style.display=ok?'':'none'; if(ok)n++;
  });
  document.getElementById('count').textContent=n+' shown';
}
document.addEventListener('change',apply);document.addEventListener('input',apply);window.onload=apply;
"""


@dataclass
class RunData:
    label: str
    model: str
    calls_by: dict[str, AnswerCall]
    grades_by: dict[str, AnswerGrade]

    @property
    def correct(self) -> int:
        return sum(g.outcome.value == "correct" for g in self.grades_by.values())

    @property
    def total(self) -> int:
        return len(self.grades_by)


def _e(x: object) -> str:
    return html.escape(str(x))


def _fmt_answer(a) -> str:
    match a:
        case float():
            return f"{a:.6g}"
        case list() | tuple():
            return "(" + ", ".join(f"{v:.6g}" for v in a) + ")"
    return str(a)


def _load_run(run_dir: Path) -> RunData:
    calls = [AnswerCall.model_validate_json(line)
             for line in (run_dir / "calls.jsonl").read_text().splitlines() if line.strip()]
    grades = [AnswerGrade.model_validate_json(line)
              for line in (run_dir / "grades.jsonl").read_text().splitlines() if line.strip()]
    label = calls[0].harness if calls else run_dir.name
    model = calls[0].model if calls else "unknown"
    return RunData(label=label, model=model, calls_by={c.task_id: c for c in calls},
                   grades_by={g.task_id: g for g in grades})


def _prompt_parts(prompt: str) -> tuple[str, str]:
    """(task text without the program, answer instruction)."""
    instruction = prompt.split("Answer instruction:", 1)[1].strip() if "Answer instruction:" in prompt else ""
    match = re.search(r"CadQuery program:\s*```python\n.*?```\s*(.*?)\s*(?:\n\nAnswer instruction:|\Z)",
                      prompt, re.DOTALL)
    task = match.group(1).strip() if match else prompt.split("Answer instruction:", 1)[0].strip()
    return task, instruction


def _tool_calls(call: AnswerCall) -> str:
    blocks: list[str] = []
    for turn_index, turn in enumerate(call.turns):
        for i, tc in enumerate(turn.tool_calls):
            name = tc.get("function", {}).get("name", "?")
            try:
                args = json.loads(tc.get("function", {}).get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            result = turn.tool_results[i] if i < len(turn.tool_results) else ""
            if name == "run_code":
                code = args.get("code", "")
                blocks.append(
                    f"<div class='tool'><b>turn {turn_index + 1}: run_code</b>"
                    f"<pre>{_e(code)}</pre>"
                    f"<details><summary>Result</summary><pre>{_e(result[:MAX_TOOL_RESULT_CHARS])}</pre></details></div>")
            elif name == "submit_answer":
                blocks.append(f"<div class='tool'><b>turn {turn_index + 1}: submit_answer</b>"
                              f"<pre>{_e(args.get('answer', ''))}</pre></div>")
            else:
                blocks.append(f"<div class='tool'><b>turn {turn_index + 1}: {_e(name)}</b>"
                              f"<pre>{_e(json.dumps(args, sort_keys=True))}</pre></div>")
    if not blocks:
        return "<p class='meta'>No tool calls.</p>"
    return f"<details><summary>Tool calls ({len(blocks)})</summary>{''.join(blocks)}</details>"


def _arm(run: RunData, task: TaskDefinition, prompt_row: dict) -> str:
    call = run.calls_by.get(task.task_id)
    grade = run.grades_by.get(task.task_id)
    if call is None or grade is None:
        return f"<div class='arm'><h4>{_e(run.label)}</h4><p class='meta'>Not evaluated.</p></div>"
    outcome = grade.outcome.value
    answer = grade.model_answer if grade.model_answer is not None else call.submitted_answer
    reasoning = call.reasoning or ""
    truncated = len(reasoning) > MAX_REASONING_CHARS
    reasoning_text = reasoning[:MAX_REASONING_CHARS] + ("\n... [truncated]" if truncated else "")
    instruction = prompt_row.get(f"user_{run.label}", "")
    _, instruction_only = _prompt_parts(instruction)
    error = ""
    if call.error or grade.error_type:
        error = (f"<div class='kv'><b>Error</b>{_e(call.error or grade.error_type)} "
                 f"{_e((grade.message or '')[:400])}</div>")
    content = ""
    if call.content.strip():
        content = (f"<details><summary>Visible content</summary>"
                   f"<pre>{_e(call.content[:MAX_REASONING_CHARS])}</pre></details>")
    return f"""<div class="arm">
<h4>{_e(run.label)} <span class="badge {outcome}">{outcome}</span></h4>
<div class="kv"><b>Answer</b>{_e(_fmt_answer(answer) if answer is not None else '-')}</div>
{error}
<div class="meta">{call.prompt_tokens} in / {call.completion_tokens} out
 ({call.reasoning_tokens} reasoning) · {call.run_code_calls} run_code · {call.latency_s}s ·
 ${call.cost_usd:.5f} · finish={_e(call.finish_reason)}</div>
<details><summary>Answer instruction ({_e(run.label)})</summary><pre>{_e(instruction_only)}</pre></details>
<details><summary>Reasoning ({len(reasoning)} chars{', truncated' if truncated else ''})</summary>
<pre>{_e(reasoning_text)}</pre></details>
{content}
{_tool_calls(call)}
</div>"""


def _card(task: TaskDefinition, facts, prompt_row: dict, runs: list[RunData]) -> str:
    clues = sorted({c.clue_type.value for s in task.segments for c in s.clues})
    base_prompt = prompt_row.get("user_no_tools", "")
    task_text, _ = _prompt_parts(base_prompt)
    arms = "".join(_arm(run, task, prompt_row) for run in runs)
    outcomes = sorted({run.grades_by[task.task_id].outcome.value for run in runs if task.task_id in run.grades_by})
    search = " ".join([task.task_id, task.source_id, task.target_category.value,
                       task.answer_meaning.value, task.native_answer_format.value,
                       *clues, task_text, *[str(r.grades_by[task.task_id].model_answer)
                                            for r in runs if task.task_id in r.grades_by]]).lower()
    badges = "".join(f"<span class='badge {run.grades_by[task.task_id].outcome.value}'>{_e(run.label)}:"
                     f"{run.grades_by[task.task_id].outcome.value}</span>"
                     for run in runs if task.task_id in run.grades_by)
    program = facts[task.program_id].program_text if task.program_id in facts else ""
    return f"""<div class="card" data-step="{task.task_reasoning_step_count}" data-outcomes="{_e(','.join(outcomes))}" data-search="{_e(search)}">
<h3>{_e(task.task_id)} · step {task.task_reasoning_step_count}{badges}</h3>
<div class="meta">{_e(task.source_id)} · target {task.target_category.value} · answer {task.answer_meaning.value}
 ({task.native_answer_format.value}) · clues: {_e(', '.join(clues) or 'none')}</div>
<div class="cols"><div>
<pre>{_e(task_text)}</pre>
<details><summary>Program ({program.count(chr(10))} lines)</summary><pre>{_e(program)}</pre></details>
<div class="kv"><b>Gold answer</b>{_e(_fmt_answer(task.gold_answer))}</div>
</div><div class="arms">{arms}</div></div></div>"""


def build_review(root: Path, run_dirs: list[Path]) -> str:
    tasks = [TaskDefinition.model_validate_json(line)
             for line in (root / "tasks.jsonl").read_text().splitlines() if line.strip()]
    prompts = {row["task_id"]: row for row in
               (json.loads(line) for line in (root / "prompts.jsonl").read_text().splitlines() if line.strip())}
    facts = load_step9()[1]
    runs = [_load_run(path) for path in run_dirs]
    steps = sorted({t.task_reasoning_step_count for t in tasks})
    all_outcomes = sorted({g.outcome.value for run in runs for g in run.grades_by.values()})
    summary = " · ".join(f"{run.label}: {run.correct}/{run.total} ({100.0 * run.correct / run.total:.1f}%)"
                           for run in runs if run.total)
    model_label = runs[0].model if runs else "unknown"
    filters = "".join(f"<label><input type=checkbox class=f-step value={s} checked> step {s}</label>"
                      for s in steps)
    filters += " " + "".join(f"<label><input type=checkbox class=f-out value={o} checked> {o}</label>"
                             for o in all_outcomes)
    cards = "\n".join(_card(t, facts, prompts[t.task_id], runs)
                      for t in sorted(tasks, key=lambda x: x.task_id))
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>New dataset step-9 review</title>
<style>{STYLE}</style><script>{SCRIPT}</script></head><body>
<header><b>Step-9 review</b> · {_e(model_label)} · {_e(summary)}<br>{filters}
 <input id=q placeholder="search task, target, clue, answer..." size=55>
 <span id=count class=meta></span></header><main>{cards}</main></body></html>"""
