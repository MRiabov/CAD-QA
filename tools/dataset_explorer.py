"""Local CAD-QA dataset explorer with cached runtime PNG renders.

This is intentionally dependency-light: it uses the standard-library HTTP
server, Polars for parquet reads, CadQuery for CAD model execution, and VTK for
offscreen PNG rendering.

Example:
    uv run python tools/dataset_explorer.py \
      --dataset runs/current_cadevolve1000_10k_regen_20260613/release_10k/rows.parquet \
      --port 8765
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import runpy
import subprocess
import sys
import tempfile
import time
from functools import cached_property
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

import polars as pl


DEFAULT_DATASET = Path("runs/current_cadevolve1000_10k_regen_20260613/release_10k/rows.parquet")


def main() -> int:
    args = _parse_args()
    if args.render_worker:
        return _render_worker(args)
    dataset = DatasetIndex(args.dataset)
    cache_dir = args.cache_dir or args.dataset.parent / "render_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    state = SimpleNamespace(
        dataset=dataset,
        cache_dir=cache_dir,
        render_timeout=args.render_timeout,
        python=sys.executable,
    )

    class Handler(DatasetExplorerHandler):
        app_state = state

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    url = f"http://{args.host}:{args.port}"
    print(f"Serving CAD-QA dataset explorer at {url}")
    print(f"Dataset: {args.dataset}")
    print(f"Rows: {dataset.row_count}; sources: {len(dataset.sources)}")
    print(f"Render cache: {cache_dir}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping explorer")
    finally:
        server.server_close()
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--render-timeout", type=float, default=30.0)
    parser.add_argument("--render-worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--source-file", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--out-png", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--width", type=int, default=1000, help=argparse.SUPPRESS)
    parser.add_argument("--height", type=int, default=760, help=argparse.SUPPRESS)
    return parser.parse_args()


class DatasetIndex:
    def __init__(self, path: Path) -> None:
        if path.is_dir():
            path = path / "rows.parquet"
        if not path.exists():
            raise FileNotFoundError(path)
        self.path = path
        self.frame = pl.read_parquet(path).with_columns(
            [
                pl.col("source_metadata").struct.field("source_collection").alias("source_collection"),
                pl.col("source_metadata").struct.field("source_subtree").alias("source_subtree"),
                pl.col("source_metadata").struct.field("path_family").alias("path_family"),
                pl.col("source_metadata").struct.field("source_feature_tags").alias("source_feature_tags"),
            ]
        )
        self.row_count = self.frame.height
        self.rows = self._rows()
        self.rows_by_id = {row["row_id"]: row for row in self.rows}
        self.sources = sorted({row["source_id"] for row in self.rows})

    def query(
        self,
        *,
        offset: int,
        limit: int,
        search: str = "",
        split: str = "",
        target_type: str = "",
        source_id: str = "",
        tag: str = "",
        order: str = "",
        seed: str = "",
    ) -> dict[str, Any]:
        matches = self.rows
        if search:
            needle = search.lower()
            matches = [
                row
                for row in matches
                if needle in row["prompt"].lower()
                or needle in row["gold_answer"].lower()
                or needle in row["source_id"].lower()
                or needle in row["source_path"].lower()
                or needle in row["prompt_template_id"].lower()
            ]
        if split:
            matches = [row for row in matches if row["split"] == split]
        if target_type:
            matches = [row for row in matches if row["target_type"] == target_type]
        if source_id:
            matches = [row for row in matches if row["source_id"] == source_id]
        if tag:
            matches = [row for row in matches if tag in row["source_feature_tags"]]
        if order == "random":
            matches = sorted(matches, key=lambda row: _stable_random_key(row, seed))
        total = len(matches)
        page = matches[offset : offset + limit]
        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "rows": [_summary(row) for row in page],
        }

    @cached_property
    def facets(self) -> dict[str, Any]:
        return {
            "splits": sorted({row["split"] for row in self.rows if row["split"]}),
            "target_types": sorted({row["target_type"] for row in self.rows if row["target_type"]}),
            "tags": sorted({tag for row in self.rows for tag in row["source_feature_tags"] if tag}),
            "sources": self.sources,
            "row_count": self.row_count,
            "source_count": len(self.sources),
        }

    def _rows(self) -> list[dict[str, Any]]:
        selected = self.frame.select(
            [
                "row_id",
                "source_id",
                "source_path",
                "source_hash",
                "source_code",
                "prompt",
                "gold_answer",
                "query_program",
                "candidate_trace",
                "relation_families",
                "measurement_scopes",
                "logical_hop_count",
                "geometry_hop_count",
                "split",
                "prompt_template_id",
                "difficulty_bucket",
                "verifier_status",
                "source_collection",
                "source_subtree",
                "path_family",
                "source_feature_tags",
            ]
        ).to_dicts()
        rows: list[dict[str, Any]] = []
        for row in selected:
            query = _parse_query_program(row["query_program"])
            row["target_type"] = str(query.get("target_type") or "")
            row["aggregation"] = str(query.get("aggregation") or "")
            row["aggregation_metric"] = str(query.get("aggregation_metric") or "")
            row["family"] = row["row_id"].rsplit(":", 1)[-1] if ":" in row["row_id"] else ""
            row["source_feature_tags"] = row.get("source_feature_tags") or []
            rows.append(row)
        return rows


class DatasetExplorerHandler(BaseHTTPRequestHandler):
    app_state: SimpleNamespace

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/" or parsed.path == "/index.html":
                self._send_html(INDEX_HTML)
            elif parsed.path == "/api/facets":
                self._send_json(self.app_state.dataset.facets)
            elif parsed.path == "/api/rows":
                self._send_json(self._api_rows(parsed.query))
            elif parsed.path == "/api/row":
                self._send_json(self._api_row(parsed.query))
            elif parsed.path.startswith("/render/") and parsed.path.endswith(".png"):
                self._send_render(parsed.path)
            else:
                self.send_error(HTTPStatus.NOT_FOUND)
        except Exception as exc:  # pragma: no cover - useful for local UI failures
            self._send_json({"error": type(exc).__name__, "message": str(exc)}, status=500)

    def log_message(self, format: str, *args: Any) -> None:
        sys.stderr.write("%s - %s\n" % (self.log_date_time_string(), format % args))

    def _api_rows(self, query: str) -> dict[str, Any]:
        params = parse_qs(query)
        return self.app_state.dataset.query(
            offset=max(0, _int_param(params, "offset", 0)),
            limit=min(200, max(1, _int_param(params, "limit", 50))),
            search=_str_param(params, "search"),
            split=_str_param(params, "split"),
            target_type=_str_param(params, "target_type"),
            source_id=_str_param(params, "source_id"),
            tag=_str_param(params, "tag"),
            order=_str_param(params, "order"),
            seed=_str_param(params, "seed"),
        )

    def _api_row(self, query: str) -> dict[str, Any]:
        row_id = _str_param(parse_qs(query), "row_id")
        row = self.app_state.dataset.rows_by_id.get(row_id)
        if row is None:
            raise KeyError(f"unknown row_id: {row_id}")
        public = dict(row)
        public["query_program"] = _parse_query_program(row["query_program"])
        return public

    def _send_render(self, path: str) -> None:
        source_id = unquote(path.removeprefix("/render/").removesuffix(".png"))
        row = next((item for item in self.app_state.dataset.rows if item["source_id"] == source_id), None)
        if row is None:
            self.send_error(HTTPStatus.NOT_FOUND, "unknown source")
            return
        png = render_png_for_row(
            row,
            cache_dir=self.app_state.cache_dir,
            timeout=self.app_state.render_timeout,
            python=self.app_state.python,
        )
        payload = png.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "image/png")
        self.send_header("Cache-Control", "public, max-age=86400")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_json(self, value: Any, *, status: int = 200) -> None:
        payload = json.dumps(value, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_html(self, value: str) -> None:
        payload = value.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def render_png_for_row(row: dict[str, Any], *, cache_dir: Path, timeout: float, python: str) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = row.get("source_hash") or row["source_id"]
    out = cache_dir / f"{_safe_filename(str(key))}.png"
    if out.exists() and out.stat().st_size > 0 and _png_looks_nonblank(out):
        return out
    source_file = cache_dir / f"{_safe_filename(str(key))}.py"
    source_file.write_text(row["source_code"], encoding="utf-8")
    tmp_out = out.with_suffix(".tmp.png")
    cmd = [
        python,
        str(Path(__file__).resolve()),
        "--render-worker",
        "--source-file",
        str(source_file),
        "--out-png",
        str(tmp_out),
    ]
    started = time.perf_counter()
    completed = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout or "render failed").strip())
    tmp_out.replace(out)
    elapsed = time.perf_counter() - started
    meta = {"source_id": row["source_id"], "source_hash": row.get("source_hash"), "elapsed_seconds": elapsed}
    out.with_suffix(".json").write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out


def _render_worker(args: argparse.Namespace) -> int:
    if args.source_file is None or args.out_png is None:
        raise ValueError("--source-file and --out-png are required for --render-worker")
    import cadquery as cq  # noqa: F401
    from cadquery import exporters
    import vtk

    args.out_png.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="cadqa-render-") as tmp:
        stl = Path(tmp) / "shape.stl"
        namespace = runpy.run_path(str(args.source_file))
        result = namespace.get("result")
        if result is None:
            raise ValueError("source did not define result")
        exporters.export(result, str(stl))
        _software_render_stl(stl, args.out_png, width=args.width, height=args.height, vtk=vtk)
    return 0


def _png_looks_nonblank(path: Path) -> bool:
    try:
        from PIL import Image, ImageStat

        image = Image.open(path).convert("RGB")
        extrema = ImageStat.Stat(image).extrema
    except Exception:
        return True
    return any(high > low for low, high in extrema)


def _software_render_stl(stl: Path, png: Path, *, width: int, height: int, vtk: Any) -> None:
    from PIL import Image, ImageDraw
    import numpy as np

    reader = vtk.vtkSTLReader()
    reader.SetFileName(str(stl))
    reader.Update()
    poly = reader.GetOutput()
    points = poly.GetPoints()
    if points is None or poly.GetNumberOfCells() == 0:
        _blank_render(png, width=width, height=height, text="No renderable geometry")
        return

    vertices = np.array([points.GetPoint(index) for index in range(points.GetNumberOfPoints())], dtype=float)
    triangles: list[tuple[int, int, int]] = []
    ids = vtk.vtkIdList()
    for cell_index in range(poly.GetNumberOfCells()):
        poly.GetCellPoints(cell_index, ids)
        if ids.GetNumberOfIds() == 3:
            triangles.append((ids.GetId(0), ids.GetId(1), ids.GetId(2)))
    if not triangles:
        _blank_render(png, width=width, height=height, text="No triangular facets")
        return

    centered = vertices - vertices.mean(axis=0)
    transform = _view_transform()
    projected = centered @ transform.T
    xy = projected[:, :2]
    span = np.ptp(xy, axis=0)
    max_span = float(max(span.max(), 1.0))
    scale = min(width * 0.78, height * 0.78) / max_span
    screen = np.column_stack(
        [
            width / 2.0 + xy[:, 0] * scale,
            height / 2.0 - xy[:, 1] * scale,
        ]
    )
    depth = projected[:, 2]
    light = np.array([0.35, -0.45, 0.82], dtype=float)
    light /= np.linalg.norm(light)

    image = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    facets = []
    for triangle in triangles:
        p0, p1, p2 = (projected[index] for index in triangle)
        normal = np.cross(p1 - p0, p2 - p0)
        length = np.linalg.norm(normal)
        if length <= 1e-9:
            continue
        normal /= length
        if normal[2] < 0:
            normal = -normal
        shade = 0.48 + 0.42 * max(float(np.dot(normal, light)), 0.0)
        color = tuple(max(0, min(255, int(channel * shade))) for channel in (176, 188, 204))
        outline = tuple(max(0, int(channel * 0.72)) for channel in color)
        polygon = [(float(screen[index, 0]), float(screen[index, 1])) for index in triangle]
        facets.append((float(np.mean([depth[index] for index in triangle])), polygon, color, outline))

    for _, polygon, color, outline in sorted(facets, key=lambda item: item[0]):
        draw.polygon(polygon, fill=color)
        draw.line([*polygon, polygon[0]], fill=outline, width=1)
    png.parent.mkdir(parents=True, exist_ok=True)
    image.save(png)


def _view_transform() -> Any:
    import numpy as np

    azimuth = math.radians(-38.0)
    elevation = math.radians(24.0)
    rz = np.array(
        [
            [math.cos(azimuth), -math.sin(azimuth), 0.0],
            [math.sin(azimuth), math.cos(azimuth), 0.0],
            [0.0, 0.0, 1.0],
        ],
        dtype=float,
    )
    rx = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.0, math.cos(elevation), -math.sin(elevation)],
            [0.0, math.sin(elevation), math.cos(elevation)],
        ],
        dtype=float,
    )
    return rx @ rz


def _blank_render(png: Path, *, width: int, height: int, text: str) -> None:
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.text((24, 24), text, fill=(80, 88, 104))
    png.parent.mkdir(parents=True, exist_ok=True)
    image.save(png)


def _vtk_render_stl(stl: Path, png: Path, *, width: int, height: int, vtk: Any) -> None:
    reader = vtk.vtkSTLReader()
    reader.SetFileName(str(stl))
    reader.Update()
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputConnection(reader.GetOutputPort())
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetColor(0.70, 0.74, 0.80)
    actor.GetProperty().SetSpecular(0.25)
    actor.GetProperty().SetSpecularPower(24)

    renderer = vtk.vtkRenderer()
    renderer.AddActor(actor)
    renderer.SetBackground(1.0, 1.0, 1.0)
    renderer.UseFXAAOn()
    light = vtk.vtkLight()
    light.SetLightTypeToSceneLight()
    light.SetPosition(1.5, -1.0, 1.2)
    light.SetIntensity(0.9)
    renderer.AddLight(light)

    window = vtk.vtkRenderWindow()
    window.SetOffScreenRendering(1)
    window.AddRenderer(renderer)
    window.SetSize(width, height)
    renderer.ResetCamera()
    camera = renderer.GetActiveCamera()
    camera.Azimuth(35)
    camera.Elevation(25)
    camera.Zoom(1.2)
    window.Render()

    image = vtk.vtkWindowToImageFilter()
    image.SetInput(window)
    image.Update()
    writer = vtk.vtkPNGWriter()
    writer.SetFileName(str(png))
    writer.SetInputConnection(image.GetOutputPort())
    writer.Write()


def _summary(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "row_id": row["row_id"],
        "source_id": row["source_id"],
        "source_path": row["source_path"],
        "prompt": _shorten(row["prompt"], 240),
        "gold_answer": row["gold_answer"],
        "split": row["split"],
        "family": row["family"],
        "target_type": row["target_type"],
        "aggregation": row["aggregation"],
        "aggregation_metric": row["aggregation_metric"],
        "logical_hop_count": row["logical_hop_count"],
        "geometry_hop_count": row["geometry_hop_count"],
        "prompt_template_id": row["prompt_template_id"],
        "source_feature_tags": row["source_feature_tags"],
    }


def _parse_query_program(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        return json.loads(value)
    return {}


def _safe_filename(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in value)[:180]


def _shorten(value: str, limit: int) -> str:
    text = " ".join(str(value).split())
    return text if len(text) <= limit else text[: limit - 1] + "..."


def _int_param(params: dict[str, list[str]], name: str, default: int) -> int:
    try:
        return int(params.get(name, [str(default)])[0])
    except ValueError:
        return default


def _str_param(params: dict[str, list[str]], name: str, default: str = "") -> str:
    return params.get(name, [default])[0]


def _stable_random_key(row: dict[str, Any], seed: str) -> str:
    row_id = str(row.get("row_id") or "")
    source_id = str(row.get("source_id") or "")
    return hashlib.sha256(f"{seed}:{source_id}:{row_id}".encode("utf-8")).hexdigest()


INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CAD-QA Dataset Explorer</title>
  <style>
    :root { color-scheme: light; --line:#d8dee8; --muted:#596579; --bg:#f7f8fb; --panel:#fff; --ink:#18202f; --accent:#215c9d; }
    * { box-sizing: border-box; }
    body { margin:0; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color:var(--ink); background:var(--bg); }
    header { height:56px; display:flex; align-items:center; gap:16px; padding:0 18px; border-bottom:1px solid var(--line); background:var(--panel); }
    header h1 { font-size:18px; margin:0; font-weight:650; }
    header .meta { color:var(--muted); font-size:13px; }
    main { display:grid; grid-template-columns: minmax(460px, 48%) minmax(460px, 52%); height:calc(100vh - 56px); }
    .left, .right { overflow:auto; }
    .left { border-right:1px solid var(--line); }
    .filters { position:sticky; top:0; z-index:2; padding:12px; display:grid; grid-template-columns: minmax(160px,1.6fr) minmax(110px,1fr) minmax(110px,1fr) minmax(110px,1fr) minmax(120px,.9fr) 88px; gap:8px; background:rgba(247,248,251,.96); border-bottom:1px solid var(--line); }
    input, select, button { height:34px; border:1px solid var(--line); border-radius:6px; background:white; color:var(--ink); padding:0 10px; font:inherit; font-size:13px; }
    button { cursor:pointer; background:#eef4fb; border-color:#c4d4e8; color:#123e68; font-weight:600; }
    .rows { display:flex; flex-direction:column; }
    .row { padding:12px 14px; border-bottom:1px solid var(--line); cursor:pointer; background:white; }
    .row:hover, .row.active { background:#eef5fd; }
    .row-top { display:flex; align-items:center; justify-content:space-between; gap:10px; font-size:12px; color:var(--muted); margin-bottom:6px; }
    .prompt { font-size:14px; line-height:1.35; }
    .answer { margin-top:7px; font-size:12px; color:#264f2b; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; overflow-wrap:anywhere; }
    .pillset { display:flex; flex-wrap:wrap; gap:5px; margin-top:8px; }
    .pill { padding:2px 6px; border:1px solid #d5dce8; border-radius:999px; background:#fafbfe; color:#4d5a6d; font-size:11px; }
    .pager { padding:10px 12px; display:flex; justify-content:space-between; align-items:center; border-top:1px solid var(--line); background:white; }
    .detail { padding:18px; display:grid; gap:14px; }
    .panel { background:white; border:1px solid var(--line); border-radius:8px; overflow:hidden; }
    .panel h2 { margin:0; padding:10px 12px; font-size:13px; border-bottom:1px solid var(--line); background:#fbfcfe; }
    .panel .body { padding:12px; }
    .render { min-height:360px; display:flex; align-items:center; justify-content:center; background:#fff; }
    .render img { max-width:100%; max-height:520px; object-fit:contain; }
    .kv { display:grid; grid-template-columns:160px 1fr; gap:6px 12px; font-size:13px; }
    .kv div:nth-child(odd) { color:var(--muted); }
    pre { margin:0; white-space:pre-wrap; overflow-wrap:anywhere; font-size:12px; line-height:1.35; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
    .question { font-size:15px; line-height:1.42; white-space:pre-wrap; }
    .empty { padding:24px; color:var(--muted); }
    @media (max-width: 980px) { main { grid-template-columns:1fr; height:auto; } .left { border-right:0; } }
  </style>
</head>
<body>
  <header>
    <h1>CAD-QA Dataset Explorer</h1>
    <div class="meta" id="meta"></div>
  </header>
  <main>
    <section class="left">
      <div class="filters">
        <input id="search" placeholder="Search questions, answers, source IDs">
        <select id="split"><option value="">All splits</option></select>
        <select id="target"><option value="">All targets</option></select>
        <select id="tag"><option value="">All tags</option></select>
        <select id="order"><option value="">File order</option><option value="random">Random</option></select>
        <button id="shuffle" title="Roll a new random order">Shuffle</button>
      </div>
      <div id="rows" class="rows"></div>
      <div class="pager">
        <button id="prev">Prev</button>
        <span id="page"></span>
        <button id="next">Next</button>
      </div>
    </section>
    <section class="right">
      <div id="detail" class="detail"><div class="empty">Select a row.</div></div>
    </section>
  </main>
<script>
let facets = null;
let offset = 0;
const limit = 50;
let activeRowId = null;
let randomSeed = String(Date.now());

async function getJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(await res.text());
  return await res.json();
}

function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

function params() {
  const p = new URLSearchParams();
  p.set('offset', offset);
  p.set('limit', limit);
  for (const id of ['search','split','tag','order']) {
    const v = document.getElementById(id).value;
    if (v) p.set(id, v);
  }
  if (document.getElementById('order').value === 'random') p.set('seed', randomSeed);
  const target = document.getElementById('target').value;
  if (target) p.set('target_type', target);
  return p;
}

async function loadFacets() {
  facets = await getJson('/api/facets');
  document.getElementById('meta').textContent = `${facets.row_count} rows · ${facets.source_count} sources`;
  fillSelect('split', facets.splits);
  fillSelect('target', facets.target_types);
  fillSelect('tag', facets.tags);
}

function fillSelect(id, values) {
  const select = document.getElementById(id);
  const first = select.firstElementChild;
  select.innerHTML = '';
  select.appendChild(first);
  for (const value of values) {
    const option = document.createElement('option');
    option.value = value;
    option.textContent = value;
    select.appendChild(option);
  }
}

async function loadRows() {
  const data = await getJson('/api/rows?' + params().toString());
  const root = document.getElementById('rows');
  root.innerHTML = '';
  for (const row of data.rows) {
    const el = document.createElement('div');
    el.className = 'row' + (row.row_id === activeRowId ? ' active' : '');
    el.innerHTML = `
      <div class="row-top"><span>${esc(row.split)} · ${esc(row.target_type)} · hop ${esc(row.logical_hop_count)}</span><span>${esc(row.source_id)}</span></div>
      <div class="prompt">${esc(row.prompt)}</div>
      <div class="answer">${esc(row.gold_answer)}</div>
      <div class="pillset">${row.source_feature_tags.map(t => `<span class="pill">${esc(t)}</span>`).join('')}</div>
    `;
    el.onclick = () => selectRow(row.row_id);
    root.appendChild(el);
  }
  document.getElementById('page').textContent = `${data.offset + 1}-${Math.min(data.offset + data.rows.length, data.total)} of ${data.total}`;
  document.getElementById('prev').disabled = offset <= 0;
  document.getElementById('next').disabled = offset + limit >= data.total;
}

async function selectRow(rowId) {
  activeRowId = rowId;
  const row = await getJson('/api/row?row_id=' + encodeURIComponent(rowId));
  renderDetail(row);
  await loadRows();
}

function renderDetail(row) {
  const renderUrl = '/render/' + encodeURIComponent(row.source_id) + '.png';
  document.getElementById('detail').innerHTML = `
    <div class="panel">
      <h2>Render</h2>
      <div class="render"><img src="${renderUrl}" onerror="this.replaceWith(document.createTextNode('Render failed or timed out.'))"></div>
    </div>
    <div class="panel"><h2>Question</h2><div class="body question">${esc(row.prompt)}</div></div>
    <div class="panel"><h2>Answer</h2><div class="body"><pre>${esc(row.gold_answer)}</pre></div></div>
    <div class="panel"><h2>Metadata</h2><div class="body kv">
      <div>row_id</div><div>${esc(row.row_id)}</div>
      <div>source_id</div><div>${esc(row.source_id)}</div>
      <div>source_path</div><div>${esc(row.source_path)}</div>
      <div>split</div><div>${esc(row.split)}</div>
      <div>family</div><div>${esc(row.family)}</div>
      <div>target</div><div>${esc(row.target_type)}</div>
      <div>aggregation</div><div>${esc(row.aggregation)} ${esc(row.aggregation_metric)}</div>
      <div>relations</div><div>${esc((row.relation_families || []).join(', '))}</div>
      <div>measurements</div><div>${esc((row.measurement_scopes || []).join(', '))}</div>
    </div></div>
    <div class="panel"><h2>Source Code</h2><div class="body"><pre>${esc(row.source_code)}</pre></div></div>
    <div class="panel"><h2>Query Program</h2><div class="body"><pre>${esc(JSON.stringify(row.query_program, null, 2))}</pre></div></div>
    <div class="panel"><h2>Candidate Trace</h2><div class="body"><pre>${esc(JSON.stringify(row.candidate_trace, null, 2))}</pre></div></div>
  `;
}

for (const id of ['search','split','target','tag','order']) {
  document.addEventListener('input', e => {
    if (e.target && e.target.id === id) { offset = 0; loadRows(); }
  });
}
document.getElementById('shuffle').onclick = () => {
  randomSeed = String(Date.now()) + ':' + String(Math.random());
  document.getElementById('order').value = 'random';
  offset = 0;
  loadRows();
};
document.getElementById('prev').onclick = () => { offset = Math.max(0, offset - limit); loadRows(); };
document.getElementById('next').onclick = () => { offset += limit; loadRows(); };

loadFacets().then(loadRows).catch(err => {
  document.getElementById('rows').innerHTML = `<div class="empty">${esc(err.message)}</div>`;
});
</script>
</body>
</html>
"""


if __name__ == "__main__":
    raise SystemExit(main())
