"""Execute the gold query of a task-construction oracle.

A gold query is a short Python fragment that runs after the oracle's program in
the same namespace. It prints exactly one line: the canonical answer value. The
fragment may use ``canon`` (4 significant figures, near-zero normalised to 0),
``json``, ``math``, and ``cq``. The program is expected to bind the final solid
to ``result``.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
import tempfile
from pathlib import Path

from task_oracle_schema import Environment, TaskOracle

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


def build_script(oracle: TaskOracle) -> str:
    return (
        f"{PRELUDE}\n"
        f"# program\n{oracle.program.text}\n"
        f"# gold query\n{oracle.gold_query.code}\n"
    )


def run_gold_query(oracle: TaskOracle, timeout: int = 120) -> str:
    """Run the oracle's gold query and return its single non-empty output line."""
    script = build_script(oracle)
    with tempfile.TemporaryDirectory(prefix="task-oracle-") as tmp:
        path = Path(tmp) / "oracle.py"
        path.write_text(script, encoding="utf-8")
        completed = subprocess.run(
            [sys.executable, str(path)],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    if completed.returncode != 0:
        stderr = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"gold query exited {completed.returncode}: {stderr}")
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if len(lines) != 1:
        raise RuntimeError(
            f"gold query printed {len(lines)} non-empty lines; expected exactly one"
        )
    return lines[0]


def gold_query_matches(oracle: TaskOracle, timeout: int = 120) -> bool:
    """True when the gold query prints the record's expected stdout."""
    return run_gold_query(oracle, timeout=timeout) == oracle.gold_query.expected_stdout


def current_environment() -> Environment:
    import OCP

    return Environment(
        cadquery_version=_cadquery_version(),
        ocp_version=OCP.__version__,
        python_version=platform.python_version(),
        oracle_tool_version=_tool_version(),
    )


def _cadquery_version() -> str:
    import cadquery

    return cadquery.__version__


def _tool_version() -> str:
    from task_oracle_schema import TOOL_VERSION

    return TOOL_VERSION


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
