from dataclasses import replace

from cad_qa.cache import load_cached_trace, store_cached_trace
from cad_qa.config import DatasetConfig
from cad_qa.fixtures import smoke_traces


def test_trace_cache_round_trips(tmp_path):
    config = DatasetConfig()
    source, trace = smoke_traces(config)[0]
    trace = replace(
        trace,
        candidate_descriptors=[
            {
                "descriptor_id": "descriptor_a",
                "task_type": "selector_count",
                "stratum": "generated_face",
                "payload": {"selector_expression": "wp1.faces()"},
            }
        ],
        sampling_manifest={
            "descriptor_counts_by_task_type": {"selector_count": 1},
            "scheduled_label_counts_by_task_type": {"selector_count": 1},
        },
    )

    assert load_cached_trace(tmp_path, source, config) is None
    store_cached_trace(tmp_path, source, config, trace)
    cached = load_cached_trace(tmp_path, source, config)

    assert cached is not None
    assert cached.trace_id == trace.trace_id
    assert cached.source_id == trace.source_id
    assert cached.candidate_descriptors == trace.candidate_descriptors
    assert cached.sampling_manifest == trace.sampling_manifest
