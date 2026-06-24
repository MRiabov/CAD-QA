"""Harbor task export and verifier wrappers for CAD-QA rows."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import shutil
from typing import Any

from cad_qa.dataset.public import PRIVATE_FIELDS, PUBLIC_FIELDS, private_rows as private_row_views, public_rows as public_row_views
from cad_qa.evaluation.grade import grade_public_private
from cad_qa.io import existing_record_artifact_path, read_records, write_json, write_jsonl


DEFAULT_VERIFIER_TIMEOUT_SEC = 120.0
DEFAULT_AGENT_TIMEOUT_SEC = 300.0
DEFAULT_HARBOR_AGENT = "terminus-2"
DEFAULT_HARBOR_MODEL = "openrouter/deepseek/deepseek-v4-flash"
DEFAULT_HARBOR_ENVIRONMENT = "docker"
HARBOR_ENVIRONMENTS = ("docker", "daytona")
DEFAULT_MAX_INPUT_TOKENS = 32_768
DEFAULT_MAX_OUTPUT_TOKENS = 16_384
DEFAULT_MAX_TURNS = 32


def materialize_harbor_tasks(
    public_rows: list[dict[str, Any]],
    private_rows: list[dict[str, Any]],
    out: Path,
    *,
    split: list[str] | None = None,
    difficulty: list[str] | None = None,
    relation_family: list[str] | None = None,
    measurement_scope: list[str] | None = None,
    max_rows: int | None = None,
    fresh: bool = False,
    model_name: str = DEFAULT_HARBOR_MODEL,
    environment: str = DEFAULT_HARBOR_ENVIRONMENT,
    n_concurrent_trials: int = 1,
    verifier_timeout_sec: float = DEFAULT_VERIFIER_TIMEOUT_SEC,
) -> dict[str, Any]:
    """Write Harbor task directories from CAD-QA public/private release rows."""

    _validate_harbor_environment(environment)
    if n_concurrent_trials < 1:
        raise ValueError("n_concurrent_trials must be at least 1")

    if fresh and out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)

    private_by_id = {row["row_id"]: _private_view(row) for row in private_rows}
    selected: list[tuple[dict[str, Any], dict[str, Any]]] = []
    skipped_missing_private = 0
    for public in public_rows:
        public_view = _public_view(public)
        private = private_by_id.get(public_view.get("row_id"))
        if private is None:
            skipped_missing_private += 1
            continue
        if not _matches_filters(
            public_view,
            split=split,
            difficulty=difficulty,
            relation_family=relation_family,
            measurement_scope=measurement_scope,
        ):
            continue
        selected.append((public_view, private))
        if max_rows is not None and len(selected) >= max(0, max_rows):
            break

    tasks: list[dict[str, Any]] = []
    for public, private in selected:
        task_dir = out / _safe_task_dir_name(str(public["row_id"]))
        if task_dir.exists():
            if fresh:
                shutil.rmtree(task_dir)
            else:
                raise FileExistsError(f"Harbor task already exists: {task_dir}")
        _write_task(task_dir, public, private, verifier_timeout_sec=verifier_timeout_sec)
        tasks.append(
            {
                "row_id": public["row_id"],
                "source_id": public.get("source_id"),
                "split": public.get("split"),
                "task_dir": str(task_dir),
                "task_name": f"cad-qa/{_safe_registry_name(str(public['row_id']))}",
            }
        )

    job_config_path = out / "cadqa_harbor_job.json"
    job_config = _job_config(
        out,
        model_name=model_name,
        environment=environment,
        n_concurrent_trials=n_concurrent_trials,
    )
    write_json(job_config_path, job_config)
    report = {
        "task_count": len(tasks),
        "input_public_rows": len(public_rows),
        "input_private_rows": len(private_rows),
        "skipped_missing_private": skipped_missing_private,
        "filters": {
            "split": split or [],
            "difficulty": difficulty or [],
            "relation_family": relation_family or [],
            "measurement_scope": measurement_scope or [],
            "max_rows": max_rows,
        },
        "out": str(out),
        "recommended_run": {
            "agent": DEFAULT_HARBOR_AGENT,
            "model": model_name,
            "environment": environment,
            "n_concurrent_trials": n_concurrent_trials,
            "max_input_tokens": DEFAULT_MAX_INPUT_TOKENS,
            "max_output_tokens": DEFAULT_MAX_OUTPUT_TOKENS,
            "max_turns": DEFAULT_MAX_TURNS,
            "job_config": str(job_config_path),
            "command": f"harbor run -c {job_config_path}",
        },
        "tasks": tasks,
    }
    write_json(out / "cadqa_harbor_manifest.json", report)
    write_jsonl(out / "tasks.jsonl", tasks)
    return report


def _job_config(
    dataset_path: Path,
    *,
    model_name: str = DEFAULT_HARBOR_MODEL,
    environment: str = DEFAULT_HARBOR_ENVIRONMENT,
    n_concurrent_trials: int = 1,
) -> dict[str, Any]:
    _validate_harbor_environment(environment)
    if n_concurrent_trials < 1:
        raise ValueError("n_concurrent_trials must be at least 1")
    llm_call_kwargs: dict[str, Any] = {
        "max_tokens": DEFAULT_MAX_OUTPUT_TOKENS,
    }
    provider_routing = _openrouter_native_provider_routing(model_name)
    if provider_routing is not None:
        llm_call_kwargs["extra_body"] = {"provider": provider_routing}
    return {
        "job_name": "cadqa-harbor-openrouter-deepseek-v4-flash",
        "n_attempts": 1,
        "n_concurrent_trials": n_concurrent_trials,
        "retry": {"max_retries": 0},
        "environment": {"type": environment, "delete": True},
        "agents": [
            {
                "name": DEFAULT_HARBOR_AGENT,
                "model_name": model_name,
                "kwargs": {
                    "max_turns": DEFAULT_MAX_TURNS,
                    "suppress_max_turns_warning": True,
                    "model_info": {
                        "max_input_tokens": DEFAULT_MAX_INPUT_TOKENS,
                        "max_output_tokens": DEFAULT_MAX_OUTPUT_TOKENS,
                    },
                    "llm_call_kwargs": llm_call_kwargs,
                },
            }
        ],
        "datasets": [
            {
                "path": str(dataset_path),
            }
        ],
    }


def _validate_harbor_environment(environment: str) -> None:
    if environment not in HARBOR_ENVIRONMENTS:
        allowed = ", ".join(HARBOR_ENVIRONMENTS)
        raise ValueError(f"unsupported Harbor environment {environment!r}; expected one of: {allowed}")


def _openrouter_native_provider_routing(model_name: str) -> dict[str, Any] | None:
    """Pin OpenRouter models to their native provider when cache locality matters."""

    parts = model_name.split("/", maxsplit=2)
    if len(parts) != 3 or parts[0] != "openrouter" or not parts[1]:
        return None
    provider = parts[1]
    return {
        "order": [provider],
        "only": [provider],
        "allow_fallbacks": False,
    }


def materialize_harbor_dataset(
    dataset_dir: Path,
    out: Path,
    *,
    split: list[str] | None = None,
    difficulty: list[str] | None = None,
    relation_family: list[str] | None = None,
    measurement_scope: list[str] | None = None,
    max_rows: int | None = None,
    fresh: bool = False,
    model_name: str = DEFAULT_HARBOR_MODEL,
    environment: str = DEFAULT_HARBOR_ENVIRONMENT,
    n_concurrent_trials: int = 1,
) -> dict[str, Any]:
    """Materialize Harbor tasks from a CAD-QA dataset directory."""

    public_path = existing_record_artifact_path(dataset_dir, "public")
    private_path = existing_record_artifact_path(dataset_dir, "private")
    if public_path.exists() and private_path.exists():
        public = read_records(public_path)
        private = read_records(private_path)
    else:
        rows_path = existing_record_artifact_path(dataset_dir, "rows")
        rows = read_records(rows_path)
        public = public_row_views(rows)
        private = private_row_views(rows)
    return materialize_harbor_tasks(
        public,
        private,
        out,
        split=split,
        difficulty=difficulty,
        relation_family=relation_family,
        measurement_scope=measurement_scope,
        max_rows=max_rows,
        fresh=fresh,
        model_name=model_name,
        environment=environment,
        n_concurrent_trials=n_concurrent_trials,
    )


def grade_harbor_task(
    task_dir: Path,
    *,
    app_dir: Path | None = None,
    logs_dir: Path | None = None,
) -> dict[str, Any]:
    """Run CAD-QA grading for one materialized Harbor task directory."""

    return grade_harbor_answer_files(
        public_path=task_dir / "workspace" / "row_public.json",
        private_path=task_dir / "expected" / "private.json",
        app_dir=app_dir or Path("/app"),
        logs_dir=logs_dir or Path("/logs/verifier"),
    )


def grade_harbor_answer_files(
    *,
    public_path: Path,
    private_path: Path,
    app_dir: Path,
    logs_dir: Path,
) -> dict[str, Any]:
    """Grade `/app/answer.json` or `/app/answer.txt` with CAD-QA's grader."""

    public = _read_json(public_path)
    private = _read_json(private_path)
    submission = _load_submission(app_dir)
    responses = []
    if submission["status"] == "ok":
        response: dict[str, Any] = {
            "row_id": public["row_id"],
            "answer": submission["answer"],
        }
        if submission.get("confidence") is not None:
            response["confidence"] = submission["confidence"]
        responses.append(response)
    grade = grade_public_private([public], [private], responses)
    graded = grade["graded"][0] if grade["graded"] else {}
    parse_invalid = bool(graded.get("error", "").startswith("parse_error:")) if graded.get("error") else False
    invalid_output = submission["status"] != "ok" or parse_invalid
    reward = 1 if graded.get("correct") is True and not invalid_output else 0
    artifact = {
        "reward": reward,
        "harbor": {
            "submission_status": submission["status"],
            "submission_error": submission.get("error"),
            "invalid_output": invalid_output,
            "invalid_output_reason": submission.get("error") or (graded.get("error") if parse_invalid else None),
        },
        "metrics": {key: value for key, value in grade.items() if key != "graded"},
        "graded": grade["graded"],
    }
    logs_dir.mkdir(parents=True, exist_ok=True)
    write_json(logs_dir / "cadqa_grade.json", artifact)
    write_jsonl(logs_dir / "graded_responses.jsonl", grade["graded"])
    (logs_dir / "reward.txt").write_text(f"{reward}\n", encoding="utf-8")
    return artifact


