"""Syntax extraction for the Don't-say checker.

The checker owns the banned-term policy; this module owns syntax. Each
extractor reports the names a file declares and the prose fragments that are
not names, so the policy never has to guess where a comment, a literal, or an
identifier ends.

- Python: the standard ``ast`` module, walked once per file.
- Go: ``go/parser`` through ``tools/dont-say-go``, which prints one JSON record
  per declared name and per comment line.
- JSON: ``json`` for the structure, plus a line-aware scan for descriptions.
- Paths: the file stem and every folder name, split into word segments.
"""

from __future__ import annotations

import ast
import json
import logging
import re
import subprocess
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger("cadqa.dont_say_names")

REPO = Path(__file__).resolve().parents[2]
GO_HELPER = REPO / "tools" / "dont-say-go"

# Split a name into the words a reader sees: snake_case, PascalCase,
# kebab-case, and CONSTANT_CASE all become their lowercase segments.
IDENTIFIER_SEGMENT = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|\d+")

# JSON Schema keys whose values are names CAD-QA owns. Every other key is
# schema vocabulary, not a CAD-QA name.
JSON_NAME_MAPS = (
    "$defs",
    "definitions",
    "dependentSchemas",
    "patternProperties",
    "properties",
)
JSON_NAME_LISTS = ("enum",)
JSON_PROSE = re.compile(r'"(?:description|title)"\s*:\s*"((?:[^"\\]|\\.)*)"')
COMMENT_MARKERS = re.compile(r"^\s*(?://+|/\*+|\*+/?)")


class Declaration(BaseModel):
    """One name a file declares, or one comment line, with where it is.

    ``form`` is ``"comment"`` for prose; every other form names a declaration kind
    a reader navigates by (``class``, ``field``, ``file name``, …).
    """

    model_config = ConfigDict(frozen=True)

    path: Path
    line: int = Field(ge=1)
    form: str = Field(min_length=1)
    value: str = Field(min_length=1)


class Fragment(BaseModel):
    """A prose fragment that is not a declaration, such as a JSON description."""

    model_config = ConfigDict(frozen=True)

    line: int = Field(ge=1)
    text: str = Field(min_length=1)


def name_segments(name: str) -> list[str]:
    """The words of an identifier, lowercased, in reader order."""

    return [segment.lower() for segment in IDENTIFIER_SEGMENT.findall(name)]


