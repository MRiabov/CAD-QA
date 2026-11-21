"""Answer comparison and the literal-answer check."""

from __future__ import annotations

import ast

from experiments.old.cq_query_scratch.models import AnswerFormat, Point3


def _close(a: float, b: float, rel: float, abs_tol: float) -> bool:
    return abs(a - b) <= max(abs_tol, rel * abs(b))


def answers_match(answer, gold: float | int | Point3, fmt: AnswerFormat, rel: float, abs_tol: float) -> bool:
    match fmt:
        case AnswerFormat.INTEGER:
            return isinstance(answer, (int, float)) and not isinstance(answer, bool) and \
                float(answer).is_integer() and int(answer) == int(gold)
        case AnswerFormat.NUMBER:
            return isinstance(answer, (int, float)) and not isinstance(answer, bool) and \
                _close(float(answer), float(gold), rel, abs_tol)
        case AnswerFormat.COORDINATE:
            return isinstance(answer, list) and len(answer) == 3 and all(
                _close(float(a), float(g), rel, abs_tol) for a, g in zip(answer, gold))
    return False


def _is_literal(node: ast.AST) -> bool:
    match node:
        case ast.Constant():
            return True
        case ast.UnaryOp(operand=operand):
            return _is_literal(operand)
        case ast.Tuple(elts=elts) | ast.List(elts=elts):
            return all(_is_literal(e) for e in elts)
    return False


def assigns_literal_answer(code: str) -> bool:
    """True when ``answer`` is only ever bound to bare constants: every assignment is a literal and it
    is never updated (``answer += ...``) or bound by a loop/with/walrus. ``answer = 0`` followed by
    accumulation is not a literal answer."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return False
    literal_assignments = 0
    for node in ast.walk(tree):
        match node:
            case ast.Assign(targets=targets, value=value) if any(
                    isinstance(t, ast.Name) and t.id == "answer" for t in targets):
                if not _is_literal(value):
                    return False
                literal_assignments += 1
            case ast.AnnAssign(target=ast.Name(id="answer"), value=value) if value is not None:
                if not _is_literal(value):
                    return False
                literal_assignments += 1
            case ast.AugAssign(target=ast.Name(id="answer")) | ast.NamedExpr(target=ast.Name(id="answer")):
                return False
            case ast.For(target=ast.Name(id="answer")) | ast.withitem(optional_vars=ast.Name(id="answer")):
                return False
    return literal_assignments > 0


FORBIDDEN_MODULES = {"os", "sys", "subprocess", "socket", "shutil", "pathlib", "importlib", "ctypes", "signal",
                     "multiprocessing", "threading", "requests", "urllib", "http", "builtins", "resource", "pty"}
FORBIDDEN_CALLS = {"open", "exec", "eval", "compile", "__import__", "globals", "locals", "vars", "getattr",
                   "setattr", "delattr", "input", "breakpoint"}


def escape_attempt(code: str) -> str | None:
    """Reason string when code reaches outside CadQuery computation (files, processes, network, introspection)."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        match node:
            case ast.Import(names=names):
                for a in names:
                    if a.name.split(".")[0] in FORBIDDEN_MODULES:
                        return f"import {a.name}"
            case ast.ImportFrom(module=module) if module and module.split(".")[0] in FORBIDDEN_MODULES:
                return f"from {module} import"
            case ast.Call(func=ast.Name(id=name)) if name in FORBIDDEN_CALLS:
                return f"call {name}()"
            case ast.Attribute(attr=attr) if attr.startswith("__") and attr.endswith("__"):
                return f"dunder attribute {attr}"
    return None
