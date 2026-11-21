"""Check that the streamlined and test doc trees mirror the dataset pipeline stage docs.

Run it as ``tools/ci_cd/check-doc-mirror`` (or
``uv run python tools/ci_cd/check_doc_mirror.py``). The rule lives in
``docs/dataset/implementation/pipeline/streamlined/README.md`` and
``docs/dataset/implementation/pipeline/testing/README.md``: every
pipeline stage/sub-step contract doc has the same relative path under
``streamlined/`` and ``testing/``.

The check is structural, not semantic. It does not compare the text of a doc
with its counterpart; it checks that the counterpart exists and that the two
trees hold no unexpected pipeline stage doc.

Exempt from the mirror:

- ``decisions.md`` — rationale, not a pipeline stage contract;
- ``algorithm/`` — mechanism docs, not a pipeline stage contract;
- ``extraction/`` — field mechanics, summarized by ``streamlined/models/``.

Additions allowed on each side:

- ``streamlined/models/`` — the typed model declarations;
- ``testing/00-*.md`` — the cross-cutting test contracts;
- ``testing/fixtures/``, ``testing/golden/``, ``testing/oracles/`` — test data;
- each tree's ``README.md``.
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from collections.abc import Iterable
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger("cadqa.check_doc_mirror")

REPO = Path(__file__).resolve().parents[2]
PIPELINE = Path("docs/dataset/implementation/pipeline")
STREAMLINED = PIPELINE / "streamlined"
TESTING = PIPELINE / "testing"

# A pipeline stage/sub-step contract doc. The patterns are relative to the dataset pipeline root.
DOC_PATTERNS = (
    re.compile(r"(?:^|.*/)0[45]-[a-z0-9-]+\.md$"),  # 04, 05 pipeline stage docs
    re.compile(r"(?:^|.*/)\d\d[a-z]-[a-z0-9-]+\.md$"),  # 01a, 02b, 03c
    re.compile(r"(?:^|.*/)\d\d[a-z]-[a-z0-9-]+/README\.md$"),  # 03a, 03b
    re.compile(r"(?:^|.*/)\d\d[a-z]-[a-z0-9-]+/[a-z][a-z0-9-]*\.md$"),  # lettered
    re.compile(r"(?:^|.*/)0[45]-[a-z0-9-]+/[a-z][a-z0-9-]*\.md$"),  # 05 sub-doc
    re.compile(r"^00-end-to-end\.md$"),
)
DIR_PATTERN = re.compile(r"(?:^|.*/)\d\d[a-z]-[a-z0-9-]+$")
EXEMPT_PARTS = frozenset({"decisions.md", "algorithm", "extraction"})
MIRROR_PARTS = frozenset({"streamlined", "testing"})
EXTRA_TEST_DIRS = frozenset({"fixtures", "golden", "oracles"})


class Side(StrEnum):
    STREAMLINED = "streamlined"
    TESTING = "testing"


class FindingType(StrEnum):
    MISSING_DOC = "missing_doc"
    MISSING_DIR = "missing_dir"
    UNEXPECTED_DOC = "unexpected_doc"


class Finding(BaseModel):
    """One structural difference between the dataset pipeline tree and a mirror."""

    model_config = ConfigDict(frozen=True)

    finding_type: FindingType
    side: Side
    relative_path: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class Report(BaseModel):
    """The check result. An empty finding list is a pass."""

    findings: list[Finding] = Field(default_factory=list)
    docs_checked: int = Field(ge=0)
    dirs_checked: int = Field(ge=0)

    @property
    def ok(self) -> bool:
        return not self.findings


Finding.model_rebuild()
Report.model_rebuild()


def _is_exempt(relative: Path) -> bool:
    if relative.parts and relative.parts[0] in MIRROR_PARTS:
        return True
    return any(part in EXEMPT_PARTS for part in relative.parts)


def expected_docs(pipeline: Path) -> set[Path]:
    """The contract docs for each pipeline stage, present under both mirrors."""

    docs: set[Path] = set()
    for path in pipeline.rglob("*.md"):
        relative = path.relative_to(pipeline)
        if _is_exempt(relative):
            continue
        if any(pattern.search(relative.as_posix()) for pattern in DOC_PATTERNS):
            docs.add(relative)
    return docs


def expected_dirs(pipeline: Path) -> set[Path]:
    """The folders for each pipeline stage, present under both mirrors."""

    dirs: set[Path] = set()
    for path in pipeline.rglob("*"):
        if not path.is_dir():
            continue
        relative = path.relative_to(pipeline)
        if _is_exempt(relative):
            continue
        if DIR_PATTERN.search(relative.as_posix()):
            dirs.add(relative)
    return dirs


def _allowed_extra(side: Side, relative: Path) -> bool:
    if relative.name == "README.md" and len(relative.parts) == 1:
        return True
    if side is Side.STREAMLINED and relative.parts[0] == "models":
        return True
    if side is Side.TESTING:
        if relative.name.startswith("00-") and len(relative.parts) == 1:
            return True
        if relative.parts[0] in EXTRA_TEST_DIRS:
            return True
    return False


def _mirror_findings(
    side: Side,
    mirror: Path,
    docs: set[Path],
    dirs: set[Path],
) -> Iterable[Finding]:
    for relative in sorted(docs):
        if not (mirror / relative).is_file():
            yield Finding(
                finding_type=FindingType.MISSING_DOC,
                side=side,
                relative_path=relative.as_posix(),
                reason="pipeline stage doc has no mirror counterpart",
            )
    for relative in sorted(dirs):
        if not (mirror / relative).is_dir():
            yield Finding(
                finding_type=FindingType.MISSING_DIR,
                side=side,
                relative_path=relative.as_posix(),
                reason="pipeline stage folder has no mirror counterpart",
            )
    for path in sorted(mirror.rglob("*.md")):
        relative = path.relative_to(mirror)
        if relative in docs or _allowed_extra(side, relative):
            continue
        yield Finding(
            finding_type=FindingType.UNEXPECTED_DOC,
            side=side,
            relative_path=relative.as_posix(),
            reason="mirror doc has no pipeline counterpart and is not an allowed addition",
        )


def check(root: Path = REPO) -> Report:
    """Check one repository root and return every structural finding."""

    pipeline = root / PIPELINE
    if not pipeline.is_dir():
        raise FileNotFoundError(f"pipeline docs not found: {pipeline}")

    docs = expected_docs(pipeline)
    dirs = expected_dirs(pipeline)
    findings = list(_mirror_findings(Side.STREAMLINED, root / STREAMLINED, docs, dirs))
    findings.extend(_mirror_findings(Side.TESTING, root / TESTING, docs, dirs))
    return Report(
        findings=findings,
        docs_checked=len(docs),
        dirs_checked=len(dirs),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO, help="repository root")
    parser.add_argument("--quiet", action="store_true", help="print only failures")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO if args.quiet else logging.DEBUG)
    report = check(args.root)

    if report.ok:
        if not args.quiet:
            print(
                f"doc mirror ok: {report.docs_checked} docs, "
                f"{report.dirs_checked} folders in both trees"
            )
        return 0

    for finding in report.findings:
        print(
            f"{finding.side.value}/{finding.relative_path}: "
            f"{finding.finding_type.value} ({finding.reason})",
            file=sys.stderr,
        )
    print(
        f"doc mirror failed: {len(report.findings)} finding(s) across "
        f"{report.docs_checked} docs and {report.dirs_checked} folders",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
