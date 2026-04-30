"""Quarantine reporting for non-release-ready graph rows."""

from __future__ import annotations

from collections import Counter
from typing import Any


def quarantine_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    reasons: Counter[str] = Counter()
    tiers: Counter[str] = Counter()
    examples: list[dict[str, Any]] = []
    quarantined = []
    for row in rows:
        tiers[row.get("evidence_tier", "unknown")] += 1
        if row.get("release_ready") is False:
            quarantined.append(row)
            row_reasons = row.get("quarantine_reasons", []) or ["unknown"]
            reasons.update(row_reasons)
            if len(examples) < 20:
                examples.append(
                    {
                        "row_id": row.get("row_id"),
                        "source_id": row.get("source_id"),
                        "query_id": row.get("query_program", {}).get("query_id"),
                        "logical_hop_count": row.get("logical_hop_count"),
                        "difficulty_bucket": row.get("difficulty_bucket"),
                        "evidence_tier": row.get("evidence_tier"),
                        "quarantine_reasons": row_reasons,
                    }
                )
    return {
        "row_count": len(rows),
        "release_ready_count": len(rows) - len(quarantined),
        "quarantine_count": len(quarantined),
        "valid_for_release": not quarantined,
        "evidence_tiers": dict(sorted(tiers.items())),
        "reasons": dict(sorted(reasons.items())),
        "examples": examples,
    }