def export_harbor_atif(
    responses: list[dict[str, Any]],
    public_rows: list[dict[str, Any]],
    private_rows: list[dict[str, Any]],
    out: Path,
) -> dict[str, Any]:
    """Export graded response/trajectory records for Harbor ATIF workflows."""

    grade = grade_public_private(public_rows, private_rows, responses)
    response_by_id = {response.get("row_id"): response for response in responses}
    public_by_id = {row["row_id"]: row for row in public_rows}
    records: list[dict[str, Any]] = []
    for graded in grade["graded"]:
        row_id = graded["row_id"]
        response = response_by_id.get(row_id, {})
        public = public_by_id.get(row_id, {})
        records.append(
            {
                "row_id": row_id,
                "reward": 1 if graded["correct"] else 0,
                "correct": graded["correct"],
                "invalid_output": bool(graded.get("error", "").startswith("parse_error:")) if graded.get("error") else False,
                "error": graded.get("error"),
                "prompt": public.get("prompt"),
                "answer": response.get("answer", response.get("response")),
                "confidence": response.get("confidence"),
                "atif": response.get("atif") or response.get("trajectory"),
                "trajectory_path": response.get("trajectory_path"),
            }
        )
    out.mkdir(parents=True, exist_ok=True)
    write_jsonl(out / "atif_records.jsonl", records)
    report = {
        "response_count": len(responses),
        "record_count": len(records),
        "metrics": {key: value for key, value in grade.items() if key != "graded"},
    }
    write_json(out / "atif_report.json", report)
    return report


