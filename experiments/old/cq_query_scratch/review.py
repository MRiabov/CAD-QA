"""Static HTML review page: one card per task with prompt, gold, model output, and grade."""

from __future__ import annotations

import html

from experiments.old.cq_query_scratch.models import GradeResult, ModelCall, Outcome, ProgramFacts, TaskDefinition

STYLE = """
body{font-family:system-ui,sans-serif;margin:0;background:#f6f6f4;color:#222}
header{position:sticky;top:0;background:#fff;border-bottom:1px solid #ddd;padding:10px 16px;z-index:1}
header label{margin-right:14px;font-size:14px}
main{padding:12px 16px;max-width:1300px}
.card{background:#fff;border:1px solid #ddd;border-radius:6px;margin:10px 0;padding:10px 14px}
.card h3{margin:0 0 6px;font-size:15px;font-weight:600}
.badge{display:inline-block;padding:1px 7px;border-radius:9px;font-size:12px;margin-left:6px;color:#fff}
.correct{background:#2e7d32}.wrong{background:#c62828}.exec_error,.timeout{background:#ef6c00}
.literal_answer{background:#6a1b9a}.no_tool_call,.api_error{background:#546e7a}.ungraded{background:#9e9e9e}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:12px}
pre{background:#fafafa;border:1px solid #eee;padding:8px;overflow:auto;font-size:12px;white-space:pre-wrap;margin:4px 0}
.kv{font-size:13px;margin:2px 0}.kv b{display:inline-block;min-width:110px}
details summary{cursor:pointer;font-size:13px;color:#555;margin:4px 0}
.meta{font-size:12px;color:#777}
"""

SCRIPT = """
function apply(){
  const steps=[...document.querySelectorAll('.f-step:checked')].map(e=>e.value);
  const outs=[...document.querySelectorAll('.f-out:checked')].map(e=>e.value);
  const q=document.getElementById('q').value.toLowerCase();
  let n=0;
  document.querySelectorAll('.card').forEach(c=>{
    const ok=steps.includes(c.dataset.step)&&outs.includes(c.dataset.outcome)&&
      (!q||c.dataset.search.includes(q));
    c.style.display=ok?'':'none'; if(ok)n++;
  });
  document.getElementById('count').textContent=n+' shown';
}
document.addEventListener('change',apply);document.addEventListener('input',apply);window.onload=apply;
"""


def _e(x: object) -> str:
    return html.escape(str(x))


def _fmt_answer(a) -> str:
    match a:
        case float():
            return f"{a:.6g}"
        case list() | tuple():
            return "(" + ", ".join(f"{v:.6g}" for v in a) + ")"
    return str(a)


def _card(t: TaskDefinition, pf: ProgramFacts, call: ModelCall | None, grade: GradeResult | None) -> str:
    outcome = grade.outcome.value if grade else "ungraded"
    task_text = t.prompt.split("Task:", 1)[1].strip() if "Task:" in t.prompt else t.prompt
    clue_types = sorted({c.clue_type.value for s in t.segments for c in s.clues})
    search = " ".join([t.task_id, t.source_id, outcome, t.answer_meaning.value, *clue_types, task_text]).lower()
    model_block = "<p class='meta'>Not evaluated yet.</p>"
    if call is not None:
        model_block = (
            f"<div class='kv'><b>Model answer</b>{_e(_fmt_answer(grade.model_answer) if grade else '-')}</div>"
            + (f"<div class='kv'><b>Error</b>{_e(grade.error_type)}: {_e((grade.message or '')[:400])}</div>"
               if grade and grade.error_type else "")
            + f"<div class='meta'>{call.completion_tokens} completion tokens ({call.reasoning_tokens} reasoning), "
              f"{call.latency_s}s, ${call.cost_usd:.5f}, finish={_e(call.finish_reason)}</div>"
            + f"<details open><summary>Model query</summary><pre>{_e(call.submitted_code or call.content or '')}</pre>"
              f"</details>"
            + f"<details><summary>Model reasoning ({len(call.reasoning)} chars)</summary>"
              f"<pre>{_e(call.reasoning)}</pre></details>")
    return f"""<div class="card" data-step="{t.task_reasoning_step_count}" data-outcome="{outcome}"
 data-search="{_e(search)}">
<h3>{_e(t.task_id)} · step {t.task_reasoning_step_count}<span class="badge {outcome}">{outcome}</span></h3>
<div class="meta">{_e(t.source_id)} · target {t.target_category.value} · answer {t.answer_meaning.value}
 ({t.native_answer_format.value}) · clues: {_e(', '.join(clue_types) or 'none')}</div>
<div class="cols"><div>
<pre>{_e(task_text)}</pre>
<details><summary>Program ({pf.program_text.count(chr(10))} lines)</summary><pre>{_e(pf.program_text)}</pre></details>
</div><div>
<div class="kv"><b>Gold answer</b>{_e(_fmt_answer(t.gold_answer))}</div>
{model_block}
<details><summary>Gold query</summary><pre>{_e(t.gold_query.split("return s if isinstance", 1)[-1].split(chr(10), 1)[-1].strip())}</pre></details>
</div></div></div>"""


def build_review(tasks: list[TaskDefinition], facts: dict[str, ProgramFacts], calls: list[ModelCall],
                 grades: list[GradeResult]) -> str:
    call_by = {c.task_id: c for c in calls}
    grade_by = {g.task_id: g for g in grades}
    steps = sorted({t.task_reasoning_step_count for t in tasks})
    outcomes = [o.value for o in Outcome] + ["ungraded"]
    summary = {s: (sum(1 for t in tasks if t.task_reasoning_step_count == s and (g := grade_by.get(t.task_id))
                       and g.outcome == Outcome.CORRECT),
                   sum(1 for t in tasks if t.task_reasoning_step_count == s and t.task_id in grade_by))
               for s in steps}
    filters = "".join(f"<label><input type=checkbox class=f-step value={s} checked> step {s} "
                      f"({summary[s][0]}/{summary[s][1]})</label>" for s in steps)
    filters += "<br>" + "".join(f"<label><input type=checkbox class=f-out value={o} checked> {o}</label>"
                                for o in outcomes)
    cards = "\n".join(_card(t, facts[t.program_id], call_by.get(t.task_id), grade_by.get(t.task_id))
                      for t in sorted(tasks, key=lambda t: (t.task_reasoning_step_count, t.task_id)))
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>CadQuery-query review</title>
<style>{STYLE}</style><script>{SCRIPT}</script></head><body>
<header>{filters}<br><input id=q placeholder="search text, task id, clue type..." size=50>
 <span id=count class=meta></span></header><main>{cards}</main>
</body></html>"""
