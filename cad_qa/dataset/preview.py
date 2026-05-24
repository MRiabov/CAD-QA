"""Markdown previews for generated CAD-QA rows and graph nodes."""

from __future__ import annotations

from collections import defaultdict
import json
import random
from typing import Any

from cad_qa.dataset.sft import is_geometry_critical_row, is_syntax_only_calibration_row, prompt_family
from cad_qa.ontology.nodes import OntologyGraph


def dataset_preview_markdown(
    rows: list[dict[str, Any]],
    *,
    graphs: list[OntologyGraph] | None = None,
    sample_per_family: int = 1,
    families: list[str] | None = None,
    node_types: list[str] | None = None,
    seed: int = 0,
    max_prompt_chars: int = 12000,
) -> str:
    rng = random.Random(seed)
    selected_families = set(families or [])
    selected_node_types = set(node_types or [])
    lines = [
        "# CAD-QA Generated Preview",
        "",
        f"- Row count: `{len(rows)}`",
        f"- Random seed: `{seed}`",
        f"- Samples per task family: `{sample_per_family}`",
        "",
        "## Quality Counts",
        "",
        _json_block(
            {
                "geometry_critical": sum(1 for row in rows if is_geometry_critical_row(row)),
                "syntax_only_calibration": sum(1 for row in rows if is_syntax_only_calibration_row(row)),
            }
        ),
        "",
        "## Task Families",
        "",
    ]
    grouped_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped_rows[prompt_family(row)].append(row)
    for family in sorted(grouped_rows):
        if selected_families and family not in selected_families:
            continue
        family_rows = grouped_rows[family]
        lines.extend(
            [
                f"### `{family}`",
                "",
                f"- Rows: `{len(family_rows)}`",
                "",
            ]
        )
        for index, row in enumerate(_sample(family_rows, sample_per_family, rng), 1):
            lines.extend(_row_sample_markdown(row, index=index, max_prompt_chars=max_prompt_chars))
    if graphs is not None:
        lines.extend(["", "## Node Samples", ""])
        nodes_by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
        measurements_by_entity: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for graph in graphs:
            for node in graph.nodes:
                nodes_by_type[node.type].append(
                    {
                        "graph_id": graph.graph_id,
                        "id": node.id,
                        "label": node.label,
                        "properties": node.properties,
                    }
                )
            for measurement in graph.measurements:
                measurements_by_entity[measurement.entity_id].append(
                    {
                        "scope": measurement.scope,
                        "name": measurement.name,
                        "value": measurement.value,
                        "unit": measurement.unit,
                    }
                )
        rendered_node_types = sorted(selected_node_types or nodes_by_type.keys())
        for node_type in rendered_node_types:
            nodes = nodes_by_type[node_type]
            lines.extend(
                [
                    f"### `{node_type}`",
                    "",
                    f"- Nodes: `{len(nodes)}`",
                    "",
                ]
            )
            if not nodes:
                lines.extend(["_No samples available._", ""])
                continue
            for node in _sample(nodes, sample_per_family, rng):
                payload = dict(node)
                measurements = measurements_by_entity.get(str(node["id"]), [])
                payload["measurement_count"] = len(measurements)
                if measurements:
                    payload["measurements"] = measurements[:10]
                    if len(measurements) > 10:
                        payload["omitted_measurement_names"] = [
                            str(measurement["name"])
                            for measurement in measurements[10:]
                        ]
                lines.extend(["```json", json.dumps(payload, indent=2, sort_keys=True), "```", ""])
    return "\n".join(lines).rstrip() + "\n"


def _row_sample_markdown(row: dict[str, Any], *, index: int, max_prompt_chars: int) -> list[str]:
    query = row.get("query_program", {})
    trace = row.get("candidate_trace", {})
    metadata = {
        "row_id": row.get("row_id"),
        "source_id": row.get("source_id"),
        "difficulty": row.get("difficulty_bucket"),
        "prompt_version": row.get("prompt_version"),
        "prompt_template_id": row.get("prompt_template_id"),
        "logical_hop_count": row.get("logical_hop_count"),
        "static_hop_count": row.get("static_hop_count"),
        "geometry_hop_count": row.get("geometry_hop_count"),
        "measurement_scopes": row.get("measurement_scopes", []),
        "relation_families": row.get("relation_families", []),
        "release_ready": row.get("release_ready"),
        "geometry_critical": is_geometry_critical_row(row),
        "syntax_only_calibration": is_syntax_only_calibration_row(row),
        "gold_answer": row.get("gold_answer"),
    }
    prompt = str(row.get("prompt", ""))
    if len(prompt) > max_prompt_chars:
        prompt = prompt[:max_prompt_chars].rstrip() + "\n\n[truncated]"
    return [
        f"#### Sample {index}",
        "",
        "Metadata:",
        "",
        _json_block(metadata),
        "",
        "Query program:",
        "",
        _json_block(
            {
                "query_id": query.get("query_id"),
                "target_type": query.get("target_type"),
                "clauses": query.get("clauses", []),
                "aggregation": query.get("aggregation"),
                "aggregation_metric": query.get("aggregation_metric"),
            }
        ),
        "",
        "Candidate trace:",
        "",
        _json_block(
            {
                "status": trace.get("status"),
                "failure_reason": trace.get("failure_reason"),
                "final_candidates": trace.get("final_candidates", []),
                "steps": trace.get("steps", []),
            }
        ),
        "",
        "Prompt:",
        "",
        "````text",
        prompt.rstrip(),
        "````",
        "",
    ]


def _sample(items: list[Any], count: int, rng: random.Random) -> list[Any]:
    if count <= 0:
        return []
    if len(items) <= count:
        return list(items)
    return rng.sample(items, count)


def _json_block(value: dict[str, Any]) -> str:
    return "```json\n" + json.dumps(value, indent=2, sort_keys=True) + "\n```"
