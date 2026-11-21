"""E2E test for the CadQuery-query scratch experiment: real CadQuery, only the LLM mocked."""

from __future__ import annotations

import hashlib
import json

import pytest

from experiments.old.cq_query_scratch import run_eval
from experiments.old.cq_query_scratch.definitions import (
    FactIndex,
    GenerationFailure,
    SegmentPlan,
    _Search,
    build_task,
)
from experiments.old.cq_query_scratch.generate import (
    StepCountStats,
    construct,
    select_and_verify,
)
from experiments.old.cq_query_scratch.grading import answers_match, assigns_literal_answer
from experiments.old.cq_query_scratch.kernel import (
    canonical_json,
    extract_program,
    run_queries,
)
from experiments.old.cq_query_scratch.models import (
    ModelCall,
    Outcome,
    ProgramFacts,
    TaskDefinition,
)
from experiments.old.cq_query_scratch.pool import check_accepted_subset, normalize
from experiments.old.cq_query_scratch.render import render_prompt, render_task_text
from experiments.old.cq_query_scratch.report import build_report

PROGRAM = """import cadquery as cq
wp1 = cq.Workplane("XY")
wp2 = wp1.box(40, 30, 20)
wp3 = wp2.faces(">Z")
wp4 = wp3.workplane()
wp5 = wp4.hole(6)
wp6 = cq.Workplane("YZ")
wp7 = wp6.rect(10, 8)
wp8 = wp7.extrude(30)
wp9 = wp5.cut(wp8)
result = wp9
"""


@pytest.fixture(scope="module")
def facts() -> ProgramFacts:
    text = normalize(PROGRAM)
    subset = check_accepted_subset(text)
    sha = hashlib.sha256(text.encode()).hexdigest()
    return extract_program(source_id="src_fixture", collection="CADEvolve-C-core", family_id="cadevolve:fixture",
                           program_id=f"cadqaprog:{sha}", program_sha256=sha, program_text=text,
                           assignments=subset.assignments, final_var=subset.final_var)


def test_pool_checks_and_entity_ids(facts: ProgramFacts) -> None:
    assert normalize(facts.program_text) == facts.program_text
    assert facts.final_var == "wp9"
    with pytest.raises(Exception):
        check_accepted_subset("import cadquery as cq\nfor i in range(2):\n    pass\nresult = 1\n")
    face = facts.faces[0]
    fields = {"centroid": list(face.center), "area": face.area, "normal": list(face.normal),
              "bbox": {"min": list(face.bbox_min), "max": list(face.bbox_max)}}
    fp_sha = hashlib.sha256(("cadqa.fingerprint.v1\0" + canonical_json(
        {"category": "face", "fields": fields})).encode()).hexdigest()
    expected = "ent:" + hashlib.sha256(f"cadqa.entity.v1\0{facts.final_state_id}\0face\0{fp_sha}".encode()).hexdigest()
    assert face.entity_id in {f.entity_id for f in facts.faces} and expected == face.entity_id
    assert canonical_json(0.1 + 0.2) == "0.3" and canonical_json(-0.0) == "0"
    created = FactIndex(facts).created
    assert created["wp9"], "the cut must create faces"


def test_construction_narrowing_necessity_and_gold(facts: ProgramFacts) -> None:
    idx = FactIndex(facts)
    for step in (1, 3, 5):
        tasks = [t for slot in range(4) if isinstance(t := build_task(facts, idx, step, slot), TaskDefinition)]
        assert tasks, f"no task at step count {step}"
        for t in tasks:
            assert t.task_reasoning_step_count == step == t.clue_step_count + 1
            assert all(c.result.after_count < c.result.before_count for s in t.segments for c in s.clues)
    task = next(t for slot in range(6) if isinstance(t := build_task(facts, idx, 3, slot), TaskDefinition))
    seg = task.segments[0]
    search = _Search(idx, ("test",))
    checks = [c.check for c in seg.clues]
    result = [e for e in idx.by_category[seg.category] if e.entity_id in seg.bound_entity_ids]
    plan = SegmentPlan(category=seg.category, length=len(checks) + 1)
    assert not search._necessary(plan, None, [*checks, checks[-1]], result), "a repeated clue is not necessary"
    stats = StepCountStats(step_count=3)
    accepted = select_and_verify(construct([facts], 3, stats), {facts.program_id: facts}, 3, stats, [])
    assert accepted and all(t.validity.gold_query_reproduces_answer for t in accepted)
    out = run_queries(facts.program_text, ["answer = 42.0", accepted[0].gold_query])
    assert assigns_literal_answer("answer = 42.0") and not assigns_literal_answer(accepted[0].gold_query)
    assert not assigns_literal_answer("answer = 0\nfor f in result.val().Faces():\n    answer += 1\n")
    assert not assigns_literal_answer("answer = 0\nanswer = len(result.val().Faces())\n")
    assert answers_match(out[1].answer, accepted[0].gold_answer, accepted[0].native_answer_format, 1e-3, 1e-6)