def run_harbor_verifier_cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="grade_cadqa.py")
    parser.add_argument("--public", type=Path)
    parser.add_argument("--private", type=Path)
    parser.add_argument("--app-dir", type=Path, default=Path("/app"))
    parser.add_argument("--logs-dir", type=Path, default=Path("/logs/verifier"))
    args = parser.parse_args(argv)
    public_path = args.public or _first_existing(
        [
            Path("/app/row_public.json"),
            Path("/tests/row_public.json"),
            Path("/workspace/row_public.json"),
            Path(__file__).resolve().parents[1] / "workspace" / "row_public.json",
            Path(__file__).resolve().parents[1] / "tests" / "row_public.json",
        ]
    )
    private_path = args.private or _first_existing(
        [
            Path("/expected/private.json"),
            Path("/tests/expected/private.json"),
            Path("/solution/expected/private.json"),
            Path(__file__).resolve().parents[1] / "expected" / "private.json",
            Path(__file__).resolve().parents[1] / "tests" / "expected" / "private.json",
        ]
    )
    if public_path is None or private_path is None:
        args.logs_dir.mkdir(parents=True, exist_ok=True)
        write_json(
            args.logs_dir / "cadqa_grade.json",
            {
                "reward": 0,
                "harbor": {
                    "submission_status": "verifier_error",
                    "submission_error": "missing public or private row fixture",
                    "invalid_output": True,
                },
            },
        )
        (args.logs_dir / "reward.txt").write_text("0\n", encoding="utf-8")
        return 2
    grade_harbor_answer_files(
        public_path=public_path,
        private_path=private_path,
        app_dir=args.app_dir,
        logs_dir=args.logs_dir,
    )
    return 0


