"""Configuration and label-policy primitives."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from typing import Any

from cad_qa.hashing import sha256_json


@dataclass(frozen=True)
class LabelPolicy:
    linear_tolerance_mm: float = 1e-6
    angular_tolerance_rad: float = 1e-6
    volume_tolerance_abs_mm3: float = 1e-6
    volume_tolerance_ratio: float = 1e-8
    bbox_tolerance_mm: float = 1e-6
    spatial_distance_tolerance_mm: float = 1e-5
    bbox_region_overlap_tolerance_mm: float = 1e-6
    point_boundary_tolerance_mm: float = 1e-5
    selector_dedup_tolerance_mm: float = 1e-7
    near_boundary_sampling_band_mm: float = 1e-3
    validity_probe_repeat_count: int = 3


@dataclass(frozen=True)
class DatasetConfig:
    dataset_name: str = "CAD-QA"
    dataset_version: str = "cadqa-v0.1"
    seed: int = 1234
    license: str = "apache-2.0"
    label_policy: LabelPolicy = field(default_factory=LabelPolicy)
    trace_timeout_seconds: float = 10.0
    worker_count: int = 1
    max_rows_per_source: int = 192
    max_rows_per_source_task_type: int = 32
    max_runtime_probe_labels_per_source: int = 64
    max_runtime_probe_labels_per_task_type: int = 32

    @property
    def config_hash(self) -> str:
        return sha256_json(asdict(self))


def load_config(path: Path | None) -> DatasetConfig:
    if path is None:
        return DatasetConfig()
    data = _load_mapping(path)
    policy_data = data.pop("label_policy", None) or {}
    return DatasetConfig(label_policy=LabelPolicy(**policy_data), **data)


def _load_mapping(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        loaded = json.loads(text)
    else:
        try:
            import yaml  # type: ignore[import-untyped]
        except ModuleNotFoundError as exc:
            raise RuntimeError("YAML config loading requires the 'yaml' extra") from exc
        loaded = yaml.safe_load(text)
    if not isinstance(loaded, dict):
        raise ValueError(f"config must contain a JSON/YAML object: {path}")
    return dict(loaded)
