"""Dataset reporting helpers."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import Any


def dataset_report(rows: list[Any]) -> dict[str, Any]:
    hop_counts: Counter[str] = Counter()
    difficulty_buckets: Counter[str] = Counter()
    relation_families: Counter[str] = Counter()
    measurement_scopes: Counter[str] = Counter()
    verifier_statuses: Counter[str] = Counter()
    answer_formats: Counter[str] = Counter()
    split_counts: Counter[str] = Counter()
    evidence_tiers: Counter[str] = Counter()
    quarantine_reasons: Counter[str] = Counter()
    release_ready: Counter[str] = Counter()
    for row in rows:
        item = row if isinstance(row, dict) else row.__dict__
        hop_counts[str(item["logical_hop_count"])] += 1
        difficulty_buckets[item["difficulty_bucket"]] += 1
        verifier_statuses[item["verifier_status"]] += 1
        answer_formats[item["answer_format"]] += 1
        if "split" in item:
            split_counts[item["split"]] += 1
        evidence_tiers[item.get("evidence_tier", "unknown")] += 1
        release_ready[str(bool(item.get("release_ready", False))).lower()] += 1
        quarantine_reasons.update(item.get("quarantine_reasons", []))
        relation_families.update(item.get("relation_families", []))
        measurement_scopes.update(item.get("measurement_scopes", []))
    return {
        "row_count": len(rows),
        "hop_counts": dict(sorted(hop_counts.items())),
        "difficulty_buckets": dict(sorted(difficulty_buckets.items())),
        "relation_families": dict(sorted(relation_families.items())),
        "measurement_scopes": dict(sorted(measurement_scopes.items())),
        "verifier_statuses": dict(sorted(verifier_statuses.items())),
        "answer_formats": dict(sorted(answer_formats.items())),
        "split_counts": dict(sorted(split_counts.items())),
        "evidence_tiers": dict(sorted(evidence_tiers.items())),
        "release_ready": dict(sorted(release_ready.items())),
        "quarantine_reasons": dict(sorted(quarantine_reasons.items())),
    }


def failure_report(failures: list[dict[str, Any]]) -> dict[str, Any]:
    reasons: Counter[str] = Counter()
    graphs: Counter[str] = Counter()
    examples: list[dict[str, Any]] = []
    for failure in failures:
        trace = failure.get("candidate_trace", {})
        trace_reason = trace.get("failure_reason") if isinstance(trace, dict) else getattr(trace, "failure_reason", None)
        final_candidates = trace.get("final_candidates", []) if isinstance(trace, dict) else getattr(trace, "final_candidates", [])
        reason = failure.get("reason") or trace_reason or "unknown"
        graph_id = failure.get("graph_id", "unknown")
        reasons[reason] += 1
        graphs[graph_id] += 1
        if len(examples) < 10:
            examples.append(
                {
                    "graph_id": graph_id,
                    "query_id": failure.get("query_id"),
                    "reason": reason,
                    "final_candidates": final_candidates,
                }
            )
    return {
        "failure_count": len(failures),
        "reasons": dict(sorted(reasons.items())),
        "graphs_with_failures": dict(sorted(graphs.items())),
        "examples": examples,
    }


def dataset_card_markdown(
    *,
    dataset_path: Path,
    report: dict[str, Any],
    validation: dict[str, Any] | None = None,
    audit: dict[str, Any] | None = None,
    failures: dict[str, Any] | None = None,
) -> str:
    lines = [
        "# CAD-QA Graph Dataset Card",
        "",
        f"Dataset path: `{dataset_path}`",
        "",
        "## Framing",
        "",
        "Rows are public prompts rendered from hidden deterministic CAD ontology query programs. Low-hop rows and high-hop BrowseComp-style rows share the same graph extraction, resolver, verifier, and materialization path.",
        "",
        "## Composition",
        "",
        _json_block(
            {
                "row_count": report.get("row_count", 0),
                "hop_counts": report.get("hop_counts", {}),
                "difficulty_buckets": report.get("difficulty_buckets", {}),
                "split_counts": report.get("split_counts", {}),
                "evidence_tiers": report.get("evidence_tiers", {}),
                "release_ready": report.get("release_ready", {}),
                "quarantine_reasons": report.get("quarantine_reasons", {}),
            }
        ),
        "",
        "## Relation And Metric Families",
        "",
        _json_block(
            {
                "relation_families": report.get("relation_families", {}),
                "measurement_scopes": report.get("measurement_scopes", {}),
                "answer_formats": report.get("answer_formats", {}),
            }
        ),
    ]
    if validation is not None:
        lines.extend(["", "## Validation", "", _json_block(validation)])
    if audit is not None:
        lines.extend(["", "## Leakage Audit", "", _json_block(audit)])
    if failures is not None:
        lines.extend(["", "## Query Failure Manifest", "", _json_block(failures)])
    lines.extend(
        [
            "",
            "## Intended Use",
            "",
            "Use `public.jsonl` or request exports for model input. Use `private.jsonl`, hidden query programs, candidate traces, and verifier outputs only for dataset construction, auditing, grading, and error analysis.",
            "",
        ]
    )
    return "\n".join(lines)


def _json_block(value: dict[str, Any]) -> str:
    return "```json\n" + json.dumps(value, indent=2, sort_keys=True) + "\n```"
