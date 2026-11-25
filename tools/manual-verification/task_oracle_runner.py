"""Execute the gold queries of task-construction oracles.

A gold query is a short Python fragment that runs after the oracle's program in
the same namespace. It prints exactly one line: the canonical answer value. The
fragment may use ``canon`` (4 significant figures, near-zero normalised to 0),
``json``, ``math``, and ``cq``. The program is expected to bind the final solid
to ``result``.

Every script of a batch runs in one child process, so CadQuery and OCP are
imported once instead of once per record
(``docs/dataset/implementation/devtools/README.md#conventions``). The child
gives each script a fresh namespace and reports one JSON line per script; the
parent enforces the per-script deadline and restarts the child after a script
that hangs, so one bad record does not hide the rest.
"""

from __future__ import annotations

import hashlib
import io
import json
import platform
import queue
import subprocess
import sys
import threading
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import IO

from pydantic import BaseModel, ConfigDict, Field, model_validator
from task_oracle_schema import (
    SLUG,
    TOOL_VERSION,
    Environment,
    TaskOracle,
)

PRELUDE = """\
import json
import math

import cadquery as cq


def canon(value: float) -> str:
    \"\"\"Canonical decimal text: 4 significant figures, near-zero is 0.\"\"\"
    if abs(value) < 1e-9:
        return "0"
    return format(value, ".4g")
"""

BATCH_FLAG = "--batch"


class GoldQueryScript(BaseModel):
    """One script the batch executes: the prelude, a program, a query."""

    model_config = ConfigDict(extra="forbid")

    slug: str = Field(pattern=SLUG)
    script: str = Field(min_length=1)


class GoldQueryRun(BaseModel):
    """What one script did: the one line it printed, or why it did not."""

    model_config = ConfigDict(extra="forbid")

    slug: str = Field(pattern=SLUG)
    stdout: str | None = Field(default=None, min_length=1)
    error: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def _one_outcome(self) -> GoldQueryRun:
        if (self.stdout is None) == (self.error is None):
            raise ValueError("a run carries either stdout or an error")
        return self


def build_script(oracle: TaskOracle) -> GoldQueryScript:
    return GoldQueryScript(
        slug=oracle.slug,
        script=(
            f"{PRELUDE}\n"
            f"# program\n{oracle.program.text}\n"
            f"# gold query\n{oracle.gold_query.code}\n"
        ),
    )


def run_gold_queries(
    oracles: list[TaskOracle], timeout: int = 120
) -> list[GoldQueryRun]:
    """Run every oracle's gold query in one batch."""
    return run_scripts([build_script(oracle) for oracle in oracles], timeout=timeout)


def run_scripts(
    scripts: list[GoldQueryScript], timeout: int = 120
) -> list[GoldQueryRun]:
    """Run scripts in one child process, restarting it after a script that hangs."""

    runs: list[GoldQueryRun] = []
    pending = list(scripts)
    while pending:
        batch, blocked, error = _run_child(pending, timeout)
        runs.extend(batch)
        if blocked is None:
            break
        runs.append(GoldQueryRun(slug=blocked.slug, error=error))
        pending = pending[len(batch) + 1 :]
    return runs


def _run_child(
    scripts: list[GoldQueryScript], timeout: int
) -> tuple[list[GoldQueryRun], GoldQueryScript | None, str]:
    """Run one child over ``scripts``.

    Returns the runs it reported, the script it stopped on (if any), and why.
    """

    process = subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), BATCH_FLAG],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if process.stdin is None or process.stdout is None or process.stderr is None:
        raise RuntimeError("the batch child has no pipes")
    payload = json.dumps([script.model_dump() for script in scripts])
    process.stdin.write(payload)
    process.stdin.close()

    lines: queue.Queue[str | None] = queue.Queue()
    reader = threading.Thread(
        target=_read_lines, args=(process.stdout, lines), daemon=True
    )
    reader.start()

    runs: list[GoldQueryRun] = []
    while len(runs) < len(scripts):
        try:
            line = lines.get(timeout=timeout)
        except queue.Empty:
            process.kill()
            process.wait()
            return (
                runs,
                scripts[len(runs)],
                f"no result within {timeout}s; the batch was stopped",
            )
        if line is None:
            process.wait()
            detail = process.stderr.read().strip() or f"exit code {process.returncode}"
            return (
                runs,
                scripts[len(runs)],
                f"the batch exited before reporting this script: {detail}",
            )
        runs.append(_parse_run(line, scripts[len(runs)]))

    process.wait(timeout=timeout)
    return runs, None, ""


