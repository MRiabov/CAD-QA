from cad_qa.splits import assign_row_splits, leakage_audit


def test_protected_operation_holdout_keeps_source_groups_together():
    rows = []
    for index in range(20):
        for task_index in range(2):
            rows.append(
                {
                    "id": f"row_{index}_{task_index}",
                    "source_id": f"src_{index}",
                    "split": "train",
                    "provenance": {
                        "source_id": f"src_{index}",
                        "generator_id": f"gen_{index % 5}",
                        "source_subtree": "CADEvolve-C",
                        "operation_signature_hash": f"op_{index}",
                        "topology_signature_hash": f"topo_{index}",
                    },
                }
            )

    assigned = assign_row_splits(rows, seed=1234)
    by_source = {}
    for row in assigned:
        by_source.setdefault(row["source_id"], set()).add(row["split"])

    assert all(len(splits) == 1 for splits in by_source.values())
    assert any(row["split"] == "test_operation_heldout" for row in assigned)
    assert leakage_audit(assigned)["status"] == "pass"


def test_near_boundary_rows_route_whole_source_group_to_hard_split():
    rows = [
        {
            "id": "row_near",
            "source_id": "src_a",
            "split": "train",
            "provenance": {
                "source_id": "src_a",
                "normalized_source_code_hash": "hash_a",
                "point_sampling_group_id": "near_boundary:src_a:near_boundary_inside",
                "split_group": "src_a",
            },
        },
        {
            "id": "row_same_source",
            "source_id": "src_a",
            "split": "train",
            "provenance": {
                "source_id": "src_a",
                "normalized_source_code_hash": "hash_a",
                "split_group": "src_a",
            },
        },
        {
            "id": "row_other",
            "source_id": "src_b",
            "split": "train",
            "provenance": {
                "source_id": "src_b",
                "normalized_source_code_hash": "hash_b",
                "split_group": "src_b",
            },
        },
        {
            "id": "row_third",
            "source_id": "src_c",
            "split": "train",
            "provenance": {
                "source_id": "src_c",
                "normalized_source_code_hash": "hash_c",
                "split_group": "src_c",
            },
        },
    ]

    assigned = assign_row_splits(rows, seed=1234)

    assert {row["split"] for row in assigned if row["source_id"] == "src_a"} == {
        "test_near_boundary"
    }
    assert leakage_audit(assigned)["status"] == "pass"
