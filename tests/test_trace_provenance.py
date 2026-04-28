from cad_qa.trace import _topology_match_provenance_records


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
            "matching_method": "geometry_signature_nearest",
            "provenance_confidence": 0.9,
            "topology_match": {
                "from_feature_id": "wp1",
                "to_feature_id": "wp2",
                "from_entity_id": "face_a",
                "to_entity_id": "face_b",
                "entity_type": "face",
                "matching_method": "geometry_signature_nearest",
                "confidence": 0.9,
            },
        }
    ]