def _write_task(
    task_dir: Path,
    public: dict[str, Any],
    private: dict[str, Any],
    *,
    verifier_timeout_sec: float,
) -> None:
    task_dir.mkdir(parents=True)
    (task_dir / "environment").mkdir()
    (task_dir / "workspace").mkdir()
    (task_dir / "tests").mkdir()
    (task_dir / "tests" / "expected").mkdir()
    (task_dir / "expected").mkdir()
    (task_dir / "solution").mkdir()
    (task_dir / "solution" / "expected").mkdir()

    (task_dir / "instruction.md").write_text(_instruction(public), encoding="utf-8")
    (task_dir / "task.toml").write_text(_task_toml(public, verifier_timeout_sec=verifier_timeout_sec), encoding="utf-8")
    (task_dir / "environment" / "Dockerfile").write_text(_dockerfile(), encoding="utf-8")
    (task_dir / "workspace" / "prompt.txt").write_text(str(public["prompt"]).rstrip() + "\n", encoding="utf-8")
    write_json(task_dir / "workspace" / "row_public.json", public)
    write_json(task_dir / "expected" / "private.json", private)
    write_json(task_dir / "tests" / "row_public.json", public)
    write_json(task_dir / "tests" / "expected" / "private.json", private)
    write_json(task_dir / "solution" / "expected" / "private.json", private)
    test_sh = task_dir / "tests" / "test.sh"
    test_sh.write_text(_test_sh(), encoding="utf-8")
    test_sh.chmod(0o755)
    solve_sh = task_dir / "solution" / "solve.sh"
    solve_sh.write_text(_solve_sh(), encoding="utf-8")
    solve_sh.chmod(0o755)
    (task_dir / "tests" / "grade_cadqa.py").write_text(_grade_script(), encoding="utf-8")
    _write_verifier_package(task_dir / "tests")


