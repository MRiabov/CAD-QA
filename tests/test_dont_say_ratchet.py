from __future__ import annotations

from pathlib import Path

from tools.check_dont_say import main

BASELINE = Path(__file__).resolve().parents[1] / "tools" / "dont_say_baseline.txt"


def test_dont_say_ratchet_holds() -> None:
    assert BASELINE.exists(), "run tools/check_dont_say.py --update-baseline"
    assert main(["--ratchet", str(BASELINE), "--quiet"]) == 0
