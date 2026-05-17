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
        self.trace_selectors_by_line_text = _trace_selectors_by_line_text(self.trace)

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

    def _extract_selector(self, record: OperationRecord) -> None:
        selector_text = str(record.args[0]) if record.args else record.target
        kernel_result = self._trace_selector_result(record, selector_text)
        selector_id = self._unique_node_id(f"selector:{_slug(selector_text)}")
        self.graph.add_node(
            Node(
                id=selector_id,
                type="selector",
                label=selector_text,
                source_ref=str(record.source_line),
                properties={
                    "selector": record.args[0] if record.args else None,
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

    def _add_kernel_selected_faces(
        self,
        selector_id: str,
        selector_text: str,
        kernel_result: dict[str, Any],
        record: OperationRecord,
    ) -> None:
        bbox_signatures = kernel_result.get("bbox_signatures") or []
        shape_types = kernel_result.get("shape_types") or []
        selected_count = int(kernel_result.get("selected_count") or 0)
        previous_selector_ids = self.selector_ids_by_text.get(selector_text, [])
        for index in range(selected_count):
            bbox = bbox_signatures[index] if index < len(bbox_signatures) else None
            shape_type = shape_types[index] if index < len(shape_types) else "unknown"
            signature = _kernel_face_signature(selector_text, bbox, shape_type, index)
            face_id = f"face:kernel:{signature}"
            self.graph.add_node(
                Node(
                    id=face_id,
                    type="face",
                    label=f"kernel face {index} selected by {selector_text}",
                    source_ref=str(record.source_line),
                    properties={
                        "stable_selector": selector_text,
                        "kernel_backed": True,
                        "selector_index": index,
                        "shape_type": shape_type,
                        "bbox": bbox,
                    },
                )
            )
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
            if isinstance(bbox, dict):
                self.graph.add_measurement(
                    Measurement(face_id, "entity_geometry", "bbox", bbox, evidence={"source": "cadquery_selector_result"})
                )
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

    def _attach_trace_feature_effect(self, feature_id: str, target: str, record: OperationRecord) -> None:
        effect = self._trace_effect_for_target(target, record)
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

    def _add_kernel_region_projection(
        self,
        feature_id: str,
        profile_id: str,
        target: str,
        record: OperationRecord,
    ) -> bool:
        effect = self._trace_effect_for_target(target, record)
        if effect is None:
            return False
        signed_delta = effect.get("signed_volume_delta")
        if not isinstance(signed_delta, (int, float)) or not math.isfinite(float(signed_delta)) or signed_delta == 0:
            return False
        region_type = "void_region" if signed_delta < 0 else "material_region"
        region_id = self._unique_node_id(f"{region_type}:{record.target}")
        self.graph.add_node(
            Node(
                id=region_id,
                type=region_type,
                label=f"{record.target} kernel-measured {region_type}",
                source_ref=str(record.source_line),
                properties={
                    "conservative": False,
                    "operation": record.operation,
                    "trace_evidence": effect.get("evidence", "cadquery_assignment_snapshot_delta"),
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
                evidence={"source": effect.get("evidence", "cadquery_assignment_snapshot_delta")},
            )
        )
        evidence = {
            "source": effect.get("evidence", "cadquery_assignment_snapshot_delta"),
            "profile_id": profile_id,
            "from_target": effect.get("from_target"),
            "to_target": effect.get("to_target"),
        }
        self.graph.add_measurement(Measurement(region_id, "entity_geometry", "volume", abs(float(signed_delta)), "mm^3", evidence))
        self.graph.add_measurement(Measurement(region_id, "feature_application_effect", "signed_volume_delta", float(signed_delta), "mm^3", evidence))
        if "bbox_delta" in effect:
            self.graph.add_measurement(Measurement(region_id, "entity_geometry", "bbox_delta", effect["bbox_delta"], None, evidence))
        if "topology_delta" in effect:
            self.graph.add_measurement(Measurement(region_id, "snapshot_state", "topology_delta", effect["topology_delta"], None, evidence))
        centroid_measurements = self.graph.measurements_for(profile_id, "world_centroid")
        centroid = centroid_measurements[0].value if centroid_measurements else None
        if isinstance(centroid, list):
            self.graph.add_measurement(Measurement(region_id, "entity_geometry", "centroid", centroid, "mm", {"profile_id": profile_id}))
            if len(centroid) >= 3:
                self.graph.add_measurement(Measurement(region_id, "entity_geometry", "centroid_z", centroid[2], "mm", {"profile_id": profile_id}))
        self.graph.add_measurement(Measurement(region_id, "snapshot_state", "source_line", record.source_line, None, evidence))
        self.graph.add_measurement(Measurement(region_id, "snapshot_state", "operation_index", len(self.operations) - 1, None, evidence))
        return True

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

    def _trace_effect_for_target(self, target: str, record: OperationRecord) -> dict[str, Any] | None:
        effects = self.trace_effects_by_target.get(target, [])
        return _best_trace_item(effects, record)

    def _trace_selector_result(self, record: OperationRecord, selector_text: str) -> dict[str, Any] | None:
        return self.trace_selectors_by_line_text.get((record.source_line, selector_text))

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


def _trace_mapping(trace: TraceRecord | Mapping[str, Any] | None) -> dict[str, Any] | None:
    if trace is None:
        return None
    if isinstance(trace, TraceRecord):
        return {
            "source_id": trace.source_id,
            "execution_status": trace.execution_status,
            "snapshots": trace.snapshots or [],
            "operation_effects": trace.operation_effects or [],
            "environment": trace.environment or {},
            "failure_reason": trace.failure_reason,
        }
    return dict(trace)


def _trace_snapshots_by_target(trace: dict[str, Any] | None) -> dict[str, list[dict[str, Any]]]:
    if not trace or trace.get("execution_status") != "ok":
        return {}
    grouped: dict[str, list[dict[str, Any]]] = {}
    for snapshot in trace.get("snapshots") or []:
        if not isinstance(snapshot, dict):
            continue
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


def _best_trace_item(items: list[dict[str, Any]], record: OperationRecord) -> dict[str, Any] | None:
    if not items:
        return None
    line_matches = [
        item
        for item in items
        if item.get("source_line") in (None, record.source_line)
    ]
    return (line_matches or items)[0]


def _kernel_face_signature(selector_text: str, bbox: Any, shape_type: Any, index: int) -> str:
    payload = {
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
