"""CAD graph data structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Node:
    id: str
    type: str
    label: str
    source_ref: str | None = None
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Relation:
    source_id: str
    target_id: str
    type: str
    properties: dict[str, Any] = field(default_factory=dict)
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Measurement:
    entity_id: str
    scope: str
    name: str
    value: Any
    unit: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class CadGraph:
    graph_id: str
    source: dict[str, Any]
    nodes: list[Node] = field(default_factory=list)
    relations: list[Relation] = field(default_factory=list)
    measurements: list[Measurement] = field(default_factory=list)
    diagnostics: list[dict[str, Any]] = field(default_factory=list)

    def node(self, node_id: str) -> Node | None:
        return self._node_index().get(node_id)

    def nodes_by_type(self, node_type: str) -> list[Node]:
        return list(self._nodes_by_type_index().get(node_type, []))

    def add_node(self, node: Node) -> None:
        node_index = self._node_index()
        if node.id in node_index:
            return
        self.nodes.append(node)
        node_index[node.id] = node
        nodes_by_type = getattr(self, "_cached_nodes_by_type_index", None)
        if nodes_by_type is not None:
            nodes_by_type.setdefault(node.type, []).append(node)

    def add_relation(self, relation: Relation) -> None:
        relation_key_index = self._relation_key_index()
        relation_key = _relation_key(relation)
        if relation_key in relation_key_index:
            return
        self.relations.append(relation)
        relation_key_index.add(relation_key)
        relation_index = getattr(self, "_cached_relation_index", None)
        if relation_index is not None:
            relation_index.setdefault((relation.source_id, relation.type), []).append(relation)
        relations_by_source = getattr(self, "_cached_relations_by_source_index", None)
        if relations_by_source is not None:
            relations_by_source.setdefault(relation.source_id, []).append(relation)

    def add_measurement(self, measurement: Measurement) -> None:
        measurement_key_index = self._measurement_key_index()
        measurement_key = _measurement_key(measurement)
        if measurement_key in measurement_key_index:
            return
        self.measurements.append(measurement)
        measurement_key_index.add(measurement_key)
        measurement_index = getattr(self, "_cached_measurement_index", None)
        if measurement_index is not None:
            measurement_index.setdefault((measurement.entity_id, measurement.name), []).append(measurement)
        measurements_by_entity = getattr(self, "_cached_measurements_by_entity_index", None)
        if measurements_by_entity is not None:
            measurements_by_entity.setdefault(measurement.entity_id, []).append(measurement)

    def measurements_for(self, entity_id: str, name: str | None = None) -> list[Measurement]:
        if name is None:
            return list(self._measurements_by_entity_index().get(entity_id, []))
        return list(self._measurement_index().get((entity_id, name), []))

    def relations_from(self, source_id: str, relation_type: str | None = None) -> list[Relation]:
        if relation_type is None:
            return list(self._relations_by_source_index().get(source_id, []))
        return list(self._relation_index().get((source_id, relation_type), []))

    def _node_index(self) -> dict[str, Node]:
        index = getattr(self, "_cached_node_index", None)
        if index is None:
            index = {node.id: node for node in self.nodes}
            self._cached_node_index = index
        return index

    def _nodes_by_type_index(self) -> dict[str, list[Node]]:
        index = getattr(self, "_cached_nodes_by_type_index", None)
        if index is None:
            index = {}
            for node in self.nodes:
                index.setdefault(node.type, []).append(node)
            self._cached_nodes_by_type_index = index
        return index

    def _relation_index(self) -> dict[tuple[str, str], list[Relation]]:
        index = getattr(self, "_cached_relation_index", None)
        if index is None:
            index = {}
            for relation in self.relations:
                index.setdefault((relation.source_id, relation.type), []).append(relation)
            self._cached_relation_index = index
        return index

    def _relations_by_source_index(self) -> dict[str, list[Relation]]:
        index = getattr(self, "_cached_relations_by_source_index", None)
        if index is None:
            index = {}
            for relation in self.relations:
                index.setdefault(relation.source_id, []).append(relation)
            self._cached_relations_by_source_index = index
        return index

    def _measurement_index(self) -> dict[tuple[str, str], list[Measurement]]:
        index = getattr(self, "_cached_measurement_index", None)
        if index is None:
            index = {}
            for measurement in self.measurements:
                index.setdefault((measurement.entity_id, measurement.name), []).append(measurement)
            self._cached_measurement_index = index
        return index

    def _measurements_by_entity_index(self) -> dict[str, list[Measurement]]:
        index = getattr(self, "_cached_measurements_by_entity_index", None)
        if index is None:
            index = {}
            for measurement in self.measurements:
                index.setdefault(measurement.entity_id, []).append(measurement)
            self._cached_measurements_by_entity_index = index
        return index

    def _relation_key_index(self) -> set[tuple[Any, ...]]:
        index = getattr(self, "_cached_relation_key_index", None)
        if index is None:
            index = {_relation_key(relation) for relation in self.relations}
            self._cached_relation_key_index = index
        return index

    def _measurement_key_index(self) -> set[tuple[Any, ...]]:
        index = getattr(self, "_cached_measurement_key_index", None)
        if index is None:
            index = {_measurement_key(measurement) for measurement in self.measurements}
            self._cached_measurement_key_index = index
        return index


def _relation_key(relation: Relation) -> tuple[Any, ...]:
    return (
        relation.source_id,
        relation.target_id,
        relation.type,
        _freeze_value(relation.properties),
        _freeze_value(relation.evidence),
    )


def _measurement_key(measurement: Measurement) -> tuple[Any, ...]:
    return (
        measurement.entity_id,
        measurement.scope,
        measurement.name,
        _freeze_value(measurement.value),
        measurement.unit,
        _freeze_value(measurement.evidence),
    )


def _freeze_value(value: Any) -> Any:
    if isinstance(value, dict):
        return tuple((key, _freeze_value(value[key])) for key in sorted(value))
    if isinstance(value, list):
        return tuple(_freeze_value(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_freeze_value(item) for item in value)
    if isinstance(value, set):
        return tuple(sorted(_freeze_value(item) for item in value))
    return value

def graph_from_dict(data: dict[str, Any]) -> CadGraph:
    return CadGraph(
        graph_id=data["graph_id"],
        source=data["source"],
        nodes=[Node(**node) for node in data.get("nodes", [])],
        relations=[Relation(**relation) for relation in data.get("relations", [])],
        measurements=[Measurement(**measurement) for measurement in data.get("measurements", [])],
        diagnostics=data.get("diagnostics", []),
    )
