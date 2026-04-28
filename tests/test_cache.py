from cad_qa.cache import load_cached_trace, store_cached_trace
from cad_qa.config import DatasetConfig
from cad_qa.fixtures import smoke_traces


def test_trace_cache_round_trips(tmp_path):
    config = DatasetConfig()
    source, trace = smoke_traces(config)[0]

    assert load_cached_trace(tmp_path, source, config) is None
    store_cached_trace(tmp_path, source, config, trace)
    cached = load_cached_trace(tmp_path, source, config)

    assert cached is not None
    assert cached.trace_id == trace.trace_id
    assert cached.source_id == trace.source_id
