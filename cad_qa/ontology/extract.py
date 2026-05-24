"""AST-backed CAD ontology graph extraction."""

from __future__ import annotations

import ast
from collections.abc import Mapping
import hashlib
import json
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
from cad_qa.trace import TraceRecord


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


def build_graph(source: SourceRecord, trace: TraceRecord | Mapping[str, Any] | None = None) -> OntologyGraph:
    tree = ast.parse(source.source_code)
    extractor = _Extractor(source, tree, trace)
    return extractor.build()


class _Extractor:
    def __init__(self, source: SourceRecord, tree: ast.Module, trace: TraceRecord | Mapping[str, Any] | None = None):
        self.source = source
        self.tree = tree
        self.trace = _trace_mapping(trace)
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
        self.trace_snapshots_by_target = _trace_snapshots_by_target(self.trace)
        self.trace_effects_by_target = _trace_effects_by_target(self.trace)
        self.trace_selectors_by_line_text_kind = _trace_selectors_by_line_text_kind(self.trace)
        self.trace_selectors_by_line_text = _trace_selectors_by_line_text(self.trace)
        self.trace_selectors_by_line = _trace_selectors_by_line(self.trace)
        self.trace_effect_use_counts: dict[tuple[str, int | None], int] = {}
        self.trace_selector_use_counts: dict[int, int] = {}

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
        if record.operation in {"faces", "edges", "vertices"}:
            self._extract_selector(record)

    def _add_feature(self, target: str, record: OperationRecord) -> None:
        input_feature_ids = self._input_feature_ids(record)
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
        for input_id in input_feature_ids:
            self.graph.add_relation(Relation(input_id, feature_id, "input_to"))
        self._attach_trace_snapshot_state(feature_id, target, record)
        self._attach_trace_feature_effect(feature_id, target, record)
        if record.operation in {"extrude", "cutBlind", "cutThruAll", "sweep"}:
            profile_id = self.variable_profiles.get(str(record.base))
            if profile_id:
                self.graph.add_relation(Relation(feature_id, profile_id, "uses_profile"))
                self.graph.add_relation(Relation(profile_id, feature_id, "used_by"))
                self._attach_profile_application_effect(feature_id, profile_id, record)
                if not self._add_kernel_region_projection(feature_id, profile_id, target, record):
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
            point_vectors = [_coerce_point3(point) for point in points]
            if all(point is not None for point in point_vectors):
                coerced_points = [point for point in point_vectors if point is not None]
                self._add_path_points(path_id, record, coerced_points)
                self._add_path_segments(path_id, record, coerced_points)

    def _add_path_points(self, path_id: str, record: OperationRecord, points: list[list[float]]) -> None:
        for index, point in enumerate(points):
            point_id = f"{path_id}:point:{index}"
            self.graph.add_node(
                Node(
                    id=point_id,
                    type="path_point",
                    label=f"{record.target} point {index}",
                    source_ref=str(record.source_line),
                    properties={"path_id": path_id, "index": index, "coordinate": point},
                )
            )
            self.graph.add_relation(Relation(point_id, path_id, "point_on_path", evidence={"source_line": record.source_line}))
            distance = math.sqrt(sum(component * component for component in point))
            self.graph.add_measurement(Measurement(point_id, "entity_geometry", "coordinate", point, "mm", {"path_id": path_id}))
            self.graph.add_measurement(Measurement(point_id, "entity_geometry", "coordinate_x", point[0], "mm", {"path_id": path_id}))
            self.graph.add_measurement(Measurement(point_id, "entity_geometry", "coordinate_y", point[1], "mm", {"path_id": path_id}))
            self.graph.add_measurement(Measurement(point_id, "entity_geometry", "coordinate_z", point[2], "mm", {"path_id": path_id}))
            self.graph.add_measurement(Measurement(point_id, "relation_metric", "distance_to_origin", distance, "mm", {"path_id": path_id}))
            self.graph.add_measurement(Measurement(point_id, "snapshot_state", "path_point_index", index, None, {"path_id": path_id}))

    def _add_path_segments(self, path_id: str, record: OperationRecord, points: list[list[float]]) -> None:
        for index, (start, end) in enumerate(zip(points, points[1:], strict=False)):
            segment_id = f"{path_id}:segment:{index}"
            vector = [end[axis] - start[axis] for axis in range(3)]
            midpoint = [(start[axis] + end[axis]) / 2.0 for axis in range(3)]
            length = math.sqrt(sum(component * component for component in vector))
            self.graph.add_node(
                Node(
                    id=segment_id,
                    type="path_segment",
                    label=f"{record.target} segment {index}",
                    source_ref=str(record.source_line),
                    properties={
                        "path_id": path_id,
                        "index": index,
                        "start": start,
                        "end": end,
                        "vector": vector,
                        "midpoint": midpoint,
                    },
                )
            )
            self.graph.add_relation(Relation(segment_id, path_id, "segment_on_path", evidence={"source_line": record.source_line}))
            self.graph.add_measurement(Measurement(segment_id, "entity_geometry", "segment_vector", vector, "mm", {"path_id": path_id}))
            self.graph.add_measurement(Measurement(segment_id, "entity_geometry", "segment_midpoint", midpoint, "mm", {"path_id": path_id}))
            self.graph.add_measurement(Measurement(segment_id, "relation_metric", "segment_length", length, "mm", {"path_id": path_id}))
            self.graph.add_measurement(Measurement(segment_id, "relation_metric", "midpoint_distance_to_origin", math.sqrt(sum(component * component for component in midpoint)), "mm", {"path_id": path_id}))
            self.graph.add_measurement(Measurement(segment_id, "snapshot_state", "path_segment_index", index, None, {"path_id": path_id}))

    def _extract_selector(self, record: OperationRecord) -> None:
        selector_text = str(record.args[0]) if record.args else ""
        selector_label = _selector_label(record.operation, selector_text)
        selector_kind = record.operation
        kernel_result = self._trace_selector_result(record, selector_text)
        if kernel_result is not None:
            selector_kind = str(kernel_result.get("selector_kind") or selector_kind)
        selector_slug = _slug(selector_text) if selector_text else f"{_slug(record.target)}_{record.operation}_all"
        selector_id = self._unique_node_id(f"selector:{selector_slug}")
        self.graph.add_node(
            Node(
                id=selector_id,
                type="selector",
                label=selector_label,
                source_ref=str(record.source_line),
                properties={
                    "selector": record.args[0] if record.args else None,
                    "selector_label": selector_label,
                    "selector_kind": selector_kind,
                    "kernel_backed": kernel_result is not None,
                    "selected_count": kernel_result.get("selected_count") if kernel_result else None,
                },
            )
        )
        self.graph.add_relation(Relation(selector_id, record.id, "selected_by"))
        self.graph.add_measurement(
            Measurement(selector_id, "snapshot_state", "source_line", record.source_line, evidence={"operation_id": record.id})
        )
        self.graph.add_measurement(
            Measurement(selector_id, "snapshot_state", "operation_index", len(self.operations) - 1, evidence={"operation_id": record.id})
        )
        if kernel_result is not None:
            self.graph.add_measurement(
                Measurement(
                    selector_id,
                    "snapshot_state",
                    "selected_count",
                    int(kernel_result.get("selected_count") or 0),
                    evidence={"source": kernel_result.get("evidence", "cadquery_selector_result")},
                )
            )
            self._add_kernel_selected_faces(selector_id, selector_text, kernel_result, record)
            self.selector_ids_by_text.setdefault(selector_text, []).append(selector_id)
            return
        if selector_kind in {"edges", "vertices"}:
            self.selector_ids_by_text.setdefault(selector_text, []).append(selector_id)
            return
        face_id = f"face:{_slug(selector_text)}"
        self.graph.add_node(
            Node(
                id=face_id,
                type="face",
                label=f"face selected by {selector_label}",
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

    def _add_kernel_selected_faces(
        self,
        selector_id: str,
        selector_text: str,
        kernel_result: dict[str, Any],
        record: OperationRecord,
    ) -> None:
        selector_kind = str(kernel_result.get("selector_kind") or record.operation)
        if selector_kind != "faces":
            self._add_kernel_selected_entities(selector_id, selector_text, kernel_result, record, selector_kind)
            return
        bbox_signatures = kernel_result.get("bbox_signatures") or []
        shape_types = kernel_result.get("shape_types") or []
        selected_count = int(kernel_result.get("selected_count") or 0)
        previous_selector_ids = self.selector_ids_by_text.get(selector_text, [])
        selected_face_ids: list[str] = []
        normal_axes: dict[str, str] = {}
        for index in range(selected_count):
            bbox = bbox_signatures[index] if index < len(bbox_signatures) else None
            shape_type = shape_types[index] if index < len(shape_types) else "unknown"
            signature = _kernel_face_signature(selector_text, bbox, shape_type, index)
            face_id = f"face:kernel:{signature}"
            normal_axis = _bbox_flat_axis(bbox)
            self.graph.add_node(
                Node(
                    id=face_id,
                    type="face",
                    label=f"kernel face {index} selected by {_selector_label(record.operation, selector_text)}",
                    source_ref=str(record.source_line),
                    properties={
                        "stable_selector": selector_text,
                        "kernel_backed": True,
                        "selector_index": index,
                        "shape_type": shape_type,
                        "bbox": bbox,
                        "normal_axis": normal_axis,
                    },
                )
            )
            selected_face_ids.append(face_id)
            if normal_axis is not None:
                normal_axes[face_id] = normal_axis
            self.graph.add_relation(
                Relation(
                    face_id,
                    selector_id,
                    "selected_by",
                    evidence={"source": kernel_result.get("evidence", "cadquery_selector_result")},
                )
            )
            self.graph.add_relation(
                Relation(
                    face_id,
                    selector_id,
                    "has_kernel_stable_face_id",
                    evidence={"signature": signature},
                )
            )
            self.graph.add_relation(
                Relation(
                    selector_id,
                    face_id,
                    "has_kernel_stable_face_id",
                    evidence={"signature": signature},
                )
            )
            if isinstance(bbox, dict):
                self.graph.add_measurement(
                    Measurement(face_id, "entity_geometry", "bbox", bbox, evidence={"source": "cadquery_selector_result"})
                )
                for name, value in _bbox_scalar_measurements("bbox", bbox).items():
                    self.graph.add_measurement(
                        Measurement(face_id, "entity_geometry", name, value, evidence={"source": "cadquery_selector_result"})
                    )
            if normal_axis is not None:
                self.graph.add_measurement(
                    Measurement(face_id, "entity_geometry", "normal_axis", normal_axis, evidence={"source": "cadquery_selector_result"})
                )
        self._add_kernel_face_center_metrics(selected_face_ids, kernel_result)
        self._add_kernel_face_spatial_relations(selected_face_ids, normal_axes, kernel_result)
        for previous_selector_id in previous_selector_ids:
            self.graph.add_relation(
                Relation(
                    selector_id,
                    previous_selector_id,
                    "same_selected_face_as",
                    evidence={"source": kernel_result.get("evidence", "cadquery_selector_result")},
                )
            )
            self.graph.add_relation(
                Relation(
                    previous_selector_id,
                    selector_id,
                    "same_selected_face_as",
                    evidence={"source": kernel_result.get("evidence", "cadquery_selector_result")},
                )
            )

    def _add_kernel_face_center_metrics(self, face_ids: list[str], kernel_result: dict[str, Any]) -> None:
        evidence = {"source": kernel_result.get("evidence", "cadquery_selector_result")}
        self._ensure_global_origin(evidence)
        for face_id in face_ids:
            face = self.graph.node(face_id)
            if face is None or self.graph.measurements_for(face_id, "face_center"):
                continue
            center = _bbox_midpoint(face.properties.get("bbox"))
            if center is None:
                continue
            distance_to_origin = math.sqrt(sum(component * component for component in center))
            self.graph.add_relation(Relation(face_id, "origin:global", "distance_to", evidence=evidence))
            self.graph.add_measurement(Measurement(face_id, "entity_geometry", "face_center", center, "mm", evidence))
            self.graph.add_measurement(Measurement(face_id, "entity_geometry", "coordinate_x", center[0], "mm", evidence))
            self.graph.add_measurement(Measurement(face_id, "entity_geometry", "coordinate_y", center[1], "mm", evidence))
            self.graph.add_measurement(Measurement(face_id, "entity_geometry", "coordinate_z", center[2], "mm", evidence))
            self.graph.add_measurement(Measurement(face_id, "relation_metric", "distance_to_origin", distance_to_origin, "mm", evidence))
            face_area = _bbox_face_area(face.properties.get("bbox"))
            if face_area is not None:
                self.graph.add_measurement(Measurement(face_id, "entity_geometry", "face_area", face_area, "mm^2", evidence))

    def _add_kernel_face_spatial_relations(
        self,
        face_ids: list[str],
        normal_axes: dict[str, str],
        kernel_result: dict[str, Any],
    ) -> None:
        evidence = {"source": kernel_result.get("evidence", "cadquery_selector_result")}
        bboxes = {
            face_id: face.properties.get("bbox")
            for face_id in face_ids
            if (face := self.graph.node(face_id)) is not None
        }
        for source_id in face_ids:
            source_axis = normal_axes.get(source_id)
            if source_axis is None:
                continue
            for target_id in face_ids:
                if source_id == target_id:
                    continue
                target_axis = normal_axes.get(target_id)
                if target_axis is None:
                    continue
                if source_axis == target_axis:
                    self.graph.add_relation(Relation(source_id, target_id, "parallel_to", evidence=evidence))
                    if _face_bboxes_opposite(bboxes.get(source_id), bboxes.get(target_id), source_axis):
                        self.graph.add_relation(Relation(source_id, target_id, "opposite_to", evidence=evidence))
                    continue
                self.graph.add_relation(Relation(source_id, target_id, "perpendicular_to", evidence=evidence))
                if _bboxes_touch_or_overlap(bboxes.get(source_id), bboxes.get(target_id)):
                    self.graph.add_relation(Relation(source_id, target_id, "adjacent_to", evidence=evidence))
                    self.graph.add_relation(Relation(source_id, target_id, "intersects", evidence=evidence))

    def _add_kernel_selected_entities(
        self,
        selector_id: str,
        selector_text: str,
        kernel_result: dict[str, Any],
        record: OperationRecord,
        selector_kind: str,
    ) -> None:
        entity_type = {"edges": "edge", "vertices": "vertex"}.get(selector_kind)
        if entity_type is None:
            return
        bbox_signatures = kernel_result.get("bbox_signatures") or []
        shape_types = kernel_result.get("shape_types") or []
        selected_count = int(kernel_result.get("selected_count") or 0)
        relation_type = f"has_kernel_stable_{entity_type}_id"
        previous_selector_ids = self.selector_ids_by_text.get(selector_text, [])
        selected_entity_ids: list[str] = []
        selected_axes: dict[str, str] = {}
        for index in range(selected_count):
            bbox = bbox_signatures[index] if index < len(bbox_signatures) else None
            shape_type = shape_types[index] if index < len(shape_types) else "unknown"
            signature = _kernel_entity_signature(entity_type, selector_text, bbox, shape_type, index)
            entity_id = f"{entity_type}:kernel:{signature}"
            axis = _bbox_dominant_axis(bbox) if entity_type == "edge" else None
            self.graph.add_node(
                Node(
                    id=entity_id,
                    type=entity_type,
                    label=f"kernel {entity_type} {index} selected by {_selector_label(record.operation, selector_text)}",
                    source_ref=str(record.source_line),
                    properties={
                        "stable_selector": selector_text,
                        "kernel_backed": True,
                        "selector_index": index,
                        "shape_type": shape_type,
                        "bbox": bbox,
                        "dominant_axis": axis,
                    },
                )
            )
            selected_entity_ids.append(entity_id)
            if axis is not None:
                selected_axes[entity_id] = axis
            self.graph.add_relation(
                Relation(
                    entity_id,
                    selector_id,
                    "selected_by",
                    evidence={"source": kernel_result.get("evidence", "cadquery_selector_result")},
                )
            )
            self.graph.add_relation(
                Relation(
                    entity_id,
                    selector_id,
                    relation_type,
                    evidence={"signature": signature},
                )
            )
            self.graph.add_relation(
                Relation(
                    selector_id,
                    entity_id,
                    relation_type,
                    evidence={"signature": signature},
                )
            )
            if isinstance(bbox, dict):
                self.graph.add_measurement(
                    Measurement(entity_id, "entity_geometry", "bbox", bbox, evidence={"source": "cadquery_selector_result"})
                )
                for name, value in _bbox_scalar_measurements("bbox", bbox).items():
                    self.graph.add_measurement(
                        Measurement(entity_id, "entity_geometry", name, value, evidence={"source": "cadquery_selector_result"})
                    )
            if axis is not None:
                self.graph.add_measurement(
                    Measurement(entity_id, "entity_geometry", "dominant_axis", axis, evidence={"source": "cadquery_selector_result"})
                )
        if entity_type == "edge":
            self._add_kernel_edge_midpoint_metrics(selected_entity_ids, kernel_result)
            self._add_kernel_edge_endpoints(selected_entity_ids, kernel_result)
            self._add_kernel_edge_spatial_relations(selected_entity_ids, selected_axes, kernel_result)
        elif entity_type == "vertex":
            self._add_kernel_vertex_coordinate_metrics(selected_entity_ids, kernel_result)
        for previous_selector_id in previous_selector_ids:
            self.graph.add_relation(
                Relation(
                    selector_id,
                    previous_selector_id,
                    "same_selected_entity_as",
                    evidence={"source": kernel_result.get("evidence", "cadquery_selector_result")},
                )
            )
            self.graph.add_relation(
                Relation(
                    previous_selector_id,
                    selector_id,
                    "same_selected_entity_as",
                    evidence={"source": kernel_result.get("evidence", "cadquery_selector_result")},
                )
            )

    def _add_kernel_edge_spatial_relations(
        self,
        edge_ids: list[str],
        axes: dict[str, str],
        kernel_result: dict[str, Any],
    ) -> None:
        evidence = {"source": kernel_result.get("evidence", "cadquery_selector_result")}
        endpoints_by_edge = {
            edge_id: endpoints
            for edge_id in edge_ids
            if (endpoints := _bbox_edge_endpoints(self.graph.node(edge_id).properties.get("bbox") if self.graph.node(edge_id) else None)) is not None
        }
        lengths_by_edge = {
            edge_id: _point_distance(endpoints[0], endpoints[1])
            for edge_id, endpoints in endpoints_by_edge.items()
        }
        for source_id in edge_ids:
            source_axis = axes.get(source_id)
            if source_axis is None:
                continue
            for target_id in edge_ids:
                if source_id == target_id:
                    continue
                target_axis = axes.get(target_id)
                if target_axis is None:
                    continue
                relation_type = "parallel_to" if source_axis == target_axis else "perpendicular_to"
                self.graph.add_relation(Relation(source_id, target_id, relation_type, evidence=evidence))
                if (
                    source_axis == target_axis
                    and not _edge_endpoints_touch(endpoints_by_edge.get(source_id), endpoints_by_edge.get(target_id))
                    and _edge_lengths_equal(endpoints_by_edge.get(source_id), endpoints_by_edge.get(target_id))
                ):
                    self.graph.add_relation(Relation(source_id, target_id, "opposite_to", evidence=evidence))
                if _edge_endpoints_touch(endpoints_by_edge.get(source_id), endpoints_by_edge.get(target_id)):
                    self.graph.add_relation(Relation(source_id, target_id, "adjacent_to", evidence=evidence))
                    self.graph.add_relation(Relation(source_id, target_id, "intersects", evidence=evidence))
                source_length = lengths_by_edge.get(source_id)
                target_length = lengths_by_edge.get(target_id)
                if source_length is None or target_length is None:
                    continue
                if abs(source_length - target_length) <= 1e-6:
                    self.graph.add_relation(Relation(source_id, target_id, "same_length_as", evidence=evidence))
                elif source_length > target_length + 1e-6:
                    self.graph.add_relation(Relation(source_id, target_id, "longer_than", evidence=evidence))
                else:
                    self.graph.add_relation(Relation(source_id, target_id, "shorter_than", evidence=evidence))

    def _add_kernel_edge_midpoint_metrics(self, edge_ids: list[str], kernel_result: dict[str, Any]) -> None:
        evidence = {"source": kernel_result.get("evidence", "cadquery_selector_result")}
        self._ensure_global_origin(evidence)
        for edge_id in edge_ids:
            edge = self.graph.node(edge_id)
            if edge is None or self.graph.measurements_for(edge_id, "midpoint"):
                continue
            midpoint = _bbox_midpoint(edge.properties.get("bbox"))
            endpoints = _bbox_edge_endpoints(edge.properties.get("bbox"))
            if midpoint is None or endpoints is None:
                continue
            edge_length = _point_distance(endpoints[0], endpoints[1])
            distance_to_origin = math.sqrt(sum(component * component for component in midpoint))
            self.graph.add_relation(Relation(edge_id, "origin:global", "distance_to", evidence=evidence))
            self.graph.add_measurement(Measurement(edge_id, "entity_geometry", "midpoint", midpoint, "mm", evidence))
            self.graph.add_measurement(Measurement(edge_id, "entity_geometry", "midpoint_x", midpoint[0], "mm", evidence))
            self.graph.add_measurement(Measurement(edge_id, "entity_geometry", "midpoint_y", midpoint[1], "mm", evidence))
            self.graph.add_measurement(Measurement(edge_id, "entity_geometry", "midpoint_z", midpoint[2], "mm", evidence))
            self.graph.add_measurement(Measurement(edge_id, "relation_metric", "edge_length", edge_length, "mm", evidence))
            self.graph.add_measurement(Measurement(edge_id, "relation_metric", "midpoint_distance_to_origin", distance_to_origin, "mm", evidence))

    def _add_kernel_edge_endpoints(self, edge_ids: list[str], kernel_result: dict[str, Any]) -> None:
        evidence = {"source": kernel_result.get("evidence", "cadquery_selector_result")}
        self._ensure_global_origin(evidence)
        for edge_id in edge_ids:
            edge = self.graph.node(edge_id)
            if edge is None:
                continue
            endpoints = _bbox_edge_endpoints(edge.properties.get("bbox"))
            if endpoints is None:
                continue
            for endpoint in endpoints:
                endpoint_id = f"edge_endpoint:kernel:{_point_signature(endpoint)}"
                self.graph.add_node(
                    Node(
                        id=endpoint_id,
                        type="edge_endpoint",
                        label=f"kernel edge endpoint {_rounded_signature_value(endpoint)}",
                        source_ref=edge.source_ref,
                        properties={
                            "coordinate": endpoint,
                            "kernel_backed": True,
                        },
                    )
                )
                self.graph.add_relation(Relation(endpoint_id, edge_id, "endpoint_of", evidence=evidence))
                self.graph.add_relation(Relation(endpoint_id, edge_id, "contained_in", evidence=evidence))
                self.graph.add_relation(Relation(endpoint_id, "origin:global", "distance_to", evidence=evidence))
                self.graph.add_relation(Relation(edge_id, endpoint_id, "has_endpoint", evidence=evidence))
                if not self.graph.measurements_for(endpoint_id, "coordinate"):
                    distance_to_origin = math.sqrt(sum(component * component for component in endpoint))
                    self.graph.add_measurement(Measurement(endpoint_id, "entity_geometry", "coordinate", endpoint, "mm", evidence))
                    self.graph.add_measurement(Measurement(endpoint_id, "entity_geometry", "coordinate_x", endpoint[0], "mm", evidence))
                    self.graph.add_measurement(Measurement(endpoint_id, "entity_geometry", "coordinate_y", endpoint[1], "mm", evidence))
                    self.graph.add_measurement(Measurement(endpoint_id, "entity_geometry", "coordinate_z", endpoint[2], "mm", evidence))
                    self.graph.add_measurement(Measurement(endpoint_id, "relation_metric", "distance_to_origin", distance_to_origin, "mm", evidence))

    def _add_kernel_vertex_coordinate_metrics(self, vertex_ids: list[str], kernel_result: dict[str, Any]) -> None:
        evidence = {"source": kernel_result.get("evidence", "cadquery_selector_result")}
        self._ensure_global_origin(evidence)
        for vertex_id in vertex_ids:
            vertex = self.graph.node(vertex_id)
            if vertex is None or self.graph.measurements_for(vertex_id, "coordinate"):
                continue
            coordinate = _bbox_midpoint(vertex.properties.get("bbox"))
            if coordinate is None:
                continue
            distance_to_origin = math.sqrt(sum(component * component for component in coordinate))
            self.graph.add_relation(Relation(vertex_id, "origin:global", "distance_to", evidence=evidence))
            self.graph.add_measurement(Measurement(vertex_id, "entity_geometry", "coordinate", coordinate, "mm", evidence))
            self.graph.add_measurement(Measurement(vertex_id, "entity_geometry", "coordinate_x", coordinate[0], "mm", evidence))
            self.graph.add_measurement(Measurement(vertex_id, "entity_geometry", "coordinate_y", coordinate[1], "mm", evidence))
            self.graph.add_measurement(Measurement(vertex_id, "entity_geometry", "coordinate_z", coordinate[2], "mm", evidence))
            self.graph.add_measurement(Measurement(vertex_id, "relation_metric", "distance_to_origin", distance_to_origin, "mm", evidence))

    def _ensure_global_origin(self, evidence: dict[str, Any]) -> None:
        self.graph.add_node(
            Node(
                id="origin:global",
                type="origin",
                label="global origin",
                properties={"coordinate": [0.0, 0.0, 0.0]},
            )
        )
        if not self.graph.measurements_for("origin:global", "coordinate"):
            self.graph.add_measurement(Measurement("origin:global", "entity_geometry", "coordinate", [0.0, 0.0, 0.0], "mm", evidence))

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

    def _attach_trace_snapshot_state(self, feature_id: str, target: str, record: OperationRecord) -> None:
        snapshot = self._trace_snapshot_for_target(target, record)
        if snapshot is None:
            return
        for name in ["volume", "bbox", "topology", "shape_type", "operation_index"]:
            if name not in snapshot:
                continue
            self.graph.add_measurement(
                Measurement(
                    feature_id,
                    "snapshot_state",
                    name,
                    snapshot[name],
                    evidence={
                        "source": "cadquery_trace_snapshot",
                        "target": target,
                        "source_line": snapshot.get("source_line"),
                    },
                )
            )
        for name, value in _scalar_geometry_measurements(snapshot).items():
            self.graph.add_measurement(
                Measurement(
                    feature_id,
                    "snapshot_state",
                    name,
                    value,
                    evidence={
                        "source": "cadquery_trace_snapshot",
                        "target": target,
                        "source_line": snapshot.get("source_line"),
                    },
                )
            )

    def _attach_trace_feature_effect(self, feature_id: str, target: str, record: OperationRecord) -> None:
        effect = self._trace_effect_for_target(target, record, consume=False)
        if effect is None:
            return
        for name in ["signed_volume_delta", "bbox_delta", "topology_delta", "effect_index"]:
            if name not in effect:
                continue
            self.graph.add_measurement(
                Measurement(
                    feature_id,
                    "feature_application_effect",
                    name,
                    effect[name],
                    evidence={
                        "source": effect.get("evidence", "cadquery_assignment_snapshot_delta"),
                        "from_target": effect.get("from_target"),
                        "to_target": effect.get("to_target"),
                        "source_line": effect.get("source_line"),
                    },
                )
            )
        for name, value in _scalar_effect_measurements(effect).items():
            self.graph.add_measurement(
                Measurement(
                    feature_id,
                    "feature_application_effect",
                    name,
                    value,
                    evidence={
                        "source": effect.get("evidence", "cadquery_assignment_snapshot_delta"),
                        "from_target": effect.get("from_target"),
                        "to_target": effect.get("to_target"),
                        "source_line": effect.get("source_line"),
                    },
                )
            )

    def _add_kernel_region_projection(
        self,
        feature_id: str,
        profile_id: str,
        target: str,
        record: OperationRecord,
    ) -> bool:
        region_measurement = self._kernel_region_measurement(target, record)
        if region_measurement is None:
            return False
        signed_delta = region_measurement["signed_volume_delta"]
        region_type = "void_region" if signed_delta < 0 else "material_region"
        region_id = self._unique_node_id(f"{region_type}:{record.target}")
        evidence_source = region_measurement["evidence"]
        self.graph.add_node(
            Node(
                id=region_id,
                type=region_type,
                label=f"{record.target} kernel-measured {region_type}",
                source_ref=str(record.source_line),
                properties={
                    "conservative": False,
                    "operation": record.operation,
                    "trace_evidence": evidence_source,
                },
            )
        )
        relation = "removes_material_from" if region_type == "void_region" else "adds_material_to"
        geometry_relation = (
            "has_kernel_void_region_geometry"
            if region_type == "void_region"
            else "has_kernel_material_region_geometry"
        )
        self.graph.add_relation(Relation(feature_id, region_id, relation))
        self.graph.add_relation(Relation(region_id, profile_id, "created_by"))
        self.graph.add_relation(
            Relation(
                region_id,
                region_id,
                geometry_relation,
                evidence={"source": evidence_source},
            )
        )
        evidence = {
            "source": evidence_source,
            "profile_id": profile_id,
            "from_target": region_measurement.get("from_target"),
            "to_target": region_measurement.get("to_target"),
        }
        self.graph.add_measurement(Measurement(region_id, "entity_geometry", "volume", abs(float(signed_delta)), "mm^3", evidence))
        self.graph.add_measurement(Measurement(region_id, "feature_application_effect", "signed_volume_delta", float(signed_delta), "mm^3", evidence))
        if region_measurement.get("bbox") is not None:
            self.graph.add_measurement(Measurement(region_id, "entity_geometry", "bbox", region_measurement["bbox"], None, evidence))
        if region_measurement.get("bbox_delta") is not None:
            self.graph.add_measurement(Measurement(region_id, "entity_geometry", "bbox_delta", region_measurement["bbox_delta"], None, evidence))
        if region_measurement.get("topology") is not None:
            self.graph.add_measurement(Measurement(region_id, "snapshot_state", "topology", region_measurement["topology"], None, evidence))
        if region_measurement.get("topology_delta") is not None:
            self.graph.add_measurement(Measurement(region_id, "snapshot_state", "topology_delta", region_measurement["topology_delta"], None, evidence))
        for name, value in region_measurement.get("scalar_entity_geometry", {}).items():
            self.graph.add_measurement(Measurement(region_id, "entity_geometry", name, value, None, evidence))
        for name, value in region_measurement.get("scalar_feature_effect", {}).items():
            self.graph.add_measurement(Measurement(region_id, "feature_application_effect", name, value, None, evidence))
        centroid_measurements = self.graph.measurements_for(profile_id, "world_centroid")
        centroid = centroid_measurements[0].value if centroid_measurements else None
        if isinstance(centroid, list):
            self.graph.add_measurement(Measurement(region_id, "entity_geometry", "centroid", centroid, "mm", {"profile_id": profile_id}))
            if len(centroid) >= 3:
                self.graph.add_measurement(Measurement(region_id, "entity_geometry", "centroid_z", centroid[2], "mm", {"profile_id": profile_id}))
        self.graph.add_measurement(Measurement(region_id, "snapshot_state", "source_line", region_measurement.get("source_line") or record.source_line, None, evidence))
        self.graph.add_measurement(Measurement(region_id, "snapshot_state", "operation_index", len(self.operations) - 1, None, evidence))
        return True

    def _kernel_region_measurement(self, target: str, record: OperationRecord) -> dict[str, Any] | None:
        is_cut = record.operation.startswith("cut")
        is_additive = record.operation in {"extrude", "sweep"}
        effect = self._trace_effect_for_target(target, record)
        if effect is not None:
            signed_delta = effect.get("signed_volume_delta")
            if isinstance(signed_delta, (int, float)) and math.isfinite(float(signed_delta)):
                if (is_cut and signed_delta < 0) or (is_additive and signed_delta > 0):
                    return {
                        "signed_volume_delta": float(signed_delta),
                        "bbox_delta": effect.get("bbox_delta"),
                        "topology_delta": effect.get("topology_delta"),
                        "scalar_feature_effect": _scalar_effect_measurements(effect),
                        "evidence": effect.get("evidence", "cadquery_assignment_snapshot_delta"),
                        "from_target": effect.get("from_target"),
                        "to_target": effect.get("to_target"),
                        "source_line": effect.get("source_line"),
                    }
        if not is_additive:
            return None
        snapshot = self._trace_snapshot_for_target(target, record)
        if snapshot is None:
            return None
        volume = snapshot.get("volume")
        if not isinstance(volume, (int, float)) or not math.isfinite(float(volume)) or volume <= 0:
            return None
        return {
            "signed_volume_delta": float(volume),
            "bbox": snapshot.get("bbox"),
            "topology": snapshot.get("topology"),
            "scalar_entity_geometry": _scalar_geometry_measurements(snapshot),
            "evidence": "cadquery_trace_snapshot",
            "from_target": None,
            "to_target": target,
            "source_line": snapshot.get("source_line"),
        }

    def _add_region_projection(self, feature_id: str, profile_id: str, record: OperationRecord) -> None:
        profile = self.graph.node(profile_id)
        if profile is None:
            return
        region_type = "void_region" if record.operation.startswith("cut") else "material_region"
        region_id = self._unique_node_id(f"{region_type}:{record.target}")
        distance = _first_number(record.args) or 0.0
        area = float(profile.properties.get("area") or 0.0)
        volume = area * abs(distance)
        projection = self._region_projection_geometry(profile_id, distance)
        centroid_measurements = self.graph.measurements_for(profile_id, "world_centroid")
        centroid = projection.get("centroid") or (centroid_measurements[0].value if centroid_measurements else [0.0, 0.0, 0.0])
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
        for name, value in projection.items():
            if name == "centroid":
                continue
            self.graph.add_measurement(
                Measurement(
                    region_id,
                    "entity_geometry",
                    name,
                    value,
                    "mm" if name not in {"extrusion_axis"} else None,
                    {"profile_id": profile_id, "evidence": "profile_prism_projection"},
                )
            )
        if isinstance(centroid, list) and len(centroid) >= 3:
            self.graph.add_measurement(Measurement(region_id, "entity_geometry", "centroid_z", centroid[2], "mm", {"profile_id": profile_id}))
        self.graph.add_measurement(Measurement(region_id, "snapshot_state", "source_line", record.source_line, None, {"profile_id": profile_id}))
        self.graph.add_measurement(Measurement(region_id, "snapshot_state", "operation_index", len(self.operations) - 1, None, {"profile_id": profile_id}))

    def _region_projection_geometry(self, profile_id: str, distance: float) -> dict[str, Any]:
        profile = self.graph.node(profile_id)
        workplane = self._profile_workplane(profile_id)
        if profile is None or workplane is None:
            return {}
        local_bbox = profile.properties.get("local_bbox")
        if not isinstance(local_bbox, dict):
            return {}
        minimum = local_bbox.get("min")
        maximum = local_bbox.get("max")
        if not isinstance(minimum, list) or not isinstance(maximum, list) or len(minimum) < 2 or len(maximum) < 2:
            return {}
        normal = workplane.properties.get("normal")
        if not isinstance(normal, list) or len(normal) != 3:
            return {}
        profile_corners = [
            project_local_point(workplane.properties, [float(x), float(y)])
            for x in (minimum[0], maximum[0])
            for y in (minimum[1], maximum[1])
        ]
        extrusion = [float(distance) * float(component) for component in normal]
        end_corners = [
            [corner[index] + extrusion[index] for index in range(3)]
            for corner in profile_corners
        ]
        all_corners = [*profile_corners, *end_corners]
        bbox = {
            "min": [min(corner[index] for corner in all_corners) for index in range(3)],
            "max": [max(corner[index] for corner in all_corners) for index in range(3)],
        }
        start_centroid_measurements = self.graph.measurements_for(profile_id, "world_centroid")
        if start_centroid_measurements:
            start_centroid = start_centroid_measurements[0].value
        else:
            start_centroid = project_local_point(
                workplane.properties,
                [(float(minimum[0]) + float(maximum[0])) / 2.0, (float(minimum[1]) + float(maximum[1])) / 2.0],
            )
        if not isinstance(start_centroid, list) or len(start_centroid) != 3:
            return {"bbox": bbox, "extrusion_axis": normal, "height": abs(float(distance))}
        end_centroid = [float(start_centroid[index]) + extrusion[index] for index in range(3)]
        centroid = [(float(start_centroid[index]) + end_centroid[index]) / 2.0 for index in range(3)]
        return {
            "bbox": bbox,
            "extrusion_axis": normal,
            "height": abs(float(distance)),
            "start_centroid": start_centroid,
            "end_centroid": end_centroid,
            "centroid": centroid,
        }

    def _profile_workplane(self, profile_id: str) -> Node | None:
        for relation in self.graph.relations:
            if relation.source_id == profile_id and relation.type == "located_on":
                node = self.graph.node(relation.target_id)
                if node and node.type == "workplane":
                    return node
        return None

    def _trace_snapshot_for_target(self, target: str, record: OperationRecord) -> dict[str, Any] | None:
        snapshots = self.trace_snapshots_by_target.get(target, [])
        return _best_trace_item(snapshots, record)

    def _trace_effect_for_target(self, target: str, record: OperationRecord, *, consume: bool = True) -> dict[str, Any] | None:
        effects = self.trace_effects_by_target.get(target, [])
        line_matches = [
            effect
            for effect in effects
            if effect.get("source_line") == record.source_line
        ]
        if line_matches:
            key = (target, record.source_line)
            index = self.trace_effect_use_counts.get(key, 0)
            if consume:
                self.trace_effect_use_counts[key] = index + 1
            return line_matches[min(index, len(line_matches) - 1)]
        return _best_trace_item(effects, record)

    def _trace_selector_result(self, record: OperationRecord, selector_text: str) -> dict[str, Any] | None:
        exact_kind = self.trace_selectors_by_line_text_kind.get((record.source_line, selector_text, record.operation))
        if exact_kind is not None:
            return exact_kind
        exact = self.trace_selectors_by_line_text.get((record.source_line, selector_text))
        if exact is not None and exact.get("selector_kind") in (None, record.operation):
            return exact
        line_matches = self.trace_selectors_by_line.get(record.source_line, [])
        if not line_matches:
            return None
        index = self.trace_selector_use_counts.get(record.source_line, 0)
        self.trace_selector_use_counts[record.source_line] = index + 1
        return line_matches[min(index, len(line_matches) - 1)]

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
        if isinstance(record.base, str) and record.base in self.variable_features:
            ids.append(self.variable_features[record.base])
        for arg in record.args:
            if isinstance(arg, str) and arg in self.variable_features:
                ids.append(self.variable_features[arg])
        return list(dict.fromkeys(ids))


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


def _coerce_point3(value: Any) -> list[float] | None:
    if not isinstance(value, (list, tuple)) or len(value) < 2:
        return None
    try:
        x = float(value[0])
        y = float(value[1])
        z = float(value[2]) if len(value) > 2 else 0.0
    except Exception:
        return None
    if not all(math.isfinite(component) for component in [x, y, z]):
        return None
    return [x, y, z]


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


def _selector_label(operation: str, selector_text: str) -> str:
    if selector_text:
        return selector_text
    return f".{operation}()"


def _trace_mapping(trace: TraceRecord | Mapping[str, Any] | None) -> dict[str, Any] | None:
    if trace is None:
        return None
    if isinstance(trace, TraceRecord):
        return {
            "source_id": trace.source_id,
            "execution_status": trace.execution_status,
            "snapshots": trace.snapshots or [],
            "operation_effects": trace.operation_effects or [],
            "selector_results": trace.selector_results or [],
            "environment": trace.environment or {},
            "failure_reason": trace.failure_reason,
        }
    return dict(trace)


def _trace_snapshots_by_target(trace: dict[str, Any] | None) -> dict[str, list[dict[str, Any]]]:
    if not trace or trace.get("execution_status") != "ok":
        return {}
    grouped: dict[str, list[dict[str, Any]]] = {}
    operation_nodes = _trace_operation_nodes_by_feature_id(trace)
    for snapshot in trace.get("snapshots") or []:
        if not isinstance(snapshot, dict):
            continue
        snapshot = _normalized_trace_snapshot(snapshot, operation_nodes)
        target = snapshot.get("target")
        if isinstance(target, str):
            grouped.setdefault(target, []).append(snapshot)
    return grouped


def _trace_effects_by_target(trace: dict[str, Any] | None) -> dict[str, list[dict[str, Any]]]:
    if not trace or trace.get("execution_status") != "ok":
        return {}
    grouped: dict[str, list[dict[str, Any]]] = {}
    for index, effect in enumerate(trace.get("operation_effects") or []):
        if not isinstance(effect, dict):
            continue
        target = effect.get("to_target")
        if isinstance(target, str):
            grouped.setdefault(target, []).append({"effect_index": index, **effect})
    return grouped


def _trace_selectors_by_line_text(trace: dict[str, Any] | None) -> dict[tuple[int, str], dict[str, Any]]:
    if not trace or trace.get("execution_status") != "ok":
        return {}
    grouped: dict[tuple[int, str], dict[str, Any]] = {}
    for result in trace.get("selector_results") or []:
        if not isinstance(result, dict):
            continue
        line = result.get("source_line")
        selector_text = result.get("selector")
        if isinstance(line, int) and isinstance(selector_text, str):
            grouped[(line, selector_text)] = result
    return grouped


def _trace_selectors_by_line_text_kind(trace: dict[str, Any] | None) -> dict[tuple[int, str, str], dict[str, Any]]:
    if not trace or trace.get("execution_status") != "ok":
        return {}
    grouped: dict[tuple[int, str, str], dict[str, Any]] = {}
    for result in trace.get("selector_results") or []:
        if not isinstance(result, dict):
            continue
        line = result.get("source_line")
        selector_text = result.get("selector")
        selector_kind = result.get("selector_kind")
        if isinstance(line, int) and isinstance(selector_text, str) and isinstance(selector_kind, str):
            grouped[(line, selector_text, selector_kind)] = result
    return grouped


def _trace_selectors_by_line(trace: dict[str, Any] | None) -> dict[int, list[dict[str, Any]]]:
    if not trace or trace.get("execution_status") != "ok":
        return {}
    grouped: dict[int, list[dict[str, Any]]] = {}
    for result in trace.get("selector_results") or []:
        if not isinstance(result, dict):
            continue
        line = result.get("source_line")
        if isinstance(line, int):
            grouped.setdefault(line, []).append(result)
    for items in grouped.values():
        items.sort(key=lambda item: int(item.get("selector_index") or 0))
    return grouped


def _trace_operation_nodes_by_feature_id(trace: dict[str, Any]) -> dict[str, dict[str, Any]]:
    operations: dict[str, dict[str, Any]] = {}
    for item in trace.get("operation_nodes") or []:
        if not isinstance(item, dict):
            continue
        feature_id = item.get("feature_id")
        target = item.get("target")
        if isinstance(feature_id, str):
            operations[feature_id] = item
        if isinstance(target, str):
            operations[target] = item
    return operations


def _normalized_trace_snapshot(
    snapshot: dict[str, Any],
    operation_nodes: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    normalized = dict(snapshot)
    feature_id = normalized.get("feature_id")
    target = normalized.get("target")
    if not isinstance(target, str) and isinstance(feature_id, str):
        normalized["target"] = feature_id
        target = feature_id
    operation = operation_nodes.get(str(target)) if isinstance(target, str) else None
    if operation is None and isinstance(feature_id, str):
        operation = operation_nodes.get(feature_id)
    if operation is not None:
        if normalized.get("source_line") is None and isinstance(operation.get("source_line"), int):
            normalized["source_line"] = operation["source_line"]
        if normalized.get("operation_index") is None and isinstance(operation.get("step_index"), int):
            normalized["operation_index"] = operation["step_index"]
    elif normalized.get("operation_index") is None and isinstance(normalized.get("step_index"), int):
        normalized["operation_index"] = normalized["step_index"]
    return normalized


def _best_trace_item(items: list[dict[str, Any]], record: OperationRecord) -> dict[str, Any] | None:
    if not items:
        return None
    line_matches = [
        item
        for item in items
        if item.get("source_line") in (None, record.source_line)
    ]
    if line_matches:
        return line_matches[0]
    if len(items) == 1:
        return items[0]
    return None


def _scalar_geometry_measurements(snapshot: dict[str, Any]) -> dict[str, float]:
    values: dict[str, float] = {}
    centroid = snapshot.get("centroid")
    if isinstance(centroid, list):
        values.update(_vector_scalar_measurements("centroid", centroid))
    topology = snapshot.get("topology")
    if isinstance(topology, dict):
        for key, value in topology.items():
            if isinstance(value, (int, float)) and math.isfinite(float(value)):
                values[f"topology_{key}"] = float(value)
                if key.endswith("_count"):
                    values[f"topology_{key.removesuffix('_count')}s"] = float(value)
    bbox = snapshot.get("bbox")
    if isinstance(bbox, dict):
        values.update(_bbox_scalar_measurements("bbox", bbox))
    return values


def _scalar_effect_measurements(effect: dict[str, Any]) -> dict[str, float]:
    values: dict[str, float] = {}
    signed_volume_delta = effect.get("signed_volume_delta")
    if isinstance(signed_volume_delta, (int, float)) and math.isfinite(float(signed_volume_delta)):
        values["volume_delta_magnitude"] = abs(float(signed_volume_delta))
    centroid_delta = effect.get("centroid_delta")
    if isinstance(centroid_delta, list):
        values.update(_vector_scalar_measurements("centroid_delta", centroid_delta))
        magnitude = _vector_magnitude(centroid_delta)
        if magnitude is not None:
            values["centroid_delta_magnitude"] = magnitude
    topology_delta = effect.get("topology_delta")
    if isinstance(topology_delta, dict):
        for key, value in topology_delta.items():
            if isinstance(value, (int, float)) and math.isfinite(float(value)):
                values[f"topology_delta_{key}"] = float(value)
    bbox_delta = effect.get("bbox_delta")
    if isinstance(bbox_delta, dict):
        values.update(_bbox_scalar_measurements("bbox_delta", bbox_delta))
    return values


def _vector_magnitude(vector: list[Any]) -> float | None:
    numeric = [
        float(value)
        for value in vector[:3]
        if isinstance(value, (int, float)) and math.isfinite(float(value))
    ]
    if len(numeric) != min(3, len(vector)):
        return None
    return math.sqrt(sum(value * value for value in numeric))


def _vector_scalar_measurements(prefix: str, vector: list[Any]) -> dict[str, float]:
    values: dict[str, float] = {}
    axis_names = ("x", "y", "z")
    for index, axis in enumerate(axis_names):
        if index >= len(vector):
            break
        value = vector[index]
        if isinstance(value, (int, float)) and math.isfinite(float(value)):
            values[f"{prefix}_{axis}"] = float(value)
    return values


def _bbox_scalar_measurements(prefix: str, bbox: dict[str, Any]) -> dict[str, float]:
    values: dict[str, float] = {}
    minimum = bbox.get("min")
    maximum = bbox.get("max")
    if not (
        isinstance(minimum, list)
        and isinstance(maximum, list)
        and len(minimum) >= 3
        and len(maximum) >= 3
    ):
        return values
    axis_names = ("x", "y", "z")
    spans: list[float] = []
    for index, axis in enumerate(axis_names):
        lo = minimum[index]
        hi = maximum[index]
        if isinstance(lo, (int, float)) and math.isfinite(float(lo)):
            values[f"{prefix}_min_{axis}"] = float(lo)
        if isinstance(hi, (int, float)) and math.isfinite(float(hi)):
            values[f"{prefix}_max_{axis}"] = float(hi)
        if (
            isinstance(lo, (int, float))
            and isinstance(hi, (int, float))
            and math.isfinite(float(lo))
            and math.isfinite(float(hi))
        ):
            span = abs(float(hi) - float(lo))
            values[f"{prefix}_span_{axis}"] = span
            values[f"{prefix}_center_{axis}"] = (float(lo) + float(hi)) / 2.0
            spans.append(span)
    if spans:
        values[f"{prefix}_max_span"] = max(spans)
    return values


def _bbox_dominant_axis(bbox: Any) -> str | None:
    if not isinstance(bbox, dict):
        return None
    spans = _bbox_scalar_measurements("bbox", bbox)
    axis_spans = {
        axis: float(spans[f"bbox_span_{axis}"])
        for axis in ("x", "y", "z")
        if isinstance(spans.get(f"bbox_span_{axis}"), (int, float))
    }
    if len(axis_spans) != 3:
        return None
    positive = [
        (axis, span)
        for axis, span in axis_spans.items()
        if span > 1e-6
    ]
    if len(positive) != 1:
        return None
    return positive[0][0]


def _bbox_flat_axis(bbox: Any) -> str | None:
    if not isinstance(bbox, dict):
        return None
    spans = _bbox_scalar_measurements("bbox", bbox)
    axis_spans = {
        axis: float(spans[f"bbox_span_{axis}"])
        for axis in ("x", "y", "z")
        if isinstance(spans.get(f"bbox_span_{axis}"), (int, float))
    }
    if len(axis_spans) != 3:
        return None
    flat = [(axis, span) for axis, span in axis_spans.items() if span <= 1e-6]
    positive = [(axis, span) for axis, span in axis_spans.items() if span > 1e-6]
    if len(flat) != 1 or len(positive) != 2:
        return None
    return flat[0][0]


def _bbox_face_area(bbox: Any) -> float | None:
    if not isinstance(bbox, dict):
        return None
    spans = _bbox_scalar_measurements("bbox", bbox)
    axis_spans = [
        float(spans[f"bbox_span_{axis}"])
        for axis in ("x", "y", "z")
        if isinstance(spans.get(f"bbox_span_{axis}"), (int, float))
    ]
    if len(axis_spans) != 3:
        return None
    flat = [span for span in axis_spans if span <= 1e-6]
    positive = [span for span in axis_spans if span > 1e-6]
    if len(flat) != 1 or len(positive) != 2:
        return None
    return positive[0] * positive[1]


def _bbox_edge_endpoints(bbox: Any) -> list[list[float]] | None:
    if _bbox_dominant_axis(bbox) is None or not isinstance(bbox, dict):
        return None
    minimum = bbox.get("min")
    maximum = bbox.get("max")
    if not (
        isinstance(minimum, list)
        and isinstance(maximum, list)
        and len(minimum) >= 3
        and len(maximum) >= 3
    ):
        return None
    try:
        return [
            [float(minimum[0]), float(minimum[1]), float(minimum[2])],
            [float(maximum[0]), float(maximum[1]), float(maximum[2])],
        ]
    except Exception:
        return None


def _edge_endpoints_touch(lhs: list[list[float]] | None, rhs: list[list[float]] | None) -> bool:
    if lhs is None or rhs is None:
        return False
    return any(_points_close(left, right) for left in lhs for right in rhs)


def _edge_lengths_equal(lhs: list[list[float]] | None, rhs: list[list[float]] | None, *, epsilon: float = 1e-6) -> bool:
    if lhs is None or rhs is None or len(lhs) != 2 or len(rhs) != 2:
        return False
    return abs(_point_distance(lhs[0], lhs[1]) - _point_distance(rhs[0], rhs[1])) <= epsilon


def _face_bboxes_opposite(lhs: Any, rhs: Any, normal_axis: str, *, epsilon: float = 1e-6) -> bool:
    lhs_ranges = _bbox_ranges(lhs)
    rhs_ranges = _bbox_ranges(rhs)
    if lhs_ranges is None or rhs_ranges is None:
        return False
    axis_index = {"x": 0, "y": 1, "z": 2}[normal_axis]
    if _ranges_touch_or_overlap(lhs_ranges[axis_index], rhs_ranges[axis_index], epsilon=epsilon):
        return False
    for index in range(3):
        if index == axis_index:
            continue
        lhs_span = lhs_ranges[index][1] - lhs_ranges[index][0]
        rhs_span = rhs_ranges[index][1] - rhs_ranges[index][0]
        lhs_center = (lhs_ranges[index][0] + lhs_ranges[index][1]) / 2.0
        rhs_center = (rhs_ranges[index][0] + rhs_ranges[index][1]) / 2.0
        if abs(lhs_span - rhs_span) > epsilon or abs(lhs_center - rhs_center) > epsilon:
            return False
    return True


def _bboxes_touch_or_overlap(lhs: Any, rhs: Any, *, epsilon: float = 1e-6) -> bool:
    lhs_ranges = _bbox_ranges(lhs)
    rhs_ranges = _bbox_ranges(rhs)
    if lhs_ranges is None or rhs_ranges is None:
        return False
    return all(
        _ranges_touch_or_overlap(lhs_ranges[index], rhs_ranges[index], epsilon=epsilon)
        for index in range(3)
    )


def _bbox_midpoint(bbox: Any) -> list[float] | None:
    ranges = _bbox_ranges(bbox)
    if ranges is None:
        return None
    return [(lo + hi) / 2.0 for lo, hi in ranges]


def _bbox_ranges(bbox: Any) -> list[tuple[float, float]] | None:
    if not isinstance(bbox, dict):
        return None
    minimum = bbox.get("min")
    maximum = bbox.get("max")
    if not (
        isinstance(minimum, list)
        and isinstance(maximum, list)
        and len(minimum) >= 3
        and len(maximum) >= 3
    ):
        return None
    ranges: list[tuple[float, float]] = []
    for index in range(3):
        lo = minimum[index]
        hi = maximum[index]
        if not (
            isinstance(lo, (int, float))
            and isinstance(hi, (int, float))
            and math.isfinite(float(lo))
            and math.isfinite(float(hi))
        ):
            return None
        ranges.append((min(float(lo), float(hi)), max(float(lo), float(hi))))
    return ranges


def _ranges_touch_or_overlap(lhs: tuple[float, float], rhs: tuple[float, float], *, epsilon: float = 1e-6) -> bool:
    return lhs[0] <= rhs[1] + epsilon and rhs[0] <= lhs[1] + epsilon


def _point_distance(lhs: list[float], rhs: list[float]) -> float:
    return math.sqrt(sum((float(lhs[index]) - float(rhs[index])) ** 2 for index in range(3)))


def _points_close(lhs: list[float], rhs: list[float], *, epsilon: float = 1e-6) -> bool:
    return len(lhs) >= 3 and len(rhs) >= 3 and all(abs(float(lhs[index]) - float(rhs[index])) <= epsilon for index in range(3))


def _point_signature(point: list[float]) -> str:
    digest = hashlib.sha256(json.dumps(_rounded_signature_value(point), sort_keys=True).encode("utf-8")).hexdigest()[:16]
    return digest


def _kernel_face_signature(selector_text: str, bbox: Any, shape_type: Any, index: int) -> str:
    return _kernel_entity_signature("face", selector_text, bbox, shape_type, index)


def _kernel_entity_signature(entity_type: str, selector_text: str, bbox: Any, shape_type: Any, index: int) -> str:
    payload = {
        "entity_type": entity_type,
        "selector": selector_text,
        "shape_type": shape_type,
        "bbox": _rounded_signature_value(bbox),
        "index": index,
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:16]
    return f"{_slug(selector_text)}:{digest}"


def _rounded_signature_value(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, dict):
        return {key: _rounded_signature_value(item) for key, item in sorted(value.items())}
    if isinstance(value, list):
        return [_rounded_signature_value(item) for item in value]
    return value
