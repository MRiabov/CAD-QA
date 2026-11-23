"""Local task browser for one release table.

The browser serves the JSON API the Vite+ app in ``task-browser/`` reads, and
serves the built app when ``task-browser/dist`` exists. It reads one
``release.parquet``, paginates the task list, and tessellates a task's final
solid state on demand. One tessellation is cached per program, so tasks that
share a program share a scene.

Run the API and the Vite dev server separately while developing::

    uv run python tools/manual-verification/task_browser.py \
        --release runs/run0001/05-validate-and-export-release/current

    cd tools/manual-verification/task-browser && pnpm dev

For a single-command review, build the app once and open the API origin::

    cd tools/manual-verification/task-browser && pnpm build
    uv run python tools/manual-verification/task_browser.py --release ...

This is a manual-verification devtool. The generator never imports it.
"""

from __future__ import annotations

import argparse
import json
import logging
import mimetypes
import random
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, override
from urllib.parse import parse_qs, unquote, urlparse

from task_release import (
    Facets,
    TaskDetail,
    TaskPage,
    detail,
    execute_program,
    load_rows,
    program_text,
    release_table_path,
    summary,
)
from task_scene import SCENE_VERSION, ScenePayload, scene_from_shape

LOGGER = logging.getLogger("cadqa.task_browser")
MAX_PAGE_SIZE = 200

FALLBACK_HTML = """<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>CAD-QA task browser</title></head>
<body style="font-family:system-ui;padding:2rem;max-width:46rem">
<h1>Task browser is not built</h1>
<p>The API is running, but <code>task-browser/dist</code> does not exist.</p>
<p>Build it once with <code>pnpm install &amp;&amp; pnpm build</code> in
<code>tools/manual-verification/task-browser</code>, then reload.</p>
<p>For live development run <code>pnpm dev</code> in the same folder and open
the Vite URL. The API is under <code>/api</code>.</p>
</body>
</html>
"""


class BadRequest(ValueError):
    """A request parameter is outside its allowed form."""


class ReleaseIndex:
    """One release table, its task list, and its scene cache."""

    def __init__(self, table_path: Path, cache_dir: Path) -> None:
        self.table_path = table_path
        self.cache_dir = cache_dir
        self.rows = load_rows(table_path)
        self.by_id = {row.task_id: row for row in self.rows}
        self.scene_lock = threading.Lock()
        self.facets = Facets(
            task_count=len(self.rows),
            splits=sorted({str(row.split) for row in self.rows}),
            subsets=sorted({str(row.subset) for row in self.rows}),
            target_categories=sorted({row.target_category for row in self.rows}),
            answer_meanings=sorted({row.answer_meaning for row in self.rows}),
        )

    def page(
        self,
        *,
        offset: int,
        limit: int,
        search: str,
        split: str,
        subset: str,
        target_category: str,
        answer_meaning: str,
        order: str,
        seed: str,
    ) -> TaskPage:
        """Filter, order, and slice the task list."""

        rows = self.rows
        if search:
            needle = search.lower()
            rows = [
                row
                for row in rows
                if needle in row.prompt.lower()
                or needle in row.task_id.lower()
                or needle in row.program_id.lower()
            ]
        if split:
            rows = [row for row in rows if row.split == split]
        if subset:
            rows = [row for row in rows if row.subset == subset]
        if target_category:
            rows = [row for row in rows if row.target_category == target_category]
        if answer_meaning:
            rows = [row for row in rows if row.answer_meaning == answer_meaning]
        if order == "random":
            rows = list(rows)
            random.Random(seed).shuffle(rows)
        total = len(rows)
        window = rows[offset : offset + limit]
        return TaskPage(
            total=total,
            offset=offset,
            limit=limit,
            tasks=[summary(row) for row in window],
        )

    def detail(self, task_id: str) -> TaskDetail:
        """The detail payload for one task."""

        row = self.by_id.get(task_id)
        if row is None:
            raise KeyError(task_id)
        return detail(row)

    def scene(self, task_id: str) -> ScenePayload:
        """The tessellated final solid state, cached by program."""

        row = self.by_id.get(task_id)
        if row is None:
            raise KeyError(task_id)
        cache_path = self.cache_dir / f"{row.program_sha256}-v{SCENE_VERSION}.json"
        if cache_path.exists():
            return ScenePayload.model_validate_json(
                cache_path.read_text(encoding="utf-8")
            )
        with self.scene_lock:
            if cache_path.exists():
                return ScenePayload.model_validate_json(
                    cache_path.read_text(encoding="utf-8")
                )
            shape = execute_program(program_text(row.prompt))
            payload = scene_from_shape(shape)
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = cache_path.with_suffix(".tmp")
            temporary.write_text(payload.model_dump_json(), encoding="utf-8")
            temporary.replace(cache_path)
            return payload


