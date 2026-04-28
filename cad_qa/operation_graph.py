"""AST-backed operation graph extraction for CadQuery-like scripts."""

from __future__ import annotations

import ast
from dataclasses import asdict
from typing import Any

from cad_qa.hashing import sha256_json
from cad_qa.schema import OperationNode

FINAL_RESULT_NAMES = ("result", "shape", "solid", "part")
CADQUERY_ALIASES = {"cq", "cadquery"}
ALIAS_OPERATIONS = {
    "cutThruAll": "cut_thru_all",
    "cutBlind": "cut_blind",
}
NON_OPERATION_METHODS = {"val", "vals", "objects", "all"}


def extract_operation_graph(code: str) -> tuple[list[OperationNode], str | None, list[str]]:
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return [], None, [f"source_parse_error:{exc.lineno}:{exc.msg}"]

    extractor = _GraphExtractor()
    for statement in tree.body:
        extractor.visit_statement(statement)
    result_variable = extractor.detect_result_variable()
    return extractor.nodes, result_variable, extractor.issues


def operation_graph_hash(nodes: list[OperationNode]) -> str:
    return sha256_json([asdict(node) for node in nodes])


def operation_signature_hash(nodes: list[OperationNode]) -> str:
    return sha256_json(
        [
            {
                "operation": node.operation,
                "args": [_arg_class(arg) for arg in node.args_repr],
                "inputs": sorted(node.input_features),
            }
            for node in nodes
            if node.status == "ok"
        ]
    )


class _GraphExtractor:
    def __init__(self) -> None:
        self.nodes: list[OperationNode] = []
        self.issues: list[str] = []
        self.feature_by_variable: dict[str, str] = {}
        self.assigned_names: list[str] = []

    def visit_statement(self, statement: ast.stmt) -> None:
        if isinstance(statement, ast.Import):
            self._record_import_aliases(statement)
            return
        if isinstance(statement, ast.ImportFrom):
            return
        if isinstance(statement, ast.Assign) and len(statement.targets) == 1:
            target = _target_name(statement.targets[0])
            if target is not None:
                self.assigned_names.append(target)
                self._visit_assignment(target, statement.value, statement.lineno)
                return
        if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call):
            self._add_call_node(None, statement.value, statement.lineno, status="partial")
            return
        if isinstance(statement, (ast.Pass,)):
            return
        self.issues.append(f"unsupported_statement:{type(statement).__name__}:{getattr(statement, 'lineno', None)}")

    def detect_result_variable(self) -> str | None:
        for name in FINAL_RESULT_NAMES:
            if name in self.assigned_names:
                return name
        for name in reversed(self.assigned_names):
            if name in self.feature_by_variable:
                return name
        return None

    def _record_import_aliases(self, statement: ast.Import) -> None:
        for alias in statement.names:
            if alias.name == "cadquery" and alias.asname:
                CADQUERY_ALIASES.add(alias.asname)

    def _visit_assignment(self, target: str, value: ast.AST, lineno: int) -> None:
        if isinstance(value, ast.Name):
            if value.id in self.feature_by_variable:
                self.feature_by_variable[target] = self.feature_by_variable[value.id]
            return
        if isinstance(value, ast.Call):
            calls = _flatten_call_chain(value)
            if len(calls) > 1:
                previous_target: str | None = None
                for index, call in enumerate(calls):
                    node_target = target if index == len(calls) - 1 else f"{target}__chain_{index:02d}"
                    node = self._add_call_node(node_target, call, lineno)
                    previous_target = node.feature_id if node is not None else previous_target
                if previous_target:
                    self.feature_by_variable[target] = previous_target
                return
            self._add_call_node(target, value, lineno)
            return
        if isinstance(value, (ast.Constant, ast.List, ast.Tuple, ast.Dict, ast.UnaryOp, ast.BinOp)):
            return
        self.issues.append(f"unsupported_assignment_value:{type(value).__name__}:{lineno}")

    def _add_call_node(
        self,
        target: str | None,
        call: ast.Call,
        lineno: int,
        *,
        status: str = "ok",
    ) -> OperationNode | None:
        base, operation = _call_base_and_operation(call.func)
        if operation is None:
            self.issues.append(f"unsupported_call:{lineno}")
            return None
        operation = normalize_operation(operation)
        if operation in NON_OPERATION_METHODS:
            status = "partial"
        feature_id = target or f"op{len(self.nodes):04d}"
        inputs = _input_features(call, base, self.feature_by_variable)
        node = OperationNode(
            feature_id=feature_id,
            step_index=len(self.nodes),
            source_line=lineno,
            target=target,
            base=base,
            operation=operation,
            args_repr=[_safe_unparse(arg) for arg in [*call.args, *[kw.value for kw in call.keywords]]],
            input_features=inputs,
            status=status,
        )
        self.nodes.append(node)
        if target is not None:
            self.feature_by_variable[target] = feature_id
        return node


def normalize_operation(operation: str) -> str:
    return ALIAS_OPERATIONS.get(operation, operation)


def _flatten_call_chain(call: ast.Call) -> list[ast.Call]:
    chain: list[ast.Call] = []
    current: ast.AST | None = call
    while isinstance(current, ast.Call):
        chain.append(current)
        func = current.func
        current = func.value if isinstance(func, ast.Attribute) else None
    chain.reverse()
    return chain


def _call_base_and_operation(func: ast.AST) -> tuple[str | None, str | None]:
    if isinstance(func, ast.Attribute):
        return _base_name(func.value), func.attr
    if isinstance(func, ast.Name):
        return None, func.id
    return None, None


def _base_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        left = _base_name(node.value)
        return f"{left}.{node.attr}" if left else node.attr
    if isinstance(node, ast.Call):
        return _base_name(node.func)
    if isinstance(node, ast.Subscript):
        return _base_name(node.value)
    return None


def _target_name(target: ast.AST) -> str | None:
    return target.id if isinstance(target, ast.Name) else None


def _input_features(call: ast.Call, base: str | None, feature_by_variable: dict[str, str]) -> list[str]:
    inputs: list[str] = []
    if base in feature_by_variable:
        inputs.append(feature_by_variable[base])
    for node in ast.walk(call):
        if isinstance(node, ast.Name) and node.id in feature_by_variable:
            feature = feature_by_variable[node.id]
            if feature not in inputs:
                inputs.append(feature)
    return inputs


def _safe_unparse(node: ast.AST) -> str:
    try:
        return ast.unparse(node)
    except Exception:
        return f"<{type(node).__name__}>"


def _arg_class(value: str) -> str:
    if value.startswith(("'", '"')):
        return "string"
    if value.replace(".", "", 1).replace("-", "", 1).isdigit():
        return "number"
    if value.startswith("[") or value.startswith("("):
        return "sequence"
    return "symbol"


def operation_nodes_to_dicts(nodes: list[OperationNode]) -> list[dict[str, Any]]:
    return [asdict(node) for node in nodes]
