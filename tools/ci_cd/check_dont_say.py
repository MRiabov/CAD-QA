"""Don't-say checker for CAD-QA docs, code, and JSON contracts.

Run it as ``tools/ci_cd/dont-say`` (or ``uv run python tools/ci_cd/check_dont_say.py``); it
is a whole-repository scan, so it is a script rather than a pytest test.

Reads the ``## Don't say`` table from ``docs/glossary.md`` and fails when a
banned term appears in a scanned file (``.md``, ``.tex``, ``.py``, ``.go``,
``.json``).

What is checked, per language:

- Markdown and LaTeX: prose, with code spans, fenced blocks, verbatim blocks,
  and comments skipped.
- Python: comments and docstrings as prose; every name the module declares
  (class, function, method, parameter, variable, field, type alias) as a name.
- Go: comments as prose; every name the file declares (type, function, method,
  receiver, parameter, result, struct field, interface method, variable,
  constant, type parameter) as a name. ``tools/dont-say-go`` reads the syntax
  with ``go/parser``; the checker never guesses.
- JSON: ``description`` and ``title`` as prose; ``properties``, ``$defs``,
  ``definitions``, ``patternProperties``, ``dependentSchemas``, ``enum``, and
  ``const`` values as names. Schema vocabulary is not a CAD-QA name.
- Every scanned file: its stem and its folder names as names.

A name matches when the rule's words appear as consecutive name segments, so
``query_program``, ``QueryProgram``, and ``query-program`` all match ``query
program``. A bare term is allowed when a preceding segment qualifies it
(``clue_type``), and a leading verb does not qualify it (``get_type`` is still
a hit). ``--ratchet`` and ``--names-ratchet`` enforce that neither count rises.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.ci_cd.dont_say_rules import Hit, parse_rules
from tools.ci_cd.dont_say_scan import SCAN_ROOTS, collect_hits

logger = logging.getLogger("cadqa.check_dont_say")


def format_hit(hit: Hit) -> str:
    where = f' in {hit.form} "{hit.name}"' if hit.form else ""
    if hit.rule.bare:
        return (
            f'{hit.path}:{hit.line}: don\'t say bare "{hit.rule.phrase}"{where} '
            f"(qualify it; for example: {hit.rule.say})"
        )
    return (
        f'{hit.path}:{hit.line}: don\'t say "{hit.rule.phrase}"{where} '
        f"(say {hit.rule.say})"
    )


def load_baseline(path: Path) -> int | None:
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8").strip()
    return int(text) if text else None


def enforce_ratchet(
    baseline_path: Path, hits: list[Hit], *, update: bool, label: str
) -> int:
    """Fail unless the hit count equals the baseline; a fall must be re-pinned."""

    baseline = load_baseline(baseline_path)
    if update or baseline is None:
        baseline_path.write_text(f"{len(hits)}\n", encoding="utf-8")
        logger.info("check_dont_say: %s baseline %s -> %d", label, baseline, len(hits))
        return 0
    if len(hits) > baseline:
        logger.error(
            "check_dont_say: %d %s hit(s) > baseline %d", len(hits), label, baseline
        )
        return 1
    if len(hits) < baseline:
        logger.error(
            "check_dont_say: %d %s hit(s) < baseline %d; run --update-baseline",
            len(hits),
            label,
            baseline,
        )
        return 1
    logger.info("check_dont_say: %d %s hit(s), at baseline", len(hits), label)
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        description="Fail on Don't-say terms in CAD-QA docs, code, and contracts."
    )
    parser.add_argument("--glossary", type=Path, default=REPO / "docs/glossary.md")
    parser.add_argument(
        "--roots", nargs="+", default=[str(REPO / root) for root in SCAN_ROOTS]
    )
    parser.add_argument(
        "--ratchet",
        type=Path,
        help="baseline for prose hits (Markdown, LaTeX, comments, docstrings, JSON prose)",
    )
    parser.add_argument(
        "--names-ratchet",
        type=Path,
        help="baseline for declared names: classes, functions, fields, files, folders, JSON names",
    )
    parser.add_argument("--update-baseline", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    try:
        rules = parse_rules(args.glossary.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        logger.error("check_dont_say: %s", exc)
        return 2

    try:
        hits = collect_hits(args.roots, rules)
    except (OSError, ValueError, RuntimeError) as exc:
        logger.error("check_dont_say: %s", exc)
        return 2

    if not args.quiet:
        for hit in hits:
            logger.warning(format_hit(hit))

    prose = [hit for hit in hits if not hit.form]
    names = [hit for hit in hits if hit.form]

    if args.ratchet is None and args.names_ratchet is None:
        if hits:
            logger.error(
                "%d Don't-say hit(s): %d prose, %d names",
                len(hits),
                len(prose),
                len(names),
            )
            return 1
        if not args.quiet:
            logger.info("check_dont_say: clean (%d rules)", len(rules))
        return 0

    status = 0
    if args.ratchet is not None:
        status |= enforce_ratchet(
            args.ratchet, prose, update=args.update_baseline, label="prose"
        )
    if args.names_ratchet is not None:
        status |= enforce_ratchet(
            args.names_ratchet, names, update=args.update_baseline, label="name"
        )
    return status


if __name__ == "__main__":
    raise SystemExit(main())
