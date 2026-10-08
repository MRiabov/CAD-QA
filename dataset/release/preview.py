"""Markdown previews for generated CAD-QA rows and graph nodes."""

from __future__ import annotations

from collections import defaultdict
import hashlib
import json
from pathlib import Path
import random
from typing import Any

from dataset.release.sft import is_geometry_critical_row, is_syntax_only_calibration_row, prompt_family
from dataset.ontology.nodes import OntologyGraph
from dataset.query.family_manifest import DEFAULT_FAMILY_MANIFEST, load_family_manifest

DEFAULT_PREVIEW_EVIDENCE_FILENAME = "preview_evidence.json"


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
                "aggregation_rank": query.get("aggregation_rank"),
                "tie_break_aggregation": query.get("tie_break_aggregation"),
                "tie_break_metric": query.get("tie_break_metric"),
                "sampled_parameters": query.get("sampled_parameters", {}),
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


def dataset_preview_evidence_report(
    rows: list[dict[str, Any]],
    *,
    preview_path: Path | None = None,
    sample_per_family: int = 1,
    families: list[str] | None = None,
    seed: int = 0,
    family_manifest: Path | None = DEFAULT_FAMILY_MANIFEST,
) -> dict[str, Any]:
    """Machine-readable evidence that preview samples covered generated families."""

    rng = random.Random(seed)
    selected_families = set(families or [])
    grouped_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped_rows[prompt_family(row)].append(row)
    rendered_families = sorted(family for family in grouped_rows if not selected_families or family in selected_families)
    family_reports = []
    for family in rendered_families:
        family_rows = grouped_rows[family]
        sampled_rows = _sample(family_rows, sample_per_family, rng)
        family_reports.append(
            {
                "prompt_family": family,
                "row_count": len(family_rows),
                "sampled_count": len(sampled_rows),
                "sampled_row_ids": [row.get("row_id") for row in sampled_rows],
            }
        )
    manifest = load_family_manifest(family_manifest)
    return {
        "schema_version": 1,
        "preview_path": str(preview_path) if preview_path is not None else None,
        "dataset_fingerprint": dataset_fingerprint(rows),
        "row_count": len(rows),
        "sample_per_family": sample_per_family,
        "seed": seed,
        "selected_families": sorted(selected_families),
        "family_manifest_path": manifest["path"],
        "family_manifest_exists": manifest["exists"],
        "families": family_reports,
    }


def preview_evidence_gate_report(
    rows: list[dict[str, Any]],
    *,
    evidence: dict[str, Any] | None,
    family_manifest: Path | None = DEFAULT_FAMILY_MANIFEST,
    min_samples_per_family: int | None = None,
    enforce: bool = False,
) -> dict[str, Any]:
    """Validate preview evidence for generated release families."""

    manifest = load_family_manifest(family_manifest)
    release_families = {
        family_id
        for family_id, spec in manifest["families"].items()
        if spec.get("status") == "release"
    }
    generated_counts = defaultdict(int)
    for row in rows:
        family = prompt_family(row)
        if release_families and family not in release_families:
            continue
        generated_counts[family] += 1

    evidence_families = {}
    if evidence:
        evidence_families = {
            str(item.get("prompt_family")): item
            for item in evidence.get("families", [])
            if isinstance(item, dict) and item.get("prompt_family")
        }
    expected_fingerprint = dataset_fingerprint(rows)
    actual_fingerprint = evidence.get("dataset_fingerprint") if evidence else None
    violations = []
    if evidence is None:
        violations.append({"reason": "missing_preview_evidence"})
    elif actual_fingerprint != expected_fingerprint:
        violations.append(
            {
                "reason": "dataset_fingerprint_mismatch",
                "expected": expected_fingerprint,
                "actual": actual_fingerprint,
            }
        )
    family_reports = []
    for family, row_count in sorted(generated_counts.items()):
        required = min(min_samples_per_family or 0, row_count)
        item = evidence_families.get(family, {})
        sampled_count = int(item.get("sampled_count") or 0)
        passed = sampled_count >= required
        family_report = {
            "prompt_family": family,
            "row_count": row_count,
            "required_sample_count": required,
            "sampled_count": sampled_count,
            "sampled_row_ids": item.get("sampled_row_ids") or [],
            "valid": passed,
        }
        family_reports.append(family_report)
        if not passed:
            violations.append(
                {
                    "reason": "insufficient_family_preview_samples",
                    "prompt_family": family,
                    "required_sample_count": required,
                    "sampled_count": sampled_count,
                }
            )
    valid = True
    if enforce:
        valid = manifest["exists"] and not violations
    return {
        "valid": valid,
        "enforced": enforce,
        "manifest_path": manifest["path"],
        "manifest_exists": manifest["exists"],
        "expected_dataset_fingerprint": expected_fingerprint,
        "evidence_dataset_fingerprint": actual_fingerprint,
        "minimum_samples_per_family": min_samples_per_family,
        "generated_release_family_count": len(generated_counts),
        "violations": violations,
        "families": family_reports,
    }


def dataset_fingerprint(rows: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for row in sorted(rows, key=lambda item: str(item.get("row_id"))):
        query = row.get("query_program") or {}
        payload = {
            "row_id": row.get("row_id"),
            "prompt_hash": hashlib.sha256(str(row.get("prompt", "")).encode("utf-8")).hexdigest(),
            "query_id": query.get("query_id") if isinstance(query, dict) else None,
            "gold_answer": row.get("gold_answer"),
        }
        digest.update(json.dumps(payload, sort_keys=True, default=str).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()
