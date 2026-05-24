"""Ontology graph data structures."""

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
class OntologyGraph:
    graph_id: str
    source: dict[str, Any]
    nodes: list[Node] = field(default_factory=list)
    relations: list[Relation] = field(default_factory=list)
    measurements: list[Measurement] = field(default_factory=list)
    diagnostics: list[dict[str, Any]] = field(default_factory=list)

    def node(self, node_id: str) -> Node | None:
        return next((node for node in self.nodes if node.id == node_id), None)

    def nodes_by_type(self, node_type: str) -> list[Node]:
        return [node for node in self.nodes if node.type == node_type]

    def add_node(self, node: Node) -> None:
        if self.node(node.id) is None:
            self.nodes.append(node)

    def add_relation(self, relation: Relation) -> None:
        if relation in self.relations:
            return
        self.relations.append(relation)

    def add_measurement(self, measurement: Measurement) -> None:
        if measurement in self.measurements:
            return
        self.measurements.append(measurement)

    def measurements_for(self, entity_id: str, name: str | None = None) -> list[Measurement]:
        return [
            measurement
            for measurement in self.measurements
            if measurement.entity_id == entity_id
            and (name is None or measurement.name == name)
        ]


def graph_from_dict(data: dict[str, Any]) -> OntologyGraph:
    return OntologyGraph(
        graph_id=data["graph_id"],
        source=data["source"],
        nodes=[Node(**node) for node in data.get("nodes", [])],
        relations=[Relation(**relation) for relation in data.get("relations", [])],
        measurements=[Measurement(**measurement) for measurement in data.get("measurements", [])],
        diagnostics=data.get("diagnostics", []),
    )
