from cad_qa.operation_graph import extract_operation_graph, operation_signature_hash


def test_extracts_simple_cadevolve_style_assignments():
    code = """\
import cadquery as cq
wp0 = cq.Workplane("XY")
wp1 = wp0.box(10, 20, 30)
wp2 = wp1.faces(">Z").workplane()
wp3 = wp2.hole(2)
result = wp3
"""

    nodes, result_variable, issues = extract_operation_graph(code)

    assert result_variable == "result"
    assert not [issue for issue in issues if issue.startswith("unsupported")]
    assert [node.operation for node in nodes] == [
        "Workplane",
        "box",
        "faces",
        "workplane",
        "hole",
    ]
    assert nodes[1].feature_id == "wp1"
    assert nodes[-1].target == "wp3"
    assert operation_signature_hash(nodes).startswith("sha256:")


def test_records_unsupported_dynamic_statement():
    nodes, result_variable, issues = extract_operation_graph("for i in range(3):\n    pass\n")

    assert nodes == []
    assert result_variable is None
    assert issues == ["unsupported_statement:For:1"]
