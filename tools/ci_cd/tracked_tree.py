"""Read the tracked file list from git.

The checks that scan the whole tree use this; an untracked working file is not
admitted yet, so it cannot make a whole-tree check red before it is staged.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def tracked_paths(root: Path) -> list[str]:
    """Return the repository-relative paths of every tracked file."""

    result = subprocess.run(
        ["git", "-C", str(root), "ls-files"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line]
