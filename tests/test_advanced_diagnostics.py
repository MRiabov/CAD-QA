from cad_qa.baselines import baseline_predictions, run_baselines
from cad_qa.config import DatasetConfig
from cad_qa.fixtures import smoke_traces
from cad_qa.materialize import materialize_rows, rows_to_dicts
from cad_qa.parse import grade_candidate
from cad_qa.schema import validate_public_row


def test_advanced_diagnostic_rows_are_materialized_from_smoke_traces():
    config = DatasetConfig()
    rows = [
        row
        for source, trace in smoke_traces(config)
        for row in materialize_rows(source, trace, config=config)
    ]
    task_types = {row.task_type for row in rows}

    assert {"graph_query", "spatial_distance", "bbox_region_query", "validity_failure_prediction"} <= task_types

    graph_row = next(row for row in rows if row.task_type == "graph_query")
    assert graph_row.answer == "wp3"
    assert graph_row.labels["graph_query"]["aggregation"] == "argmax"
    assert not validate_public_row(rows_to_dicts([graph_row])[0])

    distance_row = next(row for row in rows if row.task_type == "spatial_distance" and row.answer == 6.0)
    assert distance_row.answer == 6.0
    assert distance_row.unit == "mm"
    assert grade_candidate(rows_to_dicts([distance_row])[0], "6")["correct"]

    region_row = next(row for row in rows if row.task_type == "bbox_region_query" and row.answer == 8)
    assert region_row.answer == 8
    assert region_row.labels["spatial_query"]["predicate"] == "inside"

    validity_row = next(row for row in rows if row.task_type == "validity_failure_prediction")
    assert validity_row.answer == "valid"
    assert validity_row.choices == ["valid", "invalid", "inconclusive"]


def test_advanced_diagnostic_naive_baseline_is_available():
    config = DatasetConfig()
    source, trace = smoke_traces(config)[1]
    rows = rows_to_dicts(materialize_rows(source, trace, config=config))

    predictions = baseline_predictions(rows, name="advanced_diagnostic_naive")
    metrics = run_baselines(rows)

    assert "advanced_diagnostic_naive" in metrics
    assert set(predictions) == {row["id"] for row in rows}