def _write_verifier_package(tests_dir: Path) -> None:
    package_dir = tests_dir / "cad_qa"
    evaluation_dir = package_dir / "evaluation"
    evaluation_dir.mkdir(parents=True, exist_ok=True)
    (package_dir / "__init__.py").write_text("", encoding="utf-8")
    (evaluation_dir / "__init__.py").write_text("", encoding="utf-8")
    source_dir = Path(__file__).resolve().parent
    for relative in [Path("evaluation") / "parse.py", Path("evaluation") / "grade.py"]:
        (package_dir / relative).write_text((source_dir / relative).read_text(encoding="utf-8"), encoding="utf-8")


def _instruction(public: dict[str, Any]) -> str:
    return (
        "# CAD-QA Closed-Book CAD Reasoning Task\n\n"
        f"{str(public['prompt']).rstrip()}\n\n"
        "You may use local computation while solving the task, including Python "
        "standard-library modules and installed third-party packages such as NumPy. "
        "Do not import or call CadQuery, `cq`, OCP, OpenCascade, or any other CAD "
        "kernel, and do not make network requests.\n\n"
        "Write your final answer to exactly one of these files:\n\n"
        '- `/app/answer.json` with JSON object `{"answer": "...", "confidence": optional_number}`\n'
        "- `/app/answer.txt` containing only the answer text\n\n"
        "Do not write both files. The verifier will parse the answer using the CAD-QA "
        f"`{public.get('answer_format', 'text')}` answer format and compare it with the private gold answer.\n"
    )


def _task_toml(public: dict[str, Any], *, verifier_timeout_sec: float) -> str:
    tags = ["cad-qa", "closed-book", "cad-reasoning", str(public.get("answer_format", "answer"))]
    lines = [
        'version = "1.0"',
        "",
        "[task]",
        f"name = {_toml_value('cad-qa/' + _safe_registry_name(str(public['row_id'])))}",
        f"description = {_toml_value('Closed-book CAD-QA reasoning task')}",
        "",
        "[metadata]",
        'author_name = "CAD-QA"',
        'author_email = "cad-qa@example.invalid"',
        f"difficulty = {_toml_value(public.get('difficulty_bucket', 'unknown'))}",
        'category = "cad-reasoning"',
        f"tags = {_toml_value(tags)}",
        f"row_id = {_toml_value(public.get('row_id'))}",
        f"source_id = {_toml_value(public.get('source_id'))}",
        f"split = {_toml_value(public.get('split', 'unsplit'))}",
        f"answer_format = {_toml_value(public.get('answer_format'))}",
        f"logical_hop_count = {_toml_value(public.get('logical_hop_count', 0))}",
        f"static_hop_count = {_toml_value(public.get('static_hop_count', 0))}",
        f"geometry_hop_count = {_toml_value(public.get('geometry_hop_count', 0))}",
        f"difficulty_bucket = {_toml_value(public.get('difficulty_bucket'))}",
        f"relation_families = {_toml_value(public.get('relation_families', []))}",
        f"measurement_scopes = {_toml_value(public.get('measurement_scopes', []))}",
        f"prompt_version = {_toml_value(public.get('prompt_version'))}",
        f"prompt_template_id = {_toml_value(public.get('prompt_template_id'))}",
        "",
        "[agent]",
        f"timeout_sec = {DEFAULT_AGENT_TIMEOUT_SEC:.1f}",
        "",
        "[verifier]",
        f"timeout_sec = {float(verifier_timeout_sec):.1f}",
        "",
        "[environment]",
        'workdir = "/app"',
        "build_timeout_sec = 600.0",
    ]
    return "\n".join(lines) + "\n"


def _dockerfile() -> str:
    return (
        "FROM python:3.11-slim\n\n"
        "WORKDIR /app\n"
        "RUN python -m pip install --no-cache-dir numpy pyarrow PyYAML\n"
        "ENV PYTHONPATH=/app:/tests:${PYTHONPATH}\n"
    )


