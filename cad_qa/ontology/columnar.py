"""Columnar side-table storage for ontology graphs.

The legacy graph artifact stores each graph as one parquet row with JSON string
payloads for nodes, relations, and measurements. These helpers write normalized
side tables that keep hot graph fields queryable with Polars/Arrow while the
legacy object artifact remains available for compatibility.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
import pickle
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from cad_qa.ontology.nodes import Measurement, Node, OntologyGraph, Relation


COLUMNAR_GRAPH_FORMAT = "cadqa_columnar_graph_v1"
COLUMNAR_GRAPH_DIR = "graph_tables"


_GRAPHS_SCHEMA = pa.schema(
    [
        pa.field("graph_id", pa.string()),
        pa.field("source_id", pa.string()),
        pa.field("source_path", pa.string()),
        pa.field("source_hash", pa.string()),
        pa.field("source_code", pa.string()),
        pa.field("source_pickle", pa.binary()),
        pa.field("source", pa.string()),
        pa.field("source_subtree", pa.string()),
        pa.field("source_collection", pa.string()),
        pa.field("path_family", pa.string()),
        pa.field("source_feature_tags", pa.list_(pa.string())),
        pa.field("generator_id", pa.string()),
        pa.field("normalized_source_code_hash", pa.string()),
        pa.field("node_count", pa.int64()),
        pa.field("relation_count", pa.int64()),
        pa.field("measurement_count", pa.int64()),
        pa.field("diagnostic_count", pa.int64()),
    ]
)

_NODES_SCHEMA = pa.schema(
    [
        pa.field("graph_id", pa.string()),
        pa.field("node_id", pa.string()),
        pa.field("node_index", pa.int64()),
        pa.field("node_type", pa.string()),
        pa.field("label", pa.string()),
        pa.field("source_ref", pa.string()),
    ]
)

_RELATIONS_SCHEMA = pa.schema(
    [
        pa.field("graph_id", pa.string()),
        pa.field("relation_id", pa.string()),
        pa.field("relation_index", pa.int64()),
        pa.field("source_id", pa.string()),
        pa.field("target_id", pa.string()),
        pa.field("relation_type", pa.string()),
    ]
)

_MEASUREMENTS_SCHEMA = pa.schema(
    [
        pa.field("graph_id", pa.string()),
        pa.field("measurement_id", pa.string()),
        pa.field("measurement_index", pa.int64()),
        pa.field("entity_id", pa.string()),
        pa.field("scope", pa.string()),
        pa.field("measurement_name", pa.string()),
        pa.field("unit", pa.string()),
        pa.field("value_kind", pa.string()),
        pa.field("value_bool", pa.bool_()),
        pa.field("value_int", pa.int64()),
        pa.field("value_float", pa.float64()),
        pa.field("value_str", pa.string()),
        pa.field("value_float_list", pa.list_(pa.float64())),
        pa.field("value_repr", pa.string()),
        pa.field("value_pickle", pa.binary()),
    ]
)

_PROPERTIES_SCHEMA = pa.schema(
    [
        pa.field("graph_id", pa.string()),
        pa.field("owner_table", pa.string()),
        pa.field("owner_id", pa.string()),
        pa.field("key", pa.string()),
        pa.field("value_kind", pa.string()),
        pa.field("value_bool", pa.bool_()),
        pa.field("value_int", pa.int64()),
        pa.field("value_float", pa.float64()),
        pa.field("value_str", pa.string()),
        pa.field("value_float_list", pa.list_(pa.float64())),
        pa.field("value_repr", pa.string()),
        pa.field("value_pickle", pa.binary()),
    ]
)

_DIAGNOSTICS_SCHEMA = pa.schema(
    [
        pa.field("graph_id", pa.string()),
        pa.field("diagnostic_index", pa.int64()),
        pa.field("key", pa.string()),
        pa.field("value_kind", pa.string()),
        pa.field("value_bool", pa.bool_()),
        pa.field("value_int", pa.int64()),
        pa.field("value_float", pa.float64()),
        pa.field("value_str", pa.string()),
        pa.field("value_float_list", pa.list_(pa.float64())),
        pa.field("value_repr", pa.string()),
        pa.field("value_pickle", pa.binary()),
    ]
)


def write_columnar_graph_store(
    out_dir: Path,
    graphs: Iterable[OntologyGraph],
    *,
    batch_size: int = 100,
) -> dict[str, Any]:
    """Write graph side tables and return a manifest dictionary."""

    writer = ColumnarGraphWriter(out_dir)
    try:
        writer.write_many(graphs, batch_size=batch_size)
    finally:
        writer.close()
    manifest = writer.manifest()
    write_columnar_graph_manifest(out_dir, manifest)
    return manifest


def write_columnar_graph_manifest(out_dir: Path, manifest: dict[str, Any]) -> None:
    import json

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_columnar_graph_store(out_dir: Path) -> list[OntologyGraph]:
    """Reconstruct ontology graphs from columnar side tables exactly."""

    graph_rows = pq.read_table(out_dir / "graphs.parquet").to_pylist()
    nodes_by_graph: dict[str, list[dict[str, Any]]] = {}
    for row in pq.read_table(out_dir / "nodes.parquet").to_pylist():
        nodes_by_graph.setdefault(row["graph_id"], []).append(row)

    relations_by_graph: dict[str, list[dict[str, Any]]] = {}
    relation_properties = _property_rows_by_owner(out_dir / "relation_properties.parquet")
    relation_evidence = _property_rows_by_owner(out_dir / "relation_evidence.parquet")
    for row in pq.read_table(out_dir / "relations.parquet").to_pylist():
        relations_by_graph.setdefault(row["graph_id"], []).append(row)

    measurements_by_graph: dict[str, list[dict[str, Any]]] = {}
    measurement_evidence = _property_rows_by_owner(out_dir / "measurement_evidence.parquet")
    for row in pq.read_table(out_dir / "measurements.parquet").to_pylist():
        measurements_by_graph.setdefault(row["graph_id"], []).append(row)

    node_properties = _property_rows_by_owner(out_dir / "node_properties.parquet")
    diagnostics_by_graph = _diagnostic_rows_by_graph(out_dir / "diagnostics.parquet")

    graphs: list[OntologyGraph] = []
    for graph_row in graph_rows:
        graph_id = graph_row["graph_id"]
        nodes = [
            Node(
                id=row["node_id"],
                type=row["node_type"],
                label=row["label"],
                source_ref=row["source_ref"],
                properties=node_properties.get((graph_id, row["node_id"]), {}),
            )
            for row in sorted(nodes_by_graph.get(graph_id, []), key=lambda item: item["node_index"])
        ]
        relations = [
            Relation(
                source_id=row["source_id"],
                target_id=row["target_id"],
                type=row["relation_type"],
                properties=relation_properties.get((graph_id, row["relation_id"]), {}),
                evidence=relation_evidence.get((graph_id, row["relation_id"]), {}),
            )
            for row in sorted(relations_by_graph.get(graph_id, []), key=lambda item: item["relation_index"])
        ]
        measurements = [
            Measurement(
                entity_id=row["entity_id"],
                scope=row["scope"],
                name=row["measurement_name"],
                value=_value_from_columns(row),
                unit=row["unit"],
                evidence=measurement_evidence.get((graph_id, row["measurement_id"]), {}),
            )
            for row in sorted(measurements_by_graph.get(graph_id, []), key=lambda item: item["measurement_index"])
        ]
        graphs.append(
            OntologyGraph(
                graph_id=graph_id,
                source=pickle.loads(graph_row["source_pickle"]),
                nodes=nodes,
                relations=relations,
                measurements=measurements,
                diagnostics=diagnostics_by_graph.get(graph_id, []),
            )
        )
    return graphs


class ColumnarGraphWriter:
    """Append ontology graphs to a normalized parquet side-table directory."""

    def __init__(self, out_dir: Path) -> None:
        self.out_dir = out_dir
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self._writers: dict[str, pq.ParquetWriter] = {}
        self._counts = {
            "graphs": 0,
            "nodes": 0,
            "relations": 0,
            "measurements": 0,
            "node_properties": 0,
            "relation_properties": 0,
            "relation_evidence": 0,
            "measurement_evidence": 0,
            "diagnostics": 0,
        }

    def write_many(self, graphs: Iterable[OntologyGraph], *, batch_size: int = 100) -> None:
        batch: list[OntologyGraph] = []
        for graph in graphs:
            batch.append(graph)
            if len(batch) >= batch_size:
                self.write_batch(batch)
                batch = []
        if batch:
            self.write_batch(batch)

    def write_batch(self, graphs: list[OntologyGraph]) -> None:
        rows = _columnar_rows(graphs)
        self._write_table("graphs", rows["graphs"], _GRAPHS_SCHEMA)
        self._write_table("nodes", rows["nodes"], _NODES_SCHEMA)
        self._write_table("relations", rows["relations"], _RELATIONS_SCHEMA)
        self._write_table("measurements", rows["measurements"], _MEASUREMENTS_SCHEMA)
        self._write_table("node_properties", rows["node_properties"], _PROPERTIES_SCHEMA)
        self._write_table("relation_properties", rows["relation_properties"], _PROPERTIES_SCHEMA)
        self._write_table("relation_evidence", rows["relation_evidence"], _PROPERTIES_SCHEMA)
        self._write_table("measurement_evidence", rows["measurement_evidence"], _PROPERTIES_SCHEMA)
        self._write_table("diagnostics", rows["diagnostics"], _DIAGNOSTICS_SCHEMA)

    def close(self) -> None:
        for writer in self._writers.values():
            writer.close()
        self._writers.clear()

    def manifest(self) -> dict[str, Any]:
        files = {
            name: f"{name}.parquet"
            for name in [
                "graphs",
                "nodes",
                "relations",
                "measurements",
                "node_properties",
                "relation_properties",
                "relation_evidence",
                "measurement_evidence",
                "diagnostics",
            ]
        }
        return {
            "format": COLUMNAR_GRAPH_FORMAT,
            "files": files,
            "counts": dict(self._counts),
        }

    def _write_table(self, name: str, rows: list[dict[str, Any]], schema: pa.Schema) -> None:
        table = pa.Table.from_pylist(rows, schema=schema)
        writer = self._writers.get(name)
        if writer is None:
            path = self.out_dir / f"{name}.parquet"
            writer = pq.ParquetWriter(path, schema, compression="zstd")
            self._writers[name] = writer
        writer.write_table(table)
        self._counts[name] += len(rows)


def _columnar_rows(graphs: list[OntologyGraph]) -> dict[str, list[dict[str, Any]]]:
    rows: dict[str, list[dict[str, Any]]] = {
        "graphs": [],
        "nodes": [],
        "relations": [],
        "measurements": [],
        "node_properties": [],
        "relation_properties": [],
        "relation_evidence": [],
        "measurement_evidence": [],
        "diagnostics": [],
    }
    for graph in graphs:
        rows["graphs"].append(_graph_row(graph))
        for index, node in enumerate(graph.nodes):
            rows["nodes"].append(_node_row(graph.graph_id, index, node))
            rows["node_properties"].extend(_property_rows(graph.graph_id, "nodes", node.id, node.properties))
        for index, relation in enumerate(graph.relations):
            relation_id = _relation_id(graph.graph_id, index)
            rows["relations"].append(_relation_row(graph.graph_id, relation_id, index, relation))
            rows["relation_properties"].extend(_property_rows(graph.graph_id, "relations", relation_id, relation.properties))
            rows["relation_evidence"].extend(_property_rows(graph.graph_id, "relations", relation_id, relation.evidence))
        for index, measurement in enumerate(graph.measurements):
            measurement_id = _measurement_id(graph.graph_id, index)
            rows["measurements"].append(_measurement_row(graph.graph_id, measurement_id, index, measurement))
            rows["measurement_evidence"].extend(
                _property_rows(graph.graph_id, "measurements", measurement_id, measurement.evidence)
            )
        for index, diagnostic in enumerate(graph.diagnostics):
            rows["diagnostics"].extend(_diagnostic_rows(graph.graph_id, index, diagnostic))
    return rows


def _graph_row(graph: OntologyGraph) -> dict[str, Any]:
    source = graph.source
    metadata = source.get("metadata") if isinstance(source.get("metadata"), dict) else {}
    return {
        "graph_id": graph.graph_id,
        "source_id": _string_or_none(source.get("source_id")),
        "source_path": _string_or_none(source.get("source_path")),
        "source_hash": _string_or_none(source.get("source_hash")),
        "source_code": _string_or_none(source.get("source_code")),
        "source_pickle": _pickle_value(source),
        "source": _string_or_none(metadata.get("source")),
        "source_subtree": _string_or_none(metadata.get("source_subtree")),
        "source_collection": _string_or_none(metadata.get("source_collection")),
        "path_family": _string_or_none(metadata.get("path_family")),
        "source_feature_tags": _string_list_or_empty(metadata.get("source_feature_tags")),
        "generator_id": _string_or_none(metadata.get("generator_id")),
        "normalized_source_code_hash": _string_or_none(metadata.get("normalized_source_code_hash")),
        "node_count": len(graph.nodes),
        "relation_count": len(graph.relations),
        "measurement_count": len(graph.measurements),
        "diagnostic_count": len(graph.diagnostics),
    }


def _node_row(graph_id: str, index: int, node: Node) -> dict[str, Any]:
    return {
        "graph_id": graph_id,
        "node_id": node.id,
        "node_index": index,
        "node_type": node.type,
        "label": node.label,
        "source_ref": node.source_ref,
    }


def _relation_row(graph_id: str, relation_id: str, index: int, relation: Relation) -> dict[str, Any]:
    return {
        "graph_id": graph_id,
        "relation_id": relation_id,
        "relation_index": index,
        "source_id": relation.source_id,
        "target_id": relation.target_id,
        "relation_type": relation.type,
    }


def _measurement_row(graph_id: str, measurement_id: str, index: int, measurement: Measurement) -> dict[str, Any]:
    return {
        "graph_id": graph_id,
        "measurement_id": measurement_id,
        "measurement_index": index,
        "entity_id": measurement.entity_id,
        "scope": measurement.scope,
        "measurement_name": measurement.name,
        "unit": measurement.unit,
        **_value_columns(measurement.value),
    }


def _property_rows(graph_id: str, owner_table: str, owner_id: str, values: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "graph_id": graph_id,
            "owner_table": owner_table,
            "owner_id": owner_id,
            "key": str(key),
            **_value_columns(value),
        }
        for key, value in sorted(values.items())
    ]


def _diagnostic_rows(graph_id: str, index: int, diagnostic: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "graph_id": graph_id,
            "diagnostic_index": index,
            "key": str(key),
            **_value_columns(value),
        }
        for key, value in sorted(diagnostic.items())
    ]


def _value_columns(value: Any) -> dict[str, Any]:
    value_kind = _value_kind(value)
    return {
        "value_kind": value_kind,
        "value_bool": value if isinstance(value, bool) else None,
        "value_int": value if isinstance(value, int) and not isinstance(value, bool) else None,
        "value_float": float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None,
        "value_str": value if isinstance(value, str) else None,
        "value_float_list": _float_list_or_none(value),
        "value_repr": None if value is None or isinstance(value, (bool, int, float, str)) else repr(value),
        "value_pickle": _pickle_value(value),
    }


def _value_kind(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    if _float_list_or_none(value) is not None:
        return "float_list"
    return type(value).__name__


def _float_list_or_none(value: Any) -> list[float] | None:
    if not isinstance(value, (list, tuple)):
        return None
    result: list[float] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            return None
        result.append(float(item))
    return result


def _relation_id(graph_id: str, index: int) -> str:
    return f"{graph_id}:rel:{index:08d}"


def _measurement_id(graph_id: str, index: int) -> str:
    return f"{graph_id}:measurement:{index:08d}"


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _string_list_or_empty(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _property_rows_by_owner(path: Path) -> dict[tuple[str, str], dict[str, Any]]:
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for row in pq.read_table(path).to_pylist():
        result.setdefault((row["graph_id"], row["owner_id"]), {})[row["key"]] = _value_from_columns(row)
    return result


def _diagnostic_rows_by_graph(path: Path) -> dict[str, list[dict[str, Any]]]:
    values: dict[tuple[str, int], dict[str, Any]] = {}
    for row in pq.read_table(path).to_pylist():
        key = (row["graph_id"], row["diagnostic_index"])
        values.setdefault(key, {})[row["key"]] = _value_from_columns(row)
    result: dict[str, list[dict[str, Any]]] = {}
    for (graph_id, _index), diagnostic in sorted(values.items()):
        result.setdefault(graph_id, []).append(diagnostic)
    return result


def _value_from_columns(row: dict[str, Any]) -> Any:
    payload = row.get("value_pickle")
    if payload is not None:
        return pickle.loads(payload)
    value_kind = row.get("value_kind")
    if value_kind == "null":
        return None
    if value_kind == "bool":
        return row.get("value_bool")
    if value_kind == "int":
        return row.get("value_int")
    if value_kind == "float":
        return row.get("value_float")
    if value_kind == "str":
        return row.get("value_str")
    if value_kind == "float_list":
        return row.get("value_float_list")
    return row.get("value_repr")


def _pickle_value(value: Any) -> bytes:
    return pickle.dumps(value, protocol=5)
