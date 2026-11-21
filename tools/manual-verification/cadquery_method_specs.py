"""CadQuery method classification for the extraction-graph oracle.

The geometry path is deliberately separate from the Go graph builder; this
table is the classification the oracle needs to name an operation, feature, and
solid kind. It mirrors `02a`'s allowlist and must be diffed against it when
either changes.
"""

from __future__ import annotations

from extraction_oracle_schema import (
    FeatureKind,
    MethodSpec,
    OperationKind,
    SolidKind,
)

METHOD_SPECS: dict[str, MethodSpec] = {
    "Workplane": MethodSpec(
        operation_kind=OperationKind.WORKPLANE, state_producing=False
    ),
    "workplane": MethodSpec(
        operation_kind=OperationKind.WORKPLANE, state_producing=False
    ),
    "workplaneFromTagged": MethodSpec(
        operation_kind=OperationKind.WORKPLANE, state_producing=False
    ),
    "transformed": MethodSpec(
        operation_kind=OperationKind.WORKPLANE, state_producing=False
    ),
    "center": MethodSpec(operation_kind=OperationKind.SKETCH, state_producing=False),
    "circle": MethodSpec(operation_kind=OperationKind.SKETCH, state_producing=False),
    "rect": MethodSpec(operation_kind=OperationKind.SKETCH, state_producing=False),
    "ellipse": MethodSpec(operation_kind=OperationKind.SKETCH, state_producing=False),
    "polygon": MethodSpec(operation_kind=OperationKind.SKETCH, state_producing=False),
    "slot2D": MethodSpec(operation_kind=OperationKind.SKETCH, state_producing=False),
    "offset2D": MethodSpec(operation_kind=OperationKind.SKETCH, state_producing=False),
    "pushPoints": MethodSpec(
        operation_kind=OperationKind.SKETCH, state_producing=False
    ),
    "moveTo": MethodSpec(operation_kind=OperationKind.PATH, state_producing=False),
    "lineTo": MethodSpec(operation_kind=OperationKind.PATH, state_producing=False),
    "hLine": MethodSpec(operation_kind=OperationKind.PATH, state_producing=False),
    "vLine": MethodSpec(operation_kind=OperationKind.PATH, state_producing=False),
    "threePointArc": MethodSpec(
        operation_kind=OperationKind.PATH, state_producing=False
    ),
    "polyline": MethodSpec(operation_kind=OperationKind.PATH, state_producing=False),
    "close": MethodSpec(operation_kind=OperationKind.PATH, state_producing=False),
    "line": MethodSpec(operation_kind=OperationKind.PATH, state_producing=False),
    "spline": MethodSpec(operation_kind=OperationKind.PATH, state_producing=False),
    "splineApprox": MethodSpec(
        operation_kind=OperationKind.PATH, state_producing=False
    ),
    "wire": MethodSpec(operation_kind=OperationKind.PATH, state_producing=False),
    "makeLine": MethodSpec(operation_kind=OperationKind.PATH, state_producing=False),
    "makeSpline": MethodSpec(operation_kind=OperationKind.PATH, state_producing=False),
    "makeCircle": MethodSpec(operation_kind=OperationKind.PATH, state_producing=False),
    "makePolygon": MethodSpec(operation_kind=OperationKind.PATH, state_producing=False),
    "assembleEdges": MethodSpec(
        operation_kind=OperationKind.PATH, state_producing=False
    ),
    "box": MethodSpec(
        operation_kind=OperationKind.SOLID,
        feature_kind=FeatureKind.ADD_MATERIAL,
        solid_kind=SolidKind.PRIMITIVE,
        state_producing=True,
    ),
    "cylinder": MethodSpec(
        operation_kind=OperationKind.SOLID,
        feature_kind=FeatureKind.ADD_MATERIAL,
        solid_kind=SolidKind.PRIMITIVE,
        state_producing=True,
    ),
    "sphere": MethodSpec(
        operation_kind=OperationKind.SOLID,
        feature_kind=FeatureKind.ADD_MATERIAL,
        solid_kind=SolidKind.PRIMITIVE,
        state_producing=True,
    ),
    "makeSphere": MethodSpec(
        operation_kind=OperationKind.SOLID,
        feature_kind=FeatureKind.ADD_MATERIAL,
        solid_kind=SolidKind.PRIMITIVE,
        state_producing=True,
    ),
    "extrude": MethodSpec(
        operation_kind=OperationKind.SOLID,
        feature_kind=FeatureKind.ADD_MATERIAL,
        solid_kind=SolidKind.EXTRUDE,
        state_producing=True,
    ),
    "loft": MethodSpec(
        operation_kind=OperationKind.SOLID,
        feature_kind=FeatureKind.ADD_MATERIAL,
        solid_kind=SolidKind.LOFT,
        state_producing=True,
    ),
    "sweep": MethodSpec(
        operation_kind=OperationKind.SOLID,
        feature_kind=FeatureKind.ADD_MATERIAL,
        solid_kind=SolidKind.SWEEP,
        state_producing=True,
    ),
    "revolve": MethodSpec(
        operation_kind=OperationKind.SOLID,
        feature_kind=FeatureKind.ADD_MATERIAL,
        solid_kind=SolidKind.REVOLVE,
        state_producing=True,
    ),
    "twistExtrude": MethodSpec(
        operation_kind=OperationKind.SOLID,
        feature_kind=FeatureKind.ADD_MATERIAL,
        solid_kind=SolidKind.TWIST,
        state_producing=True,
    ),
    "text": MethodSpec(
        operation_kind=OperationKind.SOLID,
        feature_kind=FeatureKind.ADD_MATERIAL,
        solid_kind=SolidKind.TEXT,
        state_producing=True,
    ),
    "union": MethodSpec(
        operation_kind=OperationKind.BOOLEAN,
        feature_kind=FeatureKind.ADD_MATERIAL,
        solid_kind=SolidKind.BOOLEAN,
        state_producing=True,
    ),
    "cut": MethodSpec(
        operation_kind=OperationKind.BOOLEAN,
        feature_kind=FeatureKind.REMOVE_MATERIAL,
        solid_kind=SolidKind.BOOLEAN,
        state_producing=True,
    ),
    "intersect": MethodSpec(
        operation_kind=OperationKind.BOOLEAN,
        feature_kind=FeatureKind.MODIFY,
        solid_kind=SolidKind.BOOLEAN,
        state_producing=True,
    ),
    "combine": MethodSpec(
        operation_kind=OperationKind.ASSEMBLY,
        feature_kind=FeatureKind.CONSTRUCTION,
        solid_kind=SolidKind.ASSEMBLY,
        state_producing=True,
    ),
    "newObject": MethodSpec(
        operation_kind=OperationKind.ASSEMBLY,
        feature_kind=FeatureKind.CONSTRUCTION,
        solid_kind=SolidKind.ASSEMBLY,
        state_producing=False,
    ),
    "add": MethodSpec(
        operation_kind=OperationKind.ASSEMBLY,
        feature_kind=FeatureKind.ADD_MATERIAL,
        solid_kind=SolidKind.ASSEMBLY,
        state_producing=False,
    ),
    "fuse": MethodSpec(
        operation_kind=OperationKind.ASSEMBLY,
        feature_kind=FeatureKind.ADD_MATERIAL,
        solid_kind=SolidKind.ASSEMBLY,
        state_producing=True,
    ),
    "cutBlind": MethodSpec(
        operation_kind=OperationKind.MODIFIER,
        feature_kind=FeatureKind.REMOVE_MATERIAL,
        solid_kind=SolidKind.MODIFIER,
        state_producing=True,
    ),
    "cutThruAll": MethodSpec(
        operation_kind=OperationKind.MODIFIER,
        feature_kind=FeatureKind.REMOVE_MATERIAL,
        solid_kind=SolidKind.MODIFIER,
        state_producing=True,
    ),
    "hole": MethodSpec(
        operation_kind=OperationKind.MODIFIER,
        feature_kind=FeatureKind.REMOVE_MATERIAL,
        solid_kind=SolidKind.MODIFIER,
        state_producing=True,
    ),
    "cskHole": MethodSpec(
        operation_kind=OperationKind.MODIFIER,
        feature_kind=FeatureKind.REMOVE_MATERIAL,
        solid_kind=SolidKind.MODIFIER,
        state_producing=True,
    ),
    "cboreHole": MethodSpec(
        operation_kind=OperationKind.MODIFIER,
        feature_kind=FeatureKind.REMOVE_MATERIAL,
        solid_kind=SolidKind.MODIFIER,
        state_producing=True,
    ),
    "fillet": MethodSpec(
        operation_kind=OperationKind.MODIFIER,
        feature_kind=FeatureKind.MODIFY,
        solid_kind=SolidKind.MODIFIER,
        state_producing=True,
    ),
    "chamfer": MethodSpec(
        operation_kind=OperationKind.MODIFIER,
        feature_kind=FeatureKind.MODIFY,
        solid_kind=SolidKind.MODIFIER,
        state_producing=True,
    ),
    "shell": MethodSpec(
        operation_kind=OperationKind.MODIFIER,
        feature_kind=FeatureKind.MODIFY,
        solid_kind=SolidKind.MODIFIER,
        state_producing=True,
    ),
    "split": MethodSpec(
        operation_kind=OperationKind.MODIFIER,
        feature_kind=FeatureKind.MODIFY,
        solid_kind=SolidKind.MODIFIER,
        state_producing=True,
    ),
    "clean": MethodSpec(
        operation_kind=OperationKind.MODIFIER,
        feature_kind=FeatureKind.MODIFY,
        solid_kind=SolidKind.MODIFIER,
        state_producing=True,
    ),
    "rarray": MethodSpec(
        operation_kind=OperationKind.MODIFIER,
        feature_kind=FeatureKind.MODIFY,
        solid_kind=SolidKind.MODIFIER,
        state_producing=True,
    ),
    "translate": MethodSpec(
        operation_kind=OperationKind.TRANSFORM,
        feature_kind=FeatureKind.MODIFY,
        solid_kind=SolidKind.TRANSFORM,
        state_producing=True,
    ),
    "rotate": MethodSpec(
        operation_kind=OperationKind.TRANSFORM,
        feature_kind=FeatureKind.MODIFY,
        solid_kind=SolidKind.TRANSFORM,
        state_producing=True,
    ),
    "mirror": MethodSpec(
        operation_kind=OperationKind.TRANSFORM,
        feature_kind=FeatureKind.MODIFY,
        solid_kind=SolidKind.TRANSFORM,
        state_producing=True,
    ),
    "tag": MethodSpec(
        operation_kind=OperationKind.MODIFIER,
        feature_kind=FeatureKind.MODIFY,
        solid_kind=SolidKind.MODIFIER,
        state_producing=False,
    ),
    "toPending": MethodSpec(
        operation_kind=OperationKind.MODIFIER,
        feature_kind=FeatureKind.MODIFY,
        solid_kind=SolidKind.MODIFIER,
        state_producing=False,
    ),
    "faces": MethodSpec(
        operation_kind=OperationKind.CADQUERY_SELECTOR, state_producing=False
    ),
    "edges": MethodSpec(
        operation_kind=OperationKind.CADQUERY_SELECTOR, state_producing=False
    ),
    "vertices": MethodSpec(
        operation_kind=OperationKind.CADQUERY_SELECTOR, state_producing=False
    ),
    "filter": MethodSpec(
        operation_kind=OperationKind.CADQUERY_SELECTOR, state_producing=False
    ),
    "NearestToPointSelector": MethodSpec(
        operation_kind=OperationKind.CADQUERY_SELECTOR, state_producing=False
    ),
    "val": MethodSpec(operation_kind=OperationKind.ACCESSOR, state_producing=False),
    "vals": MethodSpec(operation_kind=OperationKind.ACCESSOR, state_producing=False),
    "all": MethodSpec(operation_kind=OperationKind.ACCESSOR, state_producing=False),
    "first": MethodSpec(operation_kind=OperationKind.ACCESSOR, state_producing=False),
    "findSolid": MethodSpec(
        operation_kind=OperationKind.ACCESSOR, state_producing=False
    ),
    "Edges": MethodSpec(operation_kind=OperationKind.ACCESSOR, state_producing=False),
    "Solids": MethodSpec(operation_kind=OperationKind.ACCESSOR, state_producing=False),
    "Length": MethodSpec(operation_kind=OperationKind.ACCESSOR, state_producing=False),
    "list": MethodSpec(operation_kind=OperationKind.ACCESSOR, state_producing=False),
}
