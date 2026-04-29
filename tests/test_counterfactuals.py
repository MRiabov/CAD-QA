from cad_qa.counterfactuals import numeric_parameter_variants


def test_numeric_parameter_variants_are_grouped():
    code = (
        "import cadquery as cq\nwp = cq.Workplane('XY').box(10, 20, 30)\nresult = wp\n"
    )

    variants = numeric_parameter_variants(code, max_variants=1)

    assert len(variants) == 2
    assert variants[0].group_id == variants[1].group_id
    assert variants[0].variant_code != code
    assert "11.0" in variants[0].variant_code or "9.0" in variants[0].variant_code