def _test_sh() -> str:
    return (
        "#!/bin/bash\n"
        "set -u\n"
        "APP_DIR=\"${CADQA_APP_DIR:-/app}\"\n"
        "LOGS_DIR=\"${CADQA_LOGS_DIR:-/logs/verifier}\"\n"
        "mkdir -p \"$LOGS_DIR\"\n"
        "TASK_DIR=\"$(cd \"$(dirname \"$0\")/..\" && pwd)\"\n"
        "PUBLIC_PATH=\"${CADQA_PUBLIC:-}\"\n"
        "if [ -z \"$PUBLIC_PATH\" ]; then\n"
        "  for candidate in /tests/row_public.json \"$TASK_DIR/tests/row_public.json\" \"$TASK_DIR/workspace/row_public.json\" /workspace/row_public.json; do\n"
        "    if [ -f \"$candidate\" ]; then PUBLIC_PATH=\"$candidate\"; break; fi\n"
        "  done\n"
        "fi\n"
        "PRIVATE_PATH=\"${CADQA_PRIVATE:-}\"\n"
        "if [ -z \"$PRIVATE_PATH\" ]; then\n"
        "  for candidate in /tests/expected/private.json \"$TASK_DIR/tests/expected/private.json\" \"$TASK_DIR/expected/private.json\" /expected/private.json; do\n"
        "    if [ -f \"$candidate\" ]; then PRIVATE_PATH=\"$candidate\"; break; fi\n"
        "  done\n"
        "fi\n"
        "GRADE_SCRIPT=\"${CADQA_GRADE_SCRIPT:-/tests/grade_cadqa.py}\"\n"
        "if [ ! -f \"$GRADE_SCRIPT\" ]; then GRADE_SCRIPT=\"$TASK_DIR/tests/grade_cadqa.py\"; fi\n"
        "python3 \"$GRADE_SCRIPT\" --public \"$PUBLIC_PATH\" --private \"$PRIVATE_PATH\" --app-dir \"$APP_DIR\" --logs-dir \"$LOGS_DIR\"\n"
        "status=$?\n"
        "if [ ! -f \"$LOGS_DIR/reward.txt\" ]; then echo 0 > \"$LOGS_DIR/reward.txt\"; fi\n"
        "exit $status\n"
    )


def _solve_sh() -> str:
    return (
        "#!/bin/bash\n"
        "set -euo pipefail\n"
        "APP_DIR=\"${CADQA_APP_DIR:-/app}\"\n"
        "mkdir -p \"$APP_DIR\"\n"
        "TASK_DIR=\"$(cd \"$(dirname \"$0\")/..\" && pwd)\"\n"
        "PRIVATE_PATH=\"${CADQA_PRIVATE:-}\"\n"
        "if [ -z \"$PRIVATE_PATH\" ]; then\n"
        "  for candidate in /solution/expected/private.json \"$TASK_DIR/solution/expected/private.json\" \"$TASK_DIR/expected/private.json\" /expected/private.json /tests/expected/private.json; do\n"
        "    if [ -f \"$candidate\" ]; then PRIVATE_PATH=\"$candidate\"; break; fi\n"
        "  done\n"
        "fi\n"
        "if [ -z \"$PRIVATE_PATH\" ] || [ ! -f \"$PRIVATE_PATH\" ]; then\n"
        "  echo 'missing CAD-QA private answer key' >&2\n"
        "  exit 2\n"
        "fi\n"
        "python3 - \"$PRIVATE_PATH\" \"$APP_DIR\" <<'PY'\n"
        "import json\n"
        "import sys\n"
        "from pathlib import Path\n"
        "private = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))\n"
        "app_dir = Path(sys.argv[2])\n"
        "app_dir.mkdir(parents=True, exist_ok=True)\n"
        "(app_dir / 'answer.txt').unlink(missing_ok=True)\n"
        "(app_dir / 'answer.json').write_text(\n"
        "    json.dumps({'answer': private['gold_answer'], 'confidence': 1.0}, sort_keys=True) + '\\n',\n"
        "    encoding='utf-8',\n"
        ")\n"
        "PY\n"
    )


