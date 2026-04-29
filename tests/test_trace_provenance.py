from cad_qa.trace import (
    _lineage_provenance_records,
    _topology_match_provenance_records,
)


def test_topology_matches_become_provenance_records():
    records = _topology_match_provenance_records(
        [
            {
                "from_feature_id": "wp1",
                "to_feature_id": "wp2",
                "from_entity_id": "face_a",
                "to_entity_id": "face_b",
                "entity_type": "face",
                "matching_method": "geometry_signature_nearest",
                "confidence": 0.9,
            }
        ]
    )

    assert records == [
        {
            "target_description": "face `face_b` inherited from adjacent snapshot",
            "target_feature_id": "wp2",
            "provenance_relation": "inherited_from",
            "answer_feature_id": "wp1",
            "contributor_feature_ids": ["wp1", "wp2"],
            "first_contributor_feature_id": "wp1",
            "first_contributor_rule": "min_step_index",
            "matching_method": "geometry_signature_nearest",
            "provenance_confidence": 0.9,
            "topology_matches": [
                {
                    "from_feature_id": "wp1",
                    "to_feature_id": "wp2",
                    "from_entity_id": "face_a",
                    "to_entity_id": "face_b",
                    "entity_type": "face",
                    "matching_method": "geometry_signature_nearest",
                    "confidence": 0.9,
                }
            ],
        }
    ]


def test_lineage_records_answer_earliest_transitive_contributor():
    snapshots = [
        _snapshot("wp1", 0, "face_a"),
        _snapshot("wp2", 1, "face_b"),
        _snapshot("wp3", 2, "face_c"),
    ]
    records = _lineage_provenance_records(
        snapshots,
        [
            _match("wp1", "wp2", "face_a", "face_b"),
            _match("wp2", "wp3", "face_b", "face_c"),
        ],
    )

    final_record = next(
        record for record in records if record["target_feature_id"] == "wp3"
    )

    assert final_record["answer_feature_id"] == "wp1"
    assert final_record["first_contributor_feature_id"] == "wp1"
    assert final_record["contributor_feature_ids"] == ["wp1", "wp2", "wp3"]


def test_topology_match_records_merge_multiple_prior_contributors():
    records = _topology_match_provenance_records(
        [
            _match("wp1", "wp3", "face_a", "face_c"),
            _match("wp2", "wp3", "face_b", "face_c"),
        ]
    )

    assert records[0]["provenance_relation"] == "bounded_by"
    assert records[0]["answer_feature_id"] == "wp1"
    assert records[0]["contributor_feature_ids"] == ["wp1", "wp2", "wp3"]


def _snapshot(feature_id: str, step_index: int, entity_id: str) -> dict:
    return {
        "feature_id": feature_id,
        "step_index": step_index,
        "diagnostics": {
            "entity_signatures": {
                "face": [
                    {
                        "entity_id": entity_id,
                        "entity_type": "face",
                        "geometry_type": "PLANE",
                        "center": [0.0, 0.0, 0.0],
                        "measure": 1.0,
                    }
                ]
            }
        },
    }


def _match(
    from_feature: str, to_feature: str, from_entity: str, to_entity: str
) -> dict:
    return {
        "from_feature_id": from_feature,
        "to_feature_id": to_feature,
        "from_entity_id": from_entity,
        "to_entity_id": to_entity,
        "entity_type": "face",
        "matching_method": "geometry_signature_nearest",
        "confidence": 0.9,
    }
