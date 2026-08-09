import json, sys
import pyarrow.parquet as pq

GRAPH_DIR = "runs/current_cadevolve1000_10k_regen_20260613/graph/graphs"
OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/1hop_queries.jsonl"
MAX_GRAPHS = int(sys.argv[2]) if len(sys.argv) > 2 else 1000

# Only workplane targets: source_ref mode resolves to script variable names (wp1),
# which the teacher can derive from the script. Face targets resolve to kernel
# internal ids / "kernel" that are NOT present in the script (unsolvable).
TEMPLATES = [
    ("argmax", "origin_z", "workplane"),
    ("argmin", "origin_z", "workplane"),
    ("argmax", "area", "workplane"),
    ("argmin", "area", "workplane"),
    ("argmax", "bbox_center_z", "workplane"),
    ("argmin", "bbox_center_z", "workplane"),
    ("argmax", "bbox_center_x", "workplane"),
    ("argmin", "bbox_center_x", "workplane"),
    ("argmax", "distance_to_origin", "workplane"),
    ("argmin", "distance_to_origin", "workplane"),
]

import glob
pats = sorted(glob.glob(f"{GRAPH_DIR}/part-*.parquet"))
graph_ids = []
for f in pats:
    t = pq.read_table(f, columns=["graph_id"])
    graph_ids.extend(t.column("graph_id").to_pylist())
graph_ids = graph_ids[:MAX_GRAPHS]

n = 0
with open(OUT, "w") as f:
    for gid in graph_ids:
        for agg, metric, ttype in TEMPLATES:
            rec = {
                "graph_id": gid,
                "query": {
                    "aggregation": agg,
                    "aggregation_metric": metric,
                    "answer_spec": {
                        "answer_format": "text",
                        "candidate_labels": {},
                        "candidate_set": "prefinal",
                        "candidate_texts": {},
                        "decimals": 6,
                        "max_candidate_labels": 7,
                        "metric": None,
                        "mode": "source_ref",
                    },
                    "answer_type": "text",
                    "clauses": [],
                    "difficulty": "low",
                    "hop_count": 1,
                    "min_individual_clause_candidates": 3,
                    "query_id": f"graph:{gid}:q1:{agg}_{metric}_{ttype}",
                    "reject_unless_unique": True,
                    "target_type": ttype,
                },
            }
            f.write(json.dumps(rec) + "\n")
            n += 1
print(f"generated {n} 1-hop queries for {len(graph_ids)} graphs -> {OUT}")
