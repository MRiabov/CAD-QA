"""AST-backed CAD ontology graph extraction."""

from __future__ import annotations

import ast
import math
from dataclasses import dataclass
from typing import Any

from cad_qa.ontology.material_regions import feature_effect_from_profile
from cad_qa.ontology.nodes import Measurement, Node, OntologyGraph, Relation
from cad_qa.ontology.profile_geometry import circle_profile, polyline_profile, rect_profile
from cad_qa.ontology.workplane_frames import (
    default_workplane_frame,
    explicit_workplane_frame,
    project_local_point,
)
from cad_qa.source import SourceRecord, source_to_dict


@dataclass(frozen=True)
class OperationRecord:
    id: str
    target: str
    operation: str
    base: str | None
    args: list[Any]
    kwargs: dict[str, Any]
    source_line: int
    chain_index: int


def build_graph(source: SourceRecord) -> OntologyGraph:
    tree = ast.parse(source.source_code)
    extractor = _Extractor(source, tree)
    return extractor.build()


class _Extractor:
    def __init__(self, source: SourceRecord, tree: ast.Module):
        self.source = source
        self.tree = tree
        self.graph = OntologyGraph(
            graph_id=f"graph:{source.source_id}",
            source=source_to_dict(source),
        )
        self.env: dict[str, Any] = {"math": math}
        self.operations: list[OperationRecord] = []
        self.assignment_exprs: dict[str, ast.AST] = {}
        self.variable_workplanes: dict[str, str] = {}
        self.variable_profiles: dict[str, str] = {}
        self.variable_features: dict[str, str] = {}
        self.operation_ids: set[str] = set()
        self.selector_ids_by_text: dict[str, list[str]] = {}

    def build(self) -> OntologyGraph:
        self.graph.add_node(
            Node(
                id=f"source:{self.source.source_id}",
                type="source",
                label=self.source.source_id,
                properties={"path": self.source.source_path},
            )
        )
        self._collect_safe_bindings()
        for statement in self.tree.body:
            self._extract_statement(statement)
        self._add_temporal_relations()
        return self.graph

    def _extract_statement(self, statement: ast.stmt) -> None:
        if isinstance(statement, ast.Assign) and len(statement.targets) == 1:
            target = _target_name(statement.targets[0])
            if target:
                self.assignment_exprs[target] = statement.value
                try:
                    self.env[target] = _safe_eval(statement.value, self.env)
                except Exception:
                    pass
                self._extract_assignment(target, statement.value, statement.lineno)
        elif isinstance(statement, ast.For):
            loop_name = _target_name(statement.target)
            if not loop_name:
                return
            try:
                values = _safe_eval(statement.iter, self.env)
            except Exception:
                self.graph.diagnostics.append(
                    {"kind": "loop_not_unrolled", "source_line": statement.lineno}
                )
                return
            if not isinstance(values, (list, tuple)) or len(values) > 64:
                self.graph.diagnostics.append(
                    {"kind": "loop_not_unrolled", "source_line": statement.lineno, "reason": "unsupported_iterable"}
                )
                return
            previous = self.env.get(loop_name)
            for index, value in enumerate(values):
                self.env[loop_name] = value
                for body_statement in statement.body:
                    self._extract_statement(body_statement)
                self.graph.diagnostics.append(
                    {"kind": "loop_unrolled", "source_line": statement.lineno, "iteration": index, "value": value}
                )
            if previous is None:
                self.env.pop(loop_name, None)
            else:
                self.env[loop_name] = previous

    def _collect_safe_bindings(self) -> None:
        for statement in self.tree.body:
            if isinstance(statement, ast.Assign) and len(statement.targets) == 1:
                name = _target_name(statement.targets[0])
                if name:
                    try:
                        self.env[name] = _safe_eval(statement.value, self.env)
                    except Exception:
                        pass
            elif isinstance(statement, ast.FunctionDef):
                try:
                    self.env[statement.name] = _compile_safe_function(statement, self.env)
                except Exception:
                    pass

    def _extract_assignment(self, target: str, expr: ast.AST, lineno: int) -> None:
        if not isinstance(expr, ast.Call):
            return
        chain = _call_chain(expr, self.env)
        previous_id: str | None = None
        for index, call in enumerate(chain):
            base = call["base"] if call["base"] is not None else (target if index > 0 else None)
            op_id = self._operation_id(target, call["operation"], index, len(chain))
            record = OperationRecord(
                id=op_id,
                target=target,
                operation=call["operation"],
                base=base,
                args=call["args"],
                kwargs=call["kwargs"],
                source_line=lineno,
                chain_index=index,
            )
            self.operations.append(record)
            self._add_operation(record)
            if previous_id:
                self.graph.add_relation(
                    Relation(previous_id, op_id, "input_to", evidence={"source_line": lineno})
                )
            previous_id = op_id
        final = self.operations[-1] if self.operations and self.operations[-1].target == target else None
        if final:
            self._add_feature(target, final)

    def _operation_id(self, target: str, operation: str, index: int, chain_length: int) -> str:
        base = f"operation:{target}" if chain_length == 1 else f"operation:{target}:{index}:{operation}"
        if base not in self.operation_ids:
            self.operation_ids.add(base)
            return base
        suffix = len(self.operation_ids)
        unique = f"{base}:{suffix}"
        self.operation_ids.add(unique)
        return unique

    def _add_operation(self, record: OperationRecord) -> None:
        self.graph.add_node(
            Node(
                id=record.id,
                type="operation",
                label=f"{record.target} = {record.operation}(...)",
                source_ref=str(record.source_line),
                properties={
                    "target": record.target,
                    "operation": record.operation,
                    "base": record.base,
                    "args": record.args,
                    "kwargs": record.kwargs,
                    "chain_index": record.chain_index,
                },
            )
        )
        for value in [*record.args, *record.kwargs.values()]:
            if _is_public_parameter(value):
                param_id = f"parameter:{record.id}:{len(self.graph.nodes)}"
                self.graph.add_node(
                    Node(
                        id=param_id,
                        type="parameter",
                        label=repr(value),
                        source_ref=str(record.source_line),
                        properties={"value": value},
                    )
                )
                self.graph.add_relation(Relation(param_id, record.id, "parameter_of"))
        for input_id in self._input_feature_ids(record):
            self.graph.add_relation(Relation(input_id, record.id, "input_to"))
        if record.operation in {"Workplane", "workplane"}:
            self._extract_workplane(record)
        if record.operation in {"circle", "rect", "polyline"}:
            self._extract_profile(record)
        if record.operation == "splineApprox":
            self._extract_path(record)
        if record.operation == "faces":
            self._extract_selector(record)

    def _add_feature(self, target: str, record: OperationRecord) -> None:
        feature_id = self._unique_node_id(f"feature:{target}")
        self.variable_features[target] = feature_id
        self.graph.add_node(
            Node(
                id=feature_id,
                type="feature",
                label=target,
                source_ref=str(record.source_line),
                properties={
                    "target": target,
                    "operation": record.operation,
                    "operation_id": record.id,
                    "step_index": len(self.operations) - 1,
                },
            )
        )
        self.graph.add_relation(Relation(record.id, feature_id, "created_by"))
        for input_id in self._input_feature_ids(record):
            self.graph.add_relation(Relation(input_id, feature_id, "input_to"))
        if record.operation in {"extrude", "cutBlind", "cutThruAll", "sweep"}:
            profile_id = self.variable_profiles.get(str(record.base))
            if profile_id:
                self.graph.add_relation(Relation(feature_id, profile_id, "uses_profile"))
                self.graph.add_relation(Relation(profile_id, feature_id, "used_by"))
                self._attach_profile_application_effect(feature_id, profile_id, record)
                self._add_region_projection(feature_id, profile_id, record)
        if record.operation == "union":
            self.graph.add_node(Node(id=f"solid:{target}", type="solid", label=target))
            self.graph.add_relation(Relation(feature_id, f"solid:{target}", "adds_material_to"))
        if record.operation.startswith("cut"):
            self.graph.add_relation(Relation(feature_id, f"source:{self.source.source_id}", "removes_material_from"))

    def _extract_workplane(self, record: OperationRecord) -> None:
        frame: dict[str, Any] | None = None
        if record.operation == "Workplane":
            plane = str(record.args[0]) if record.args else "XY"
            origin = _coerce_vector(record.kwargs.get("origin")) or [0.0, 0.0, 0.0]
            if record.args and isinstance(record.args[0], dict) and record.args[0].get("kind") == "plane":
                plane_arg = record.args[0]
                frame = explicit_workplane_frame(
                    origin=plane_arg["origin"],
                    x_axis=plane_arg.get("xDir") or [1.0, 0.0, 0.0],
                    normal=plane_arg.get("normal") or [0.0, 0.0, 1.0],
                )
            else:
                frame = default_workplane_frame(plane, origin)
        elif record.operation == "workplane":
            frame = default_workplane_frame("derived", [0.0, 0.0, 0.0])
        if frame is None:
            return
        node_id = self._unique_node_id(f"workplane:{record.target}")
        self.variable_workplanes[record.target] = node_id
        self.graph.add_node(
            Node(
                id=node_id,
                type="workplane",
                label=record.target,
                source_ref=str(record.source_line),
                properties=frame,
            )
        )
        for name, value in {"origin": frame["origin"], "normal": frame["normal"], "origin_z": frame["origin"][2]}.items():
            self.graph.add_measurement(
                Measurement(node_id, "entity_geometry", name, value, evidence={"source_line": record.source_line})
            )

    def _extract_profile(self, record: OperationRecord) -> None:
        try:
            if record.operation == "circle":
                geom = circle_profile(float(record.args[0]))
            elif record.operation == "rect":
                geom = rect_profile(float(record.args[0]), float(record.args[1]))
            else:
                points = record.args[0]
                geom = polyline_profile(points, closed=True)
        except Exception as exc:
            self.graph.diagnostics.append(
                {"kind": "profile_extraction_failed", "target": record.target, "reason": str(exc)}
            )
            return
        profile_id = self._unique_node_id(f"profile:{record.target}")
        self.variable_profiles[record.target] = profile_id
        self.graph.add_node(
            Node(
                id=profile_id,
                type="profile",
                label=record.target,
                source_ref=str(record.source_line),
                properties=geom,
            )
        )
        for key in ["area", "perimeter", "centroid", "local_bbox", "edge_count", "vertex_count"]:
            self.graph.add_measurement(
                Measurement(profile_id, "profile_intrinsic", key, geom[key], evidence={"source_line": record.source_line})
            )
        self.graph.add_relation(Relation(f"feature:{record.target}", profile_id, "uses_profile"))
        self.graph.add_relation(Relation(profile_id, f"feature:{record.target}", "used_by"))
        workplane_id = self.variable_workplanes.get(str(record.base))
        if workplane_id:
            self.graph.add_relation(Relation(profile_id, workplane_id, "located_on"))
            centroid = geom.get("centroid")
            workplane = self.graph.node(workplane_id)
            if isinstance(centroid, list) and workplane:
                self.graph.add_measurement(
                    Measurement(
                        profile_id,
                        "entity_geometry",
                        "world_centroid",
                        project_local_point(workplane.properties, centroid),
                        evidence={"relation": "located_on"},
                    )
                )
                centroid_id = self._unique_node_id(f"centroid:{record.target}")
                world_centroid = project_local_point(workplane.properties, centroid)
                self.graph.add_node(
                    Node(
                        id=centroid_id,
                        type="centroid",
                        label=f"{record.target} centroid",
                        source_ref=str(record.source_line),
                        properties={"coordinate": world_centroid},
                    )
                )
                self.graph.add_relation(Relation(profile_id, centroid_id, "has_centroid"))
                self.graph.add_measurement(
                    Measurement(
                        centroid_id,
                        "entity_geometry",
                        "coordinate",
                        world_centroid,
                        evidence={"profile_id": profile_id},
                    )
                )
                self.graph.add_measurement(
                    Measurement(
                        profile_id,
                        "entity_geometry",
                        "workplane_origin_z",
                        workplane.properties["origin"][2],
                        evidence={"relation": "located_on"},
                    )
                )
        if record.operation == "polyline":
            sketch_id = self._unique_node_id(f"sketch:{record.target}")
            self.graph.add_node(
                Node(
                    id=sketch_id,
                    type="sketch",
                    label=f"{record.target} point list",
                    source_ref=str(record.source_line),
                    properties={"points": geom.get("points"), "center": geom.get("centroid")},
                )
            )
            self.graph.add_relation(Relation(sketch_id, profile_id, "uses_profile"))
            self.graph.add_relation(Relation(sketch_id, profile_id, "has_sketch_center"))

    def _extract_path(self, record: OperationRecord) -> None:
        points = record.args[0] if record.args else []
        path_id = f"path:{record.target}"
        self.graph.add_node(
            Node(
                id=path_id,
                type="path",
                label=record.target,
                source_ref=str(record.source_line),
                properties={"points": points},
            )
        )
        if isinstance(points, list) and len(points) >= 2:
            tangent = [
                float(points[1][i]) - float(points[0][i])
                for i in range(min(3, len(points[0])))
            ]
            self.graph.add_measurement(
                Measurement(path_id, "entity_geometry", "initial_tangent", tangent, evidence={"source_line": record.source_line})
            )
            self.graph.add_relation(Relation(path_id, path_id, "has_path_tangent"))
            xs = [float(point[0]) for point in points]
            ys = [float(point[1]) for point in points]
            zs = [float(point[2]) if len(point) > 2 else 0.0 for point in points]
            self.graph.add_measurement(
                Measurement(path_id, "entity_geometry", "path_bbox", {"min": [min(xs), min(ys), min(zs)], "max": [max(xs), max(ys), max(zs)]}, evidence={"source_line": record.source_line})
            )
            self.graph.add_measurement(
                Measurement(path_id, "entity_geometry", "nearest_point_to_origin", min(points, key=lambda point: sum(float(v) * float(v) for v in point[:3])), evidence={"source_line": record.source_line})
            )
            nearest_distance = min(math.sqrt(sum(float(v) * float(v) for v in point[:3])) for point in points)
            self.graph.add_measurement(
                Measurement(path_id, "relation_metric", "nearest_point_distance_to_origin", nearest_distance, evidence={"source_line": record.source_line})
            )
            self.graph.add_relation(Relation(path_id, path_id, "nearest_point_on_path"))

    def _extract_selector(self, record: OperationRecord) -> None:
        selector_text = str(record.args[0]) if record.args else record.target
        selector_id = self._unique_node_id(f"selector:{_slug(selector_text)}")
        self.graph.add_node(
            Node(
                id=selector_id,
                type="selector",
                label=selector_text,
                source_ref=str(record.source_line),
                properties={"selector": record.args[0] if record.args else None},
            )
        )
        self.graph.add_relation(Relation(selector_id, record.id, "selected_by"))
        self.graph.add_measurement(
            Measurement(selector_id, "snapshot_state", "source_line", record.source_line, evidence={"operation_id": record.id})
        )
        self.graph.add_measurement(
            Measurement(selector_id, "snapshot_state", "operation_index", len(self.operations) - 1, evidence={"operation_id": record.id})
        )
        face_id = f"face:{_slug(selector_text)}"
        self.graph.add_node(
            Node(
                id=face_id,
                type="face",
                label=f"face selected by {selector_text}",
                source_ref=str(record.source_line),
                properties={"stable_selector": selector_text},
            )
        )
        self.graph.add_relation(Relation(face_id, selector_id, "selected_by"))
        self.graph.add_relation(Relation(face_id, selector_id, "has_stable_face_id"))
        for previous_selector_id in self.selector_ids_by_text.get(selector_text, []):
            self.graph.add_relation(Relation(selector_id, previous_selector_id, "same_selected_face_as"))
            self.graph.add_relation(Relation(previous_selector_id, selector_id, "same_selected_face_as"))
        self.selector_ids_by_text.setdefault(selector_text, []).append(selector_id)

    def _attach_profile_application_effect(
        self, feature_id: str, profile_id: str, record: OperationRecord
    ) -> None:
        profile = self.graph.node(profile_id)
        if profile is None:
            return
        distance = _first_number(record.args)
        effect = feature_effect_from_profile(profile.properties, record.operation, distance)
        for name, value in effect.items():
            if name in {"operation", "evidence"}:
                continue
            self.graph.add_measurement(
                Measurement(feature_id, "feature_application_effect", name, value, evidence={"profile_id": profile_id})
            )

    def _add_region_projection(self, feature_id: str, profile_id: str, record: OperationRecord) -> None:
        profile = self.graph.node(profile_id)
        if profile is None:
            return
        region_type = "void_region" if record.operation.startswith("cut") else "material_region"
        region_id = self._unique_node_id(f"{region_type}:{record.target}")
        distance = _first_number(record.args) or 0.0
        area = float(profile.properties.get("area") or 0.0)
        volume = area * abs(distance)
        centroid_measurements = self.graph.measurements_for(profile_id, "world_centroid")
        centroid = centroid_measurements[0].value if centroid_measurements else [0.0, 0.0, 0.0]
        self.graph.add_node(
            Node(
                id=region_id,
                type=region_type,
                label=f"{record.target} projected {region_type}",
                source_ref=str(record.source_line),
                properties={"conservative": True, "operation": record.operation},
            )
        )
        relation = "removes_material_from" if region_type == "void_region" else "adds_material_to"
        geometry_relation = "has_void_region_geometry" if region_type == "void_region" else "has_material_region_geometry"
        self.graph.add_relation(Relation(feature_id, region_id, relation))
        self.graph.add_relation(Relation(region_id, profile_id, "created_by"))
        self.graph.add_relation(Relation(region_id, region_id, geometry_relation))
        self.graph.add_measurement(Measurement(region_id, "entity_geometry", "volume", volume, "mm^3", {"profile_id": profile_id}))
        self.graph.add_measurement(Measurement(region_id, "entity_geometry", "centroid", centroid, "mm", {"profile_id": profile_id}))
        if isinstance(centroid, list) and len(centroid) >= 3:
            self.graph.add_measurement(Measurement(region_id, "entity_geometry", "centroid_z", centroid[2], "mm", {"profile_id": profile_id}))
        self.graph.add_measurement(Measurement(region_id, "snapshot_state", "source_line", record.source_line, None, {"profile_id": profile_id}))
        self.graph.add_measurement(Measurement(region_id, "snapshot_state", "operation_index", len(self.operations) - 1, None, {"profile_id": profile_id}))

    def _unique_node_id(self, base: str) -> str:
        if self.graph.node(base) is None:
            return base
        index = 1
        while self.graph.node(f"{base}:{index}") is not None:
            index += 1
        return f"{base}:{index}"

    def _add_temporal_relations(self) -> None:
        for earlier, later in zip(self.operations, self.operations[1:], strict=False):
            self.graph.add_relation(Relation(earlier.id, later.id, "before"))
            self.graph.add_relation(Relation(later.id, earlier.id, "after"))

    def _input_feature_ids(self, record: OperationRecord) -> list[str]:
        ids: list[str] = []
        if isinstance(record.base, str) and record.base in self.assignment_exprs:
            ids.append(self.variable_features.get(record.base, f"feature:{record.base}"))
        for arg in record.args:
            if isinstance(arg, str) and arg in self.assignment_exprs:
                ids.append(self.variable_features.get(arg, f"feature:{arg}"))
        return ids