def _read_lines(stream: IO[str], sink: queue.Queue[str | None]) -> None:
    try:
        for line in stream:
            if line.strip():
                sink.put(line)
    finally:
        sink.put(None)


def _parse_run(line: str, script: GoldQueryScript) -> GoldQueryRun:
    try:
        run = GoldQueryRun.model_validate_json(line)
    except ValueError as error:
        raise RuntimeError(
            f"the batch reported a line that is not a run for {script.slug}: "
            f"{line.strip()!r}"
        ) from error
    if run.slug != script.slug:
        raise RuntimeError(
            f"the batch reported {run.slug!r} where {script.slug!r} was expected"
        )
    return run


def _batch_main() -> int:
    """The child entry point: import the kernel once, then run every script."""

    scripts = [GoldQueryScript.model_validate(item) for item in json.load(sys.stdin)]
    for script in scripts:
        sys.stdout.write(_run_one(script).model_dump_json() + "\n")
        sys.stdout.flush()
    return 0


def _run_one(script: GoldQueryScript) -> GoldQueryRun:
    out = io.StringIO()
    err = io.StringIO()
    try:
        with redirect_stdout(out), redirect_stderr(err):
            exec(  # noqa: S102 - checked-in, reviewed test data
                compile(script.script, f"<oracle:{script.slug}>", "exec"),
                {"__name__": "__oracle__"},
            )
    except (Exception, SystemExit) as error:  # noqa: BLE001 - every failure is a row
        parts = [str(error).strip()]
        stderr_lines = err.getvalue().strip().splitlines()
        if stderr_lines:
            parts.append(stderr_lines[-1])
        detail = " ".join(part for part in parts if part)
        return GoldQueryRun(
            slug=script.slug,
            error=f"{type(error).__name__}: {detail}"
            if detail
            else type(error).__name__,
        )
    lines = [line for line in out.getvalue().splitlines() if line.strip()]
    if len(lines) != 1:
        return GoldQueryRun(
            slug=script.slug,
            error=f"the gold query printed {len(lines)} non-empty lines; expected one",
        )
    return GoldQueryRun(slug=script.slug, stdout=lines[0])


def current_environment() -> Environment:
    """The versions that produced a record.

    The version strings live in the compiled extensions, so this imports
    CadQuery and OCP. It runs once per command, never once per record.
    """

    import OCP

    return Environment(
        cadquery_version=_cadquery_version(),
        ocp_version=OCP.__version__,
        python_version=platform.python_version(),
        oracle_tool_version=TOOL_VERSION,
    )


def _cadquery_version() -> str:
    import cadquery

    return cadquery.__version__


def query_sha256(oracle: TaskOracle) -> str:
    return hashlib.sha256(oracle.gold_query.code.encode("utf-8")).hexdigest()


def load_oracles(directory: Path) -> list[tuple[Path, TaskOracle]]:
    paths = sorted(directory.glob("*.json"))
    records: list[tuple[Path, TaskOracle]] = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        if not text.endswith("\n"):
            raise ValueError(f"{path.name}: record needs a trailing newline")
        records.append((path, TaskOracle.model_validate(json.loads(text))))
    return records


def record_text(oracle: TaskOracle) -> str:
    """The record as it is written to disk, with its trailing newline."""

    return oracle.model_dump_json(indent=2) + "\n"


def write_record(path: Path, oracle: TaskOracle) -> bool:
    """Write the record when its bytes change; return whether it did."""

    text = record_text(oracle)
    if path.read_text(encoding="utf-8") == text:
        return False
    path.write_text(text, encoding="utf-8")
    return True


if __name__ == "__main__":
    if sys.argv[1:] != [BATCH_FLAG]:
        raise SystemExit(f"usage: {Path(__file__).name} {BATCH_FLAG}")
    raise SystemExit(_batch_main())
