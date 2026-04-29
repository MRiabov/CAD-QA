from cad_qa.scheduler import schedule_and_label_descriptors, schedule_descriptors


def _descriptor(
    descriptor_id: str,
    task_type: str,
    stratum: str,
    target_feature_id: str = "feature",
):
    return {
        "descriptor_id": descriptor_id,
        "task_type": task_type,
        "stratum": stratum,
        "target_feature_id": target_feature_id,
        "label_cost": 1,
        "payload": descriptor_id,
    }


def _ids(result):
    return [descriptor["descriptor_id"] for descriptor in result.selected_descriptors]


def test_scheduler_is_reproducible_for_same_seed():
    descriptors = [
        _descriptor(f"selector_{index}", "selector_count", "generated_face")
        for index in range(12)
    ]

    first = schedule_descriptors(
        descriptors,
        seed=123,
        max_per_source=5,
        max_per_task_type=5,
        scope="same",
    )
    second = schedule_descriptors(
        descriptors,
        seed=123,
        max_per_source=5,
        max_per_task_type=5,
        scope="same",
    )

    assert _ids(first) == _ids(second)


def test_scheduler_seed_changes_sampling_when_bucket_has_multiple_items():
    descriptors = [
        _descriptor(f"point_{index}", "point_membership", "deep_inside")
        for index in range(20)
    ]

    first = schedule_descriptors(
        descriptors,
        seed=1,
        max_per_source=6,
        max_per_task_type=6,
        scope="sample",
    )
    second = schedule_descriptors(
        descriptors,
        seed=2,
        max_per_source=6,
        max_per_task_type=6,
        scope="sample",
    )

    assert _ids(first) != _ids(second)


def test_scheduler_round_robins_across_task_strata():
    descriptors = [
        *[
            _descriptor(f"selector_{index}", "selector_count", "generated_face")
            for index in range(20)
        ],
        *[_descriptor("point_a", "point_membership", "deep_inside")],
        *[_descriptor("point_b", "point_membership", "deep_outside")],
    ]

    result = schedule_descriptors(
        descriptors,
        seed=42,
        max_per_source=4,
        max_per_task_type=4,
        scope="round-robin",
    )

    assert {descriptor["task_type"] for descriptor in result.selected_descriptors} == {
        "selector_count",
        "point_membership",
    }
    point_count = len(
        [
            item
            for item in result.selected_descriptors
            if item["task_type"] == "point_membership"
        ]
    )
    assert point_count == 2


def test_scheduler_enforces_source_and_task_caps():
    descriptors = [
        *[
            _descriptor(f"selector_{index}", "selector_count", "generated_face")
            for index in range(10)
        ],
        *[
            _descriptor(f"point_{index}", "point_membership", "deep_inside")
            for index in range(10)
        ],
    ]

    result = schedule_descriptors(
        descriptors,
        seed=7,
        max_per_source=5,
        max_per_task_type=3,
        scope="caps",
    )

    assert len(result.selected_descriptors) == 5
    assert result.manifest["scheduled_label_counts_by_task_type"] == {
        "point_membership": 3,
        "selector_count": 2,
    }


def test_failed_labels_backfill_from_later_scheduled_descriptors():
    descriptors = [
        _descriptor("fail_a", "selector_count", "generated_face"),
        _descriptor("ok_b", "selector_count", "generated_face"),
        _descriptor("ok_c", "selector_count", "generated_edge"),
    ]

    result = schedule_and_label_descriptors(
        descriptors,
        labeler=lambda descriptor: None
        if descriptor["descriptor_id"] == "fail_a"
        else descriptor["payload"],
        seed=102,
        max_per_source=3,
        max_per_task_type=3,
        scope="backfill",
    )

    assert len(result.labeled_payloads) == 2
    assert "fail_a" not in result.labeled_payloads
    assert result.manifest["label_failure_counts_by_task_type"] == {
        "selector_count": 1
    }
