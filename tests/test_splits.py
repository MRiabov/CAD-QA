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
