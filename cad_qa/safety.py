"""Static source safety checks before optional execution."""

from __future__ import annotations

import ast

DANGEROUS_CALLS = {
    "eval",
    "exec",
    "compile",
    "open",
    "__import__",
    "input",
}

DANGEROUS_MODULES = {
    "os",
    "sys",
    "subprocess",
    "socket",
    "pathlib",
    "shutil",
    "requests",
    "urllib",
    "http",
}

ALLOWED_IMPORTS = {
    "cadquery",
    "math",
}


def safety_issues(code: str) -> list[str]:
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return [f"source_parse_error:{exc.lineno}:{exc.msg}"]

    issues: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            issues.extend(_import_issues(node))
        elif isinstance(node, ast.Call):
            call_name = _call_name(node.func)
            if call_name in DANGEROUS_CALLS:
                issues.append(f"dangerous_call:{call_name}")
            if call_name in {"system", "popen", "remove", "unlink", "rmtree"}:
                issues.append(f"dangerous_method:{call_name}")
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            issues.append("unsupported_with_statement")
        elif isinstance(node, (ast.For, ast.While, ast.AsyncFor)):
            issues.append("unsupported_loop")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            issues.append("unsupported_definition")
    return sorted(set(issues))


def is_safe_for_execution(code: str) -> bool:
    return not safety_issues(code)


def _import_issues(node: ast.Import | ast.ImportFrom) -> list[str]:
    issues: list[str] = []
    if isinstance(node, ast.Import):
        names = [alias.name for alias in node.names]
    else:
        names = [node.module or ""]
    for name in names:
        top = name.split(".", 1)[0]
        if top in DANGEROUS_MODULES:
            issues.append(f"dangerous_import:{top}")
        elif top and top not in ALLOWED_IMPORTS:
            issues.append(f"unsupported_import:{top}")
    return issues


def _call_name(func: ast.AST) -> str | None:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None