def _grade_script() -> str:
    return (
        "import argparse\n"
        "import json\n"
        "import math\n"
        "from pathlib import Path\n\n"
        "from cad_qa.evaluation.grade import grade_public_private\n\n\n"
        "def main() -> int:\n"
        "    parser = argparse.ArgumentParser()\n"
        "    parser.add_argument('--public', type=Path, required=True)\n"
        "    parser.add_argument('--private', type=Path, required=True)\n"
        "    parser.add_argument('--app-dir', type=Path, default=Path('/app'))\n"
        "    parser.add_argument('--logs-dir', type=Path, default=Path('/logs/verifier'))\n"
        "    args = parser.parse_args()\n"
        "    artifact = grade_answer_files(args.public, args.private, args.app_dir)\n"
        "    args.logs_dir.mkdir(parents=True, exist_ok=True)\n"
        "    write_json(args.logs_dir / 'cadqa_grade.json', artifact)\n"
        "    write_jsonl(args.logs_dir / 'graded_responses.jsonl', artifact['graded'])\n"
        "    (args.logs_dir / 'reward.txt').write_text(f\"{artifact['reward']}\\n\", encoding='utf-8')\n"
        "    return 0\n\n\n"
        "def grade_answer_files(public_path: Path, private_path: Path, app_dir: Path) -> dict:\n"
        "    public = json.loads(public_path.read_text(encoding='utf-8'))\n"
        "    private = json.loads(private_path.read_text(encoding='utf-8'))\n"
        "    submission = load_submission(app_dir)\n"
        "    responses = []\n"
        "    if submission['status'] == 'ok':\n"
        "        response = {'row_id': public['row_id'], 'answer': submission['answer']}\n"
        "        if submission.get('confidence') is not None:\n"
        "            response['confidence'] = submission['confidence']\n"
        "        responses.append(response)\n"
        "    grade = grade_public_private([public], [private], responses)\n"
        "    graded = grade['graded'][0] if grade['graded'] else {}\n"
        "    error = graded.get('error')\n"
        "    parse_invalid = bool(error.startswith('parse_error:')) if error else False\n"
        "    invalid_output = submission['status'] != 'ok' or parse_invalid\n"
        "    reward = 1 if graded.get('correct') is True and not invalid_output else 0\n"
        "    return {\n"
        "        'reward': reward,\n"
        "        'harbor': {\n"
        "            'submission_status': submission['status'],\n"
        "            'submission_error': submission.get('error'),\n"
        "            'invalid_output': invalid_output,\n"
        "            'invalid_output_reason': submission.get('error') or (error if parse_invalid else None),\n"
        "        },\n"
        "        'metrics': {key: value for key, value in grade.items() if key != 'graded'},\n"
        "        'graded': grade['graded'],\n"
        "    }\n\n\n"
        "def load_submission(app_dir: Path) -> dict:\n"
        "    answer_json = app_dir / 'answer.json'\n"
        "    answer_txt = app_dir / 'answer.txt'\n"
        "    if answer_json.exists() and answer_txt.exists():\n"
        "        return {'status': 'duplicate', 'error': 'duplicate_output_files'}\n"
        "    if not answer_json.exists() and not answer_txt.exists():\n"
        "        return {'status': 'missing', 'error': 'missing_answer_file'}\n"
        "    if answer_json.exists():\n"
        "        try:\n"
        "            payload = json.loads(answer_json.read_text(encoding='utf-8'))\n"
        "        except Exception as exc:\n"
        "            return {'status': 'invalid', 'error': f'invalid_answer_json:{type(exc).__name__}'}\n"
        "        if not isinstance(payload, dict) or 'answer' not in payload:\n"
        "            return {'status': 'invalid', 'error': 'answer_json_missing_answer'}\n"
        "        confidence = payload.get('confidence')\n"
        "        if confidence is not None:\n"
        "            try:\n"
        "                confidence = float(confidence)\n"
        "            except (TypeError, ValueError):\n"
        "                confidence = None\n"
        "            if confidence is not None and not math.isfinite(confidence):\n"
        "                confidence = None\n"
        "        answer = payload['answer']\n"
        "        if isinstance(answer, (dict, list)):\n"
        "            answer = json.dumps(answer, sort_keys=True)\n"
        "        else:\n"
        "            answer = str(answer)\n"
        "        return {'status': 'ok', 'answer': answer, 'confidence': confidence}\n"
        "    return {'status': 'ok', 'answer': answer_txt.read_text(encoding='utf-8')}\n\n\n"
        "def write_json(path: Path, data) -> None:\n"
        "    path.write_text(json.dumps(data, indent=2, sort_keys=True) + '\\n', encoding='utf-8')\n\n\n"
        "def write_jsonl(path: Path, rows) -> None:\n"
        "    with path.open('w', encoding='utf-8') as handle:\n"
        "        for row in rows:\n"
        "            handle.write(json.dumps(row, sort_keys=True) + '\\n')\n\n\n"
        "if __name__ == '__main__':\n"
        "    raise SystemExit(main())\n"
    )


