# CAD-QA Benchmark Family

CAD-QA is a single benchmark family over typed CAD ontology graphs.

Rows are grouped by hop count, relation families, and measurement scopes:

- 0-hop rows: direct source statistics and parser calibration.
- 1-hop rows: resolve one entity and read one metric.
- 2-hop rows: traverse one relation and read or compare a metric.
- 3+ hop rows: BrowseComp-style CAD reasoning with obfuscated, distractor-rich
  public clues.

The family includes profile, workplane, selector, topology, path, distance,
material-region, void-region, provenance, validity, and edit-effect questions
only when those questions are represented as deterministic query programs over
the ontology graph.

The graph is the benchmark; rows should be named by hop count, relation family,
and measurement scope.
