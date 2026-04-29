"""Bounded source-level counterfactual generation."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Any

from cad_qa.hashing import sha256_text


@dataclass(frozen=True)
class CounterfactualVariant:
    group_id: str
    variant_id: str
    original_code: str
    variant_code: str
    changed_value: float
    new_value: float
    source_line: int | None
    source_column: int | None


def numeric_parameter_variants(
    code: str,
    *,
    relative_delta: float = 0.1,
    max_variants: int = 4,
) -> list[CounterfactualVariant]:
    tree = ast.parse(code)
    constants = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, (int, float))
        and not isinstance(node.value, bool)
        and float(node.value) != 0.0
    ]
    variants = []
    group_id = "cfgrp_" + sha256_text(code).removeprefix("sha256:")[:16]
    for index, node in enumerate(constants[:max_variants]):
        for direction, factor in (
            ("increase", 1.0 + relative_delta),
            ("decrease", 1.0 - relative_delta),
        ):
            new_value = float(node.value) * factor
            transformer = _ReplaceConstant(node.lineno, node.col_offset, new_value)
            variant_tree = transformer.visit(ast.parse(code))
            ast.fix_missing_locations(variant_tree)
            variant_code = ast.unparse(variant_tree) + "\n"
            variants.append(
                CounterfactualVariant(
                    group_id=group_id,
                    variant_id=f"{group_id}_{index:04d}_{direction}",
                    original_code=code,
                    variant_code=variant_code,
                    changed_value=float(node.value),
                    new_value=new_value,
                    source_line=node.lineno,
                    source_column=node.col_offset,
                )
            )
    return variants


class _ReplaceConstant(ast.NodeTransformer):
    def __init__(self, lineno: int, col_offset: int, value: float) -> None:
        self.lineno = lineno
        self.col_offset = col_offset
        self.value = value

    def visit_Constant(self, node: ast.Constant) -> Any:  # noqa: N802
        if node.lineno == self.lineno and node.col_offset == self.col_offset:
            return ast.copy_location(ast.Constant(value=self.value), node)
        return node