def _load_submission(app_dir: Path) -> dict[str, Any]:
    answer_json = app_dir / "answer.json"
    answer_txt = app_dir / "answer.txt"
    has_json = answer_json.exists()
    has_txt = answer_txt.exists()
    if has_json and has_txt:
        return {"status": "duplicate", "error": "duplicate_output_files"}
    if not has_json and not has_txt:
        return {"status": "missing", "error": "missing_answer_file"}
    if has_json:
        try:
            payload = json.loads(answer_json.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            return {"status": "invalid", "error": f"invalid_answer_json:{type(exc).__name__}"}
        if not isinstance(payload, dict) or "answer" not in payload:
            return {"status": "invalid", "error": "answer_json_missing_answer"}
        confidence = payload.get("confidence")
        if confidence is not None:
            try:
                confidence = float(confidence)
            except (TypeError, ValueError):
                confidence = None
            if confidence is not None and not math.isfinite(confidence):
                confidence = None
        answer = payload["answer"]
        return {
            "status": "ok",
            "answer": json.dumps(answer, sort_keys=True) if isinstance(answer, (dict, list)) else str(answer),
            "confidence": confidence,
        }
    return {"status": "ok", "answer": answer_txt.read_text(encoding="utf-8")}


def _matches_filters(
    row: dict[str, Any],
    *,
    split: list[str] | None,
    difficulty: list[str] | None,
    relation_family: list[str] | None,
    measurement_scope: list[str] | None,
) -> bool:
    if split and row.get("split") not in set(split):
        return False
    if difficulty and row.get("difficulty_bucket") not in set(difficulty):
        return False
    if relation_family and not (set(row.get("relation_families") or []) & set(relation_family)):
        return False
    if measurement_scope and not (set(row.get("measurement_scopes") or []) & set(measurement_scope)):
        return False
    return True


def _public_view(row: dict[str, Any]) -> dict[str, Any]:
    public = {field: row[field] for field in sorted(PUBLIC_FIELDS) if field in row}
    leaked = (PRIVATE_FIELDS - {"row_id", "source_id", "answer_format", "split"}) & set(public)
    if leaked:
        raise ValueError(f"public row contains private fields: {sorted(leaked)}")
    return public


def _private_view(row: dict[str, Any]) -> dict[str, Any]:
    return {field: row[field] for field in sorted(PRIVATE_FIELDS) if field in row}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _first_existing(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def _safe_task_dir_name(value: str) -> str:
    safe = _safe_registry_name(value)
    return safe[:120] or "task"


def _safe_registry_name(value: str) -> str:
    safe = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return safe or "task"


def _toml_value(value: Any) -> str:
    if value is None:
        return '""'
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, list):
        return "[" + ", ".join(_toml_value(item) for item in value) + "]"
    return json.dumps(str(value))