def _int_param(query: dict[str, list[str]], name: str, default: int) -> int:
    raw = query.get(name, [""])[0] or str(default)
    try:
        return int(raw)
    except ValueError as error:
        raise BadRequest(f"{name} must be an integer") from error


def _str_param(query: dict[str, list[str]], name: str, default: str = "") -> str:
    return query.get(name, [default])[0] or default


class TaskBrowserHandler(BaseHTTPRequestHandler):
    """The JSON API and the static app."""

    server_version = "CADQATaskBrowser/1"
    index: ReleaseIndex
    web_dist: Path

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        try:
            if path == "/api/facets":
                self._send_json(self.index.facets.model_dump())
            elif path == "/api/tasks":
                self._send_json(self._tasks(parse_qs(parsed.query)).model_dump())
            elif path.startswith("/api/tasks/") and path.endswith("/scene"):
                task_id = path[len("/api/tasks/") : -len("/scene")]
                self._send_json(self.index.scene(task_id).model_dump())
            elif path.startswith("/api/tasks/"):
                task_id = path[len("/api/tasks/") :]
                self._send_json(self.index.detail(task_id).model_dump())
            else:
                self._serve_static(path)
        except BadRequest as error:
            self._send_error(HTTPStatus.BAD_REQUEST, str(error))
        except KeyError:
            self._send_error(HTTPStatus.NOT_FOUND, "task not found")
        except Exception as error:
            LOGGER.exception("request failed: %s", path)
            self._send_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(error))

    def _tasks(self, query: dict[str, list[str]]) -> TaskPage:
        limit = _int_param(query, "limit", 50)
        limit = max(1, min(limit, MAX_PAGE_SIZE))
        offset = max(0, _int_param(query, "offset", 0))
        return self.index.page(
            offset=offset,
            limit=limit,
            search=_str_param(query, "search"),
            split=_str_param(query, "split"),
            subset=_str_param(query, "subset"),
            target_category=_str_param(query, "target_category"),
            answer_meaning=_str_param(query, "answer_meaning"),
            order=_str_param(query, "order", "file"),
            seed=_str_param(query, "seed", "0"),
        )

    def _serve_static(self, path: str) -> None:
        root = self.web_dist.resolve()
        if not root.is_dir():
            self._send_html(FALLBACK_HTML)
            return
        relative = path.lstrip("/") or "index.html"
        candidate = (root / relative).resolve()
        if not candidate.is_relative_to(root) or not candidate.is_file():
            if path.startswith("/assets/") or Path(path).suffix:
                self._send_error(HTTPStatus.NOT_FOUND, "file not found")
                return
            candidate = root / "index.html"
        if not candidate.is_file():
            self._send_error(HTTPStatus.NOT_FOUND, "app not built")
            return
        content_type = (
            mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        )
        self._send_bytes(candidate.read_bytes(), content_type)

    def _send_json(self, value: Any, *, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(value, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, value: str) -> None:
        self._send_bytes(value.encode("utf-8"), "text/html; charset=utf-8")

    def _send_bytes(self, body: bytes, content_type: str) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, status: HTTPStatus, message: str) -> None:
        self._send_json({"error": message}, status=status)

    @override
    def log_message(self, format: str, *args: Any) -> None:
        LOGGER.info("%s - %s", self.address_string(), format % args)


def build_handler(index: ReleaseIndex, web_dist: Path) -> type[TaskBrowserHandler]:
    """Bind one release index and web build to a handler class."""

    return type(
        "BoundTaskBrowserHandler",
        (TaskBrowserHandler,),
        {"index": index, "web_dist": web_dist},
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--release",
        required=True,
        type=Path,
        help="release directory, current symlink, or release.parquet",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path("runs/manual_verification/task_browser/cache"),
        help="scene cache; one JSON per program",
    )
    parser.add_argument(
        "--web-dist",
        type=Path,
        default=Path(__file__).with_name("task-browser") / "dist",
        help="built Vite+ app to serve",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    table_path = release_table_path(args.release)
    index = ReleaseIndex(table_path, args.cache_dir)
    server = ThreadingHTTPServer(
        (args.host, args.port), build_handler(index, args.web_dist)
    )
    url = f"http://{args.host}:{server.server_port}"
    built = "built" if args.web_dist.is_dir() else "not built; run pnpm build"
    print(f"Serving CAD-QA task browser at {url}")
    print(f"Release table: {table_path}")
    print(f"Rows: {len(index.rows)}")
    print(f"Scene cache: {args.cache_dir}")
    print(f"Web app: {args.web_dist} ({built})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping task browser")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
