"""Dataset row materialization."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cad_qa.ontology.nodes import OntologyGraph
from cad_qa.prompts.render import render_prompt
from cad_qa.query.ir import QueryResolution
from cad_qa.query.parameters import normalize_sampled_parameters, sampled_parameters_from_query
from cad_qa.source import source_family_from_path


@dataclass(frozen=True)
class DatasetRow:
    row_id: str
    source_id: str
    source_path: str | None
    source_hash: str | None
    source_metadata: dict[str, Any]
    split_group: str
    source_code: str
    prompt: str
    answer_format: str
    gold_answer: Any
    query_program: dict[str, Any]
    candidate_trace: dict[str, Any]
    relation_families: list[str]
    measurement_scopes: list[str]
    logical_hop_count: int
    static_hop_count: int
    geometry_hop_count: int
    difficulty_bucket: str
    verifier_status: str
    prompt_version: str
    prompt_template_id: str
    clue_map: list[dict[str, Any]]
    evidence_tier: str
    release_ready: bool
    quarantine_reasons: list[str]


def materialize_row(graph: OntologyGraph, resolution: QueryResolution) -> DatasetRow:
    rendered = render_prompt(graph.source["source_code"], resolution.query_program)
    source_id = graph.source["source_id"]
    source_metadata = graph.source.get("metadata") or {}
    query = resolution.query_program
    static_hops = sum(
        1
        for clause in query.clauses
        if clause.kind in {"property_equals"} or clause.relation in {"before", "after", "input_to", "parameter_of"}
    )
    geometry_hops = max(0, query.hop_count - static_hops)
    evidence_tier, quarantine_reasons = _evidence_policy(resolution)
    return DatasetRow(
        row_id=f"row:{source_id}:{query.query_id.split(':')[-1]}",
        source_id=source_id,
        source_path=graph.source.get("source_path"),
        source_hash=graph.source.get("source_hash"),
        source_metadata=source_metadata,
        split_group=_split_group(graph.source),
        source_code=graph.source["source_code"],
        prompt=rendered.prompt,
        answer_format=query.answer_type,
        gold_answer=resolution.gold_answer,
        query_program=_query_to_dict(query, rendered),
        candidate_trace={
            "query_id": resolution.candidate_trace.query_id,
            "steps": resolution.candidate_trace.steps,
            "final_candidates": resolution.candidate_trace.final_candidates,
            "status": resolution.candidate_trace.status,
            "failure_reason": resolution.candidate_trace.failure_reason,
        },
        relation_families=resolution.relation_families,
        measurement_scopes=resolution.measurement_scopes,
        logical_hop_count=query.hop_count,
        static_hop_count=static_hops,
        geometry_hop_count=geometry_hops,
        difficulty_bucket=query.difficulty,
        verifier_status=resolution.verifier_status,
        prompt_version=rendered.prompt_version,
        prompt_template_id=rendered.prompt_template_id,
        clue_map=_clue_map_with_candidate_counts(rendered.clue_map, resolution.candidate_trace.steps),
        evidence_tier=evidence_tier,
        release_ready=not quarantine_reasons,
        quarantine_reasons=quarantine_reasons,
    )


def _query_to_dict(query: Any, rendered: Any | None = None) -> dict[str, Any]:
    mapping = {
        "query_id": query.query_id,
        "target_type": query.target_type,
        "answer_type": query.answer_type,
        "clauses": [clause.__dict__ for clause in query.clauses],
        "aggregation": query.aggregation,
        "aggregation_metric": query.aggregation_metric,
        "aggregation_rank": getattr(query, "aggregation_rank", None),
        "tie_break_aggregation": getattr(query, "tie_break_aggregation", None),
        "tie_break_metric": getattr(query, "tie_break_metric", None),
        "hop_count": query.hop_count,
        "difficulty": query.difficulty,
        "reject_unless_unique": query.reject_unless_unique,
        "min_individual_clause_candidates": query.min_individual_clause_candidates,
    }
    sampled = normalize_sampled_parameters(getattr(query, "sampled_parameters", None)) or sampled_parameters_from_query(
        mapping
    )
    if rendered is not None:
        rendered_parameters: dict[str, list[str]] = {
            "rendered_prompt_template_id": [rendered.prompt_template_id],
        }
        clue_template_ids = [
            str(clue["clue_template_id"])
            for clue in getattr(rendered, "clue_map", [])
            if isinstance(clue, dict) and clue.get("clue_template_id")
        ]
        if clue_template_ids:
            rendered_parameters["rendered_clue_template_id"] = sorted(set(clue_template_ids))
            rendered_parameters["rendered_clue_template_sequence"] = [" > ".join(clue_template_ids)]
        sampled = _merge_sampled_parameter_values(sampled, rendered_parameters)
    mapping["sampled_parameters"] = sampled
    return mapping


def _merge_sampled_parameter_values(
    base: dict[str, list[str]],
    extra: dict[str, list[str]],
) -> dict[str, list[str]]:
    merged = {
        str(dimension): [str(value) for value in values if value is not None and str(value)]
        for dimension, values in base.items()
    }
    for dimension, values in extra.items():
        current = set(merged.get(dimension, []))
        current.update(str(value) for value in values if value is not None and str(value))
        if current:
            merged[dimension] = sorted(current)
    return dict(sorted(merged.items()))


def _clue_map_with_candidate_counts(
    clue_map: list[dict[str, Any]],
    trace_steps: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    steps_by_id = {
        step.get("step"): step
        for step in trace_steps
        if isinstance(step, dict) and step.get("step")
    }
    enriched: list[dict[str, Any]] = []
    for clue in clue_map:
        item = dict(clue)
        step = steps_by_id.get(item.get("clause_id"))
        if step:
            before = step.get("before") or step.get("candidate_ids") or []
            after = step.get("after") or step.get("candidate_ids") or []
            if isinstance(before, list):
                item["candidate_count_before"] = len(before)
            if isinstance(after, list):
                item["candidate_count_after"] = len(after)
        enriched.append(item)
    return enriched


def _evidence_policy(resolution: QueryResolution) -> tuple[str, list[str]]:
    reasons: list[str] = []
    families = set(resolution.relation_families)
    query = resolution.query_program
    if families & {"has_material_region_geometry", "has_void_region_geometry"}:
        reasons.append("conservative_region_projection")
    has_kernel_selector_evidence = bool(
        families
        & {
            "has_kernel_stable_face_id",
            "has_kernel_stable_edge_id",
            "has_kernel_stable_vertex_id",
        }
    )
    has_selector_surrogate = families & {
        "selected_by",
        "same_selected_face_as",
        "same_selected_entity_as",
        "has_stable_face_id",
    }
    if (
        (query.target_type in {"face", "edge", "vertex", "selector"} and not has_kernel_selector_evidence)
        or (has_selector_surrogate and not has_kernel_selector_evidence)
    ):
        reasons.append("selector_identity_surrogate")
    if resolution.verifier_status != "resolved":
        reasons.append("unresolved_verifier")
    if not reasons:
        return "source_static_or_analytic", []
    if "unresolved_verifier" in reasons:
        return "unresolved", sorted(set(reasons))
    return "quarantine", sorted(set(reasons))


def _split_group(source: dict[str, Any]) -> str:
    metadata = source.get("metadata") or {}
    for key in ("split_group", "counterfactual_group", "source_family", "family_id", "template_id"):
        value = metadata.get(key) or source.get(key)
        if value:
            return f"{key}:{value}"
    path = source.get("source_path")
    if path:
        return f"path_family:{source_family_from_path(str(path))}"
    return f"source:{source['source_id']}"