def _call_chain(call: ast.Call, env: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(call.func, ast.Attribute):
        base_expr = call.func.value
        base_name = _base_name(base_expr)
        prefix = _call_chain(base_expr, env) if isinstance(base_expr, ast.Call) else []
        return [
            *prefix,
            {
                "operation": call.func.attr,
                "base": base_name,
                "args": [_literal_or_repr(arg, env) for arg in call.args],
                "kwargs": {kw.arg or "": _literal_or_repr(kw.value, env) for kw in call.keywords},
            },
        ]
    if isinstance(call.func, ast.Name):
        return [
            {
                "operation": call.func.id,
                "base": None,
                "args": [_literal_or_repr(arg, env) for arg in call.args],
                "kwargs": {kw.arg or "": _literal_or_repr(kw.value, env) for kw in call.keywords},
            }
        ]
    return []


def _target_name(target: ast.AST) -> str | None:
    return target.id if isinstance(target, ast.Name) else None


def _base_name(expr: ast.AST) -> str | None:
    if isinstance(expr, ast.Name):
        return expr.id
    if isinstance(expr, ast.Attribute):
        base = _base_name(expr.value)
        return f"{base}.{expr.attr}" if base else expr.attr
    if isinstance(expr, ast.Call):
        return None
    return ast.unparse(expr)


def _literal_or_repr(expr: ast.AST, env: dict[str, Any]) -> Any:
    try:
        return _safe_eval(expr, env)
    except Exception:
        if isinstance(expr, ast.Name):
            return expr.id
        return ast.unparse(expr)


def _safe_eval(expr: ast.AST, env: dict[str, Any]) -> Any:
    if isinstance(expr, ast.Constant):
        return expr.value
    if isinstance(expr, ast.List):
        return [_safe_eval(item, env) for item in expr.elts]
    if isinstance(expr, ast.Tuple):
        return [_safe_eval(item, env) for item in expr.elts]
    if isinstance(expr, ast.UnaryOp) and isinstance(expr.op, ast.USub):
        return -_safe_eval(expr.operand, env)
    if isinstance(expr, ast.BinOp) and isinstance(expr.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
        left = _safe_eval(expr.left, env)
        right = _safe_eval(expr.right, env)
        if isinstance(expr.op, ast.Add):
            return left + right
        if isinstance(expr.op, ast.Sub):
            return left - right
        if isinstance(expr.op, ast.Mult):
            return left * right
        return left / right
    if isinstance(expr, ast.Name):
        if expr.id in env:
            return env[expr.id]
        raise ValueError(expr.id)
    if isinstance(expr, ast.Attribute):
        base = _safe_eval(expr.value, env)
        return getattr(base, expr.attr)
    if isinstance(expr, ast.Call):
        func_name = ast.unparse(expr.func)
        if func_name in {"cq.Vector", "Vector"}:
            return [_safe_eval(arg, env) for arg in expr.args]
        if func_name in {"cq.Plane", "Plane"}:
            kwargs = {kw.arg: _safe_eval(kw.value, env) for kw in expr.keywords if kw.arg}
            return {"kind": "plane", **kwargs}
        func = _safe_eval(expr.func, env)
        args = [_safe_eval(arg, env) for arg in expr.args]
        kwargs = {kw.arg: _safe_eval(kw.value, env) for kw in expr.keywords if kw.arg}
        return func(*args, **kwargs)
    raise ValueError(ast.dump(expr))


def _compile_safe_function(fn: ast.FunctionDef, env: dict[str, Any]) -> Any:
    module = ast.Module(body=[fn], type_ignores=[])
    ast.fix_missing_locations(module)
    namespace = {"math": math, "__builtins__": {"range": range, "len": len}}
    namespace.update(env)
    exec(compile(module, "<cadqa-safe-function>", "exec"), namespace)  # noqa: S102
    return namespace[fn.name]


def _coerce_vector(value: Any) -> list[float] | None:
    if isinstance(value, (list, tuple)) and len(value) == 3:
        return [float(v) for v in value]
    return None


def _is_public_parameter(value: Any) -> bool:
    return isinstance(value, (int, float, str, bool)) or (
        isinstance(value, list) and len(value) <= 8
    )


def _first_number(values: list[Any]) -> float | None:
    for value in values:
        if isinstance(value, (int, float)):
            return float(value)
    return None


def _slug(value: str) -> str:
    chars = [char.lower() if char.isalnum() else "_" for char in value]
    slug = "".join(chars).strip("_")
    return slug or "value"
