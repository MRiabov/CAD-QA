# CAD-QA Label Rules

Labels are valid only when they are produced by deterministic source, trace, or
ontology evidence and verified by the query resolver.

## General Rules

- Each public release row must have a matching private verifier row carrying
  the hidden query program that produced it.
- Candidate traces must show how each clause changed the candidate set.
- Ties are rejected unless the query explicitly allows a set-valued answer.
- Geometry labels must record tolerance and evidence source.
- Quarantined labels may be useful diagnostics but are not release-grade.

## Measurement Scopes

- `profile_intrinsic`: area, perimeter, centroid, local bbox, edge count,
  vertex count, primitive segment counts.
- `feature_application_effect`: signed volume delta, bbox delta, topology
  delta, edge-count delta, circular-edge delta.
- `entity_geometry`: coordinates, normals, axes, centroids, bboxes.
- `snapshot_state`: volume, topology, bbox, validity at a snapshot.
- `relation_metric`: distance, angle, containment, intersection metrics.

Do not attach effect measurements to intrinsic entities. For example,
`edge_count_delta` belongs to the feature application that used a profile, not
to the profile itself.

## Prompt Labels

Every rendered clue must map to a hidden clause. Public prompt text must avoid
private ontology terms unless it also grounds them in visible CadQuery source.