def test_generation_is_byte_identical(facts: ProgramFacts) -> None:
    def gen() -> str:
        idx = FactIndex(facts)
        rows = []
        for step in (1, 3, 5, 7):
            for slot in range(3):
                t = build_task(facts, idx, step, slot)
                if isinstance(t, TaskDefinition):
                    t.prompt = render_task_text(t, facts)
                    rows.append(t.model_dump_json())
                else:
                    assert isinstance(t, GenerationFailure)
        return "\n".join(rows)

    assert gen() == gen()


def test_eval_pipeline_with_mocked_llm(facts: ProgramFacts, tmp_path, monkeypatch) -> None:
    stats = StepCountStats(step_count=3)
    tasks = select_and_verify(construct([facts], 3, stats), {facts.program_id: facts}, 2, stats, [])
    for t in tasks:
        t.prompt = render_task_text(t, facts)
        assert "Task:" in render_prompt(t).user
        if isinstance(t.gold_answer, float):  # small integers legitimately appear in clue numbering
            assert f"{t.gold_answer:.4f}".rstrip("0") not in t.prompt.split("Task:")[1]
    literal = tasks[1].task_id if len(tasks) > 1 else None

    def fake_call(task: TaskDefinition, api_key: str) -> ModelCall:
        code = "answer = 1.0" if task.task_id == literal else task.gold_query
        tc = [{"function": {"name": "submit_query", "arguments": json.dumps({"code": code})}}]
        return ModelCall(task_id=task.task_id, model="mock", system_prompt_sha256="0" * 64,
                         user_prompt_sha256="0" * 64, reasoning="r", tool_calls=tc,
                         submitted_code=run_eval._submitted_code(tc))

    monkeypatch.setattr(run_eval, "call_model", fake_call)
    grades = run_eval.run(tasks, {facts.program_id: facts}, tmp_path, "unused", max_cost_usd=1.0)
    outcomes = {g.task_id: g.outcome for g in grades}
    assert outcomes[tasks[0].task_id] == Outcome.CORRECT
    if literal:
        assert outcomes[literal] == Outcome.LITERAL_ANSWER
    assert len((tmp_path / "calls.jsonl").read_text().splitlines()) == len(tasks)
    assert run_eval.run(tasks, {facts.program_id: facts}, tmp_path, "unused", 1.0) == []  # resume skips all
    text = build_report([stats], tasks, grades, [])
    assert f"| 3 | {stats.attempts} | {stats.constructed} |" in text


def test_agentic_loop_and_escape_guard(facts: ProgramFacts, monkeypatch) -> None:
    from experiments.old.cq_query_scratch.grading import escape_attempt
    from experiments.old.cq_query_scratch.models import Harness

    assert escape_attempt("import os\nanswer = 1") == "import os"
    assert escape_attempt("answer = open('/etc/passwd').read()") == "call open()"
    assert escape_attempt("import math\nanswer = math.pi * result.val().Volume()") is None
    stats = StepCountStats(step_count=3)
    task = select_and_verify(construct([facts], 3, stats), {facts.program_id: facts}, 1, stats, [])[0]
    task.prompt = render_task_text(task, facts)

    def tc(name: str, code: str, i: int) -> dict:
        return {"id": f"t{i}", "type": "function", "function": {"name": name, "arguments": json.dumps({"code": code})}}

    script = [[tc("run_query", "import os\nanswer = 1", 0)], [tc("run_query", task.gold_query, 1)],
              [tc("submit_query", task.gold_query, 2)]]
    seen: list[list[dict]] = []

    def fake_chat(api_key, messages, tools=None):
        seen.append(list(messages))
        return run_eval.ChatResponse(tool_calls=script[len(seen) - 1], completion_tokens=10, reasoning_tokens=5,
                                     cost_usd=0.001, vendor="deepseek")

    monkeypatch.setattr(run_eval, "chat", fake_chat)
    call = run_eval.call_model_agentic(task, "unused", facts)
    assert call.harness == Harness.AGENTIC and len(call.turns) == 3 and call.run_query_calls == 2
    assert call.blocked_run_queries == 1 and call.turns[0].tool_results[0].startswith("refused")
    assert call.turns[1].tool_results[0].startswith("answer = ")
    assert call.completion_tokens == 30 and seen[-1][-1]["role"] == "tool"
    assert run_eval.grade(task, facts, call).outcome == Outcome.CORRECT
