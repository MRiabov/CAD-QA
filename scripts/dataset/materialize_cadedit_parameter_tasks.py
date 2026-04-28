"""Materialize CADEditQA parameter-edit-direction rows from counterfactual manifests."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
from typing import Any

from cad_qa.hashing import sha256_json
from cad_qa.jsonio import read_json, write_json, write_jsonl
from cad_qa.splits import assign_row_splits, split_manifest


CHOICES = ["increase", "decrease", "unchanged", "no_valid_edit"]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("counterfactual_manifest", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--dataset-version", default="cadeditqa-v0.1")
    parser.add_argument("--seed", type=int, default=1234)
    args = parser.parse_args(argv)

    manifest = read_json(args.counterfactual_manifest)
    rows = materialize_parameter_edit_rows(manifest, dataset_version=args.dataset_version)
    rows = assign_row_splits(rows, args.seed)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    _write_split_jsonl(args.output_dir / "jsonl", rows)
    write_json(args.output_dir / "split_manifest.json", split_manifest(rows))
    report = {
        "schema": "cadeditqa_parameter_edit_direction_report_v1",
        "counterfactual_manifest": str(args.counterfactual_manifest),
        "dataset_version": args.dataset_version,
        "row_count": len(rows),
        "row_counts_by_split": dict(Counter(str(row.get("split")) for row in rows)),
        "row_counts_by_answer": dict(Counter(str(row.get("answer")) for row in rows)),
        "row_counts_by_source": dict(Counter(str(row.get("source_id")) for row in rows)),
    }
    write_json(args.output_dir / "metadata.json", report)
    print(report)


def materialize_parameter_edit_rows(manifest: dict[str, Any], *, dataset_version: str) -> list[dict[str, Any]]:
    rows = []
    for variant in manifest.get("variants", []):
        if not isinstance(variant, dict):
            continue
        old_value = _number(variant.get("changed_value"))
        new_value = _number(variant.get("new_value"))
        if old_value is None or new_value is None:
            continue
        direction = _direction(old_value, new_value)
        original_code = str(variant.get("original_code") or "")
        source_id = _source_id(variant)
        group_id = str(variant.get("group_id") or source_id)
        variant_id = str(variant.get("variant_id") or sha256_json(variant).removeprefix("sha256:")[:16])
        source_line = variant.get("source_line")
        prompt = (
            "Given the CadQuery script below, choose the edit direction for the numeric literal "
            f"at source line `{source_line}` so it changes from `{old_value}` to `{new_value}`. "
            "Answer with exactly one of increase, decrease, unchanged, or no_valid_edit.\n\n"
            f"```python\n{original_code}```"
        )
        prompt_hash = sha256_json({"task_type": "parameter_edit_direction", "variant_id": variant_id, "prompt": prompt})
        row_payload = {
            "dataset_version": dataset_version,
            "task_type": "parameter_edit_direction",
            "source_id": source_id,
            "trace_id": group_id,
            "target_feature_id": f"line:{source_line}",
            "answer": direction,
            "prompt_hash": prompt_hash,
        }
        rows.append(
            {
                "id": "cadedit_parameter_edit_direction_" + sha256_json(row_payload).removeprefix("sha256:")[:16],
                "dataset_version": dataset_version,
                "task_type": "parameter_edit_direction",
                "source_id": source_id,
                "trace_id": group_id,
                "target_feature_id": f"line:{source_line}",
                "split": "train",
                "prompt": prompt,
                "answer_type": "enum",
                "answer": direction,
                "choices": CHOICES,
                "unit": None,
                "numeric_tolerance": None,
                "requires": ["cadquery_syntax", "counterfactual_edit", "numeric_parameter"],
                "difficulty_tags": ["cadeditqa", "parameter_edit_direction"],
                "labels": {
                    "answer_status": "ok",
                    "failure_reason": None,
                    "old_value": old_value,
                    "new_value": new_value,
                    "edit_direction": direction,
                    "source_line": source_line,
                    "source_column": variant.get("source_column"),
                },
                "diagnostics": {
                    "answer_status": "ok",
                    "failure_reason": None,
                    "variant_id": variant_id,
                    "original_relative_path": variant.get("original_relative_path"),
                    "variant_relative_path": variant.get("variant_relative_path"),
                },
                "provenance": {
                    "source": "cadevolve_counterfactual",
                    "source_id": source_id,
                    "generator_id": None,
                    "source_subtree": None,
                    "normalized_archive_member_path": variant.get("original_relative_path"),
                    "normalized_source_code_hash": sha256_json(original_code),
                    "operation_signature_hash": None,
                    "topology_signature_hash": None,
                    "counterfactual_group_id": group_id,
                    "point_sampling_group_id": None,
                },
                "hashes": {"prompt_hash": prompt_hash, "variant_hash": sha256_json(variant)},
                "parse_policy": "strict_enum_v1",
            }
        )
        value_prompt = (
            "Given the CadQuery script below, predict the edited numeric value for the literal "
            f"at source line `{source_line}` after the counterfactual change. "
            "Answer with exactly one finite number.\n\n"
            f"Original value: {old_value}\n\n"
            f"```python\n{original_code}```"
        )
        value_prompt_hash = sha256_json({"task_type": "counterfactual_parameter", "variant_id": variant_id, "prompt": value_prompt})
        value_payload = {
            "dataset_version": dataset_version,
            "task_type": "counterfactual_parameter",
            "source_id": source_id,
            "trace_id": group_id,
            "target_feature_id": f"line:{source_line}",
            "answer": new_value,
            "prompt_hash": value_prompt_hash,
        }
        rows.append(
            {
                "id": "cadedit_counterfactual_parameter_" + sha256_json(value_payload).removeprefix("sha256:")[:16],
                "dataset_version": dataset_version,
                "task_type": "counterfactual_parameter",
                "source_id": source_id,
                "trace_id": group_id,
                "target_feature_id": f"line:{source_line}",
                "split": "train",
                "prompt": value_prompt,
                "answer_type": "number",
                "answer": new_value,
                "choices": None,
                "unit": None,
                "numeric_tolerance": 1e-9,
                "requires": ["cadquery_syntax", "counterfactual_edit", "numeric_parameter"],
                "difficulty_tags": ["cadeditqa", "counterfactual_parameter"],
                "labels": {
                    "answer_status": "ok",
                    "failure_reason": None,
                    "old_value": old_value,
                    "new_value": new_value,
                    "edit_direction": direction,
                    "source_line": source_line,
                    "source_column": variant.get("source_column"),
                },
                "diagnostics": {
                    "answer_status": "ok",
                    "failure_reason": None,
                    "variant_id": variant_id,
                    "original_relative_path": variant.get("original_relative_path"),
                    "variant_relative_path": variant.get("variant_relative_path"),
                },
                "provenance": {
                    "source": "cadevolve_counterfactual",
                    "source_id": source_id,
                    "generator_id": None,
                    "source_subtree": None,
                    "normalized_archive_member_path": variant.get("original_relative_path"),
                    "normalized_source_code_hash": sha256_json(original_code),
                    "operation_signature_hash": None,
                    "topology_signature_hash": None,
                    "counterfactual_group_id": group_id,
                    "point_sampling_group_id": None,
                },
                "hashes": {"prompt_hash": value_prompt_hash, "variant_hash": sha256_json(variant)},
                "parse_policy": "numeric_4_sigfig_v1",
            }
        )
    return rows


def _write_split_jsonl(jsonl_dir: Path, rows: list[dict[str, Any]]) -> None:
    by_split: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_split.setdefault(str(row["split"]), []).append(row)
    for split, split_rows in sorted(by_split.items()):
        write_jsonl(jsonl_dir / f"{split}.jsonl", sorted(split_rows, key=lambda row: str(row["id"])))


def _number(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def _direction(old_value: float, new_value: float) -> str:
    if new_value > old_value:
        return "increase"
    if new_value < old_value:
        return "decrease"
    return "unchanged"


def _source_id(variant: dict[str, Any]) -> str:
    key = variant.get("original_relative_path") or variant.get("group_id") or variant.get("original_code")
    return "cadedit_src_" + sha256_json(str(key)).removeprefix("sha256:")[:16]


if __name__ == "__main__":
    main()