class _PythonNames(ast.NodeVisitor):
    """Collect every name a Python module declares."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.declarations: list[Declaration] = []
        self._scopes: list[str] = []

    def _add(self, current: ast.AST, form: str, name: str) -> None:
        if not name:
            return
        self.declarations.append(
            Declaration(
                path=self.path,
                line=getattr(current, "lineno", 1),
                form=form,
                value=name,
            )
        )

    def _scope(self) -> str:
        return self._scopes[-1] if self._scopes else "module"

    def visit_ClassDef(self, current: ast.ClassDef) -> None:
        self._add(current, "class", current.name)
        for param in getattr(current, "type_params", ()):
            self._add(param, "type parameter", param.name)
        self._scopes.append("class")
        self.generic_visit(current)
        self._scopes.pop()

    def visit_FunctionDef(self, current: ast.FunctionDef) -> None:
        self._function(current)

    def visit_AsyncFunctionDef(self, current: ast.AsyncFunctionDef) -> None:
        self._function(current)

    def _function(self, current: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        form = "method" if self._scope() == "class" else "function"
        self._add(current, form, current.name)
        for param in getattr(current, "type_params", ()):
            self._add(param, "type parameter", param.name)
        self._scopes.append("function")
        self.generic_visit(current)
        self._scopes.pop()

    def visit_arg(self, current: ast.arg) -> None:
        self._add(current, "parameter", current.arg)

    def visit_Assign(self, current: ast.Assign) -> None:
        form = "field" if self._scope() == "class" else "variable"
        for target in current.targets:
            self._target(target, form)
        self.generic_visit(current)

    def visit_AnnAssign(self, current: ast.AnnAssign) -> None:
        form = "field" if self._scope() == "class" else "variable"
        self._target(current.target, form)
        self.generic_visit(current)

    def visit_AugAssign(self, current: ast.AugAssign) -> None:
        self._target(current.target, "variable")
        self.generic_visit(current)

    def visit_NamedExpr(self, current: ast.NamedExpr) -> None:
        self._target(current.target, "variable")
        self.generic_visit(current)

    def visit_For(self, current: ast.For) -> None:
        self._target(current.target, "variable")
        self.generic_visit(current)

    def visit_AsyncFor(self, current: ast.AsyncFor) -> None:
        self._target(current.target, "variable")
        self.generic_visit(current)

    def visit_comprehension(self, current: ast.comprehension) -> None:
        self._target(current.target, "variable")
        self.generic_visit(current)

    def visit_With(self, current: ast.With) -> None:
        self._with(current)

    def visit_AsyncWith(self, current: ast.AsyncWith) -> None:
        self._with(current)

    def _with(self, current: ast.With | ast.AsyncWith) -> None:
        for item in current.items:
            if item.optional_vars is not None:
                self._target(item.optional_vars, "variable")
        self.generic_visit(current)

    def visit_ExceptHandler(self, current: ast.ExceptHandler) -> None:
        if current.name:
            self._add(current, "variable", current.name)
        self.generic_visit(current)

    def visit_Global(self, current: ast.Global) -> None:
        for name in current.names:
            self._add(current, "variable", name)

    def visit_Nonlocal(self, current: ast.Nonlocal) -> None:
        for name in current.names:
            self._add(current, "variable", name)

    def visit_MatchAs(self, current: ast.MatchAs) -> None:
        if current.name:
            self._add(current, "variable", current.name)
        self.generic_visit(current)

    def visit_MatchStar(self, current: ast.MatchStar) -> None:
        if current.name:
            self._add(current, "variable", current.name)
        self.generic_visit(current)

    def visit_MatchMapping(self, current: ast.MatchMapping) -> None:
        if current.rest:
            self._add(current, "variable", current.rest)
        self.generic_visit(current)

    def visit_TypeAlias(self, current: ast.TypeAlias) -> None:
        if isinstance(current.name, ast.Name):
            self._add(current.name, "type alias", current.name.id)
        self.generic_visit(current)

    def _target(self, target: ast.expr, form: str) -> None:
        match target:
            case ast.Name():
                self._add(target, form, target.id)
            case ast.Attribute():
                self._add(target, "field", target.attr)
            case ast.Starred():
                self._target(target.value, form)
            case ast.Tuple() | ast.List():
                for element in target.elts:
                    self._target(element, form)


def python_declarations(path: Path, text: str) -> list[Declaration]:
    """Every name a Python module declares, plus its prose fragments.

    A module that does not parse raises: skipping it would report a clean file
    that was never read.
    """

    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        raise ValueError(f"{path}: does not parse, names not checked: {exc}") from exc
    collector = _PythonNames(path)
    collector.visit(tree)
    return collector.declarations


def go_declarations(paths: list[Path]) -> list[Declaration]:
    """Every name and comment line the Go files declare, through go/parser."""

    if not paths:
        return []
    try:
        result = subprocess.run(
            ["go", "run", ".", *[str(path) for path in paths]],
            cwd=GO_HELPER,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise RuntimeError(
            f"cannot run the Go declaration helper at {GO_HELPER}: {exc}"
        ) from exc
    if result.returncode != 0:
        raise RuntimeError(
            f"Go declaration helper failed ({result.returncode}):\n{result.stderr.strip()}"
        )
    declarations: list[Declaration] = []
    for line in result.stdout.splitlines():
        raw = json.loads(line)
        declarations.append(
            Declaration(
                path=Path(raw["path"]),
                line=int(raw["line"]),
                form=str(raw["form"]),
                value=str(raw["value"]),
            )
        )
    return declarations


def comment_text(value: str) -> str:
    """A Go comment line without its markers, or the empty string."""

    return COMMENT_MARKERS.sub("", value).strip()


def json_declarations(path: Path, text: str) -> list[Declaration]:
    """The names a JSON document declares: property, definition, enum, const.

    Schema vocabulary is not a CAD-QA name, so only the values of the keys that
    name something CAD-QA owns are checked.
    """

    try:
        document = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: does not parse: {exc}") from exc

    found: list[tuple[str, str]] = []

    def walk(current: object) -> None:
        match current:
            case dict():
                for key, value in current.items():
                    if key in JSON_NAME_MAPS and isinstance(value, dict):
                        for name, child in value.items():
                            found.append((f"JSON {key} name", name))
                            walk(child)
                    elif key in JSON_NAME_LISTS and isinstance(value, list):
                        for item in value:
                            if isinstance(item, str):
                                found.append(("JSON enum value", item))
                    elif key == "const" and isinstance(value, str):
                        found.append(("JSON const value", value))
                    else:
                        walk(value)
            case list():
                for item in current:
                    walk(item)

    walk(document)
    return [
        Declaration(path=path, line=line_of(text, name), form=form, value=name)
        for form, name in found
    ]


def json_prose(text: str) -> list[Fragment]:
    """The description and title strings of a JSON document, with line numbers."""

    fragments: list[Fragment] = []
    for match in JSON_PROSE.finditer(text):
        try:
            decoded = json.loads(f'"{match.group(1)}"')
        except json.JSONDecodeError:
            continue
        if not isinstance(decoded, str) or not decoded.strip():
            continue
        fragments.append(
            Fragment(
                line=text.count("\n", 0, match.start()) + 1,
                text=" ".join(decoded.split()),
            )
        )
    return fragments


def line_of(text: str, name: str) -> int:
    """The first line that names ``name`` as a JSON key or value."""

    match = re.search(rf'"{re.escape(name)}"\s*[,:\]]', text)
    if match is None:
        return 1
    return text.count("\n", 0, match.start()) + 1


def file_declaration(path: Path) -> Declaration:
    """The file stem as a name a reader navigates by."""

    return Declaration(path=path, line=1, form="file name", value=path.stem)


def folder_declaration(folder: Path) -> Declaration:
    """The folder name as a name a reader navigates by."""

    return Declaration(path=folder, line=1, form="folder name", value=folder.name)
