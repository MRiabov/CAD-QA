"""Render the paper's example CAD-QA task as a reproducible figure.

The geometry comes from :mod:`figure_scene`; Blender renders the scene
offscreen; Pillow lays the question beside the render and draws the clue
badges. The 3D picture is Blender's, not a renderer in this repository.

Run from the repository root with the ``cadquery`` extra installed::

    uv run --extra cadquery python docs/paper/figures/task_figure.py

Requirements: CadQuery 2.8+, Blender 5.x on ``PATH``, Pillow 12+.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from figure_scene import FigureError, FigureSpec, build_figure, load_oracle
from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parents[3]
ORACLE_DIR = (
    REPO_ROOT / "docs/dataset/implementation/pipeline/testing/oracles/task-construction"
)
DEFAULT_OUT = REPO_ROOT / "docs/paper/figures/task-example.png"
WORK_ROOT = REPO_ROOT / "runs/manual_verification/paper_figure"
BLENDER_SCRIPT = Path(__file__).with_name("blender_render.py")

FIGURE_WIDTH = 1890
FIGURE_HEIGHT = 680
TEXT_WIDTH = 960
LEGEND_HEIGHT = 64
DPI = 300

FONT_DIR = Path("/usr/share/fonts/truetype")
SANS_REGULAR = FONT_DIR / "noto/NotoSans-Regular.ttf"
SANS_BOLD = FONT_DIR / "noto/NotoSans-Bold.ttf"
MONO_REGULAR = FONT_DIR / "dejavu/DejaVuSansMono.ttf"


def _font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    if not path.is_file():
        raise FigureError(f"font does not exist: {path}")
    return ImageFont.truetype(str(path), size)


def _css(color: tuple[float, float, float]) -> tuple[int, int, int]:
    return tuple(round(channel * 255) for channel in color)


def _wrap(
    draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, width: int
) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = word if not current else f"{current} {word}"
        if draw.textlength(candidate, font=font) <= width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _draw_tracked(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int],
    tracking: int,
) -> None:
    x, y = xy
    for character in text:
        draw.text((x, y), character, font=font, fill=fill)
        x += int(draw.textlength(character, font=font)) + tracking


def _arrow(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    color: tuple[int, int, int],
) -> None:
    """A short right arrow, drawn rather than typed so it needs no glyph."""

    draw.line((x, y, x + 17, y), fill=color, width=2)
    draw.polygon(((x + 16, y - 6), (x + 24, y), (x + 16, y + 6)), fill=color)


def _badge(
    draw: ImageDraw.ImageDraw,
    centre: tuple[int, int],
    text: str,
    color: tuple[int, int, int],
    radius: int,
    font: ImageFont.FreeTypeFont,
) -> None:
    x, y = centre
    draw.ellipse(
        (x - radius + 2, y - radius + 4, x + radius + 2, y + radius + 4),
        fill=(0, 0, 0, 45),
    )
    draw.ellipse(
        (x - radius, y - radius, x + radius, y + radius),
        fill=color,
        outline=(255, 255, 255),
        width=max(3, radius // 5),
    )
    draw.text((x, y), text, font=font, fill=(255, 255, 255), anchor="mm")


def compose(
    figure: FigureSpec, render_path: Path, projection_path: Path, out_path: Path
) -> None:
    panel = figure.panel
    render = Image.open(render_path).convert("RGBA")
    projections = json.loads(projection_path.read_text(encoding="utf-8"))

    canvas = Image.new("RGB", (FIGURE_WIDTH, FIGURE_HEIGHT), (255, 255, 255))
    draw = ImageDraw.Draw(canvas, "RGBA")

    pane_width = FIGURE_WIDTH - TEXT_WIDTH
    pane_height = FIGURE_HEIGHT
    render = render.resize((pane_width, pane_height), Image.Resampling.LANCZOS)
    canvas.paste(render, (TEXT_WIDTH, 0), render)
    draw.line(
        ((TEXT_WIDTH, 0), (TEXT_WIDTH, FIGURE_HEIGHT)),
        fill=(229, 231, 235),
        width=2,
    )

    eyebrow = _font(SANS_BOLD, 22)
    question = _font(SANS_BOLD, 46)
    clue_font = _font(SANS_REGULAR, 46)
    badge_font = _font(SANS_BOLD, 22)
    answer_label = _font(SANS_BOLD, 22)
    answer_font = _font(SANS_BOLD, 48)
    legend_label = _font(SANS_BOLD, 24)
    legend_detail = _font(SANS_REGULAR, 22)

    left = 36
    _draw_tracked(draw, (left, 36), panel.eyebrow.upper(), eyebrow, (107, 114, 128), 3)
    draw.text((left, 74), panel.question, font=question, fill=(17, 24, 39))

    y = 160
    for clue in panel.clues:
        color = _css(clue.color)
        _badge(draw, (left + 22, y + 20), str(clue.order), color, 22, badge_font)
        text_x = left + 56
        text_width = TEXT_WIDTH - text_x - left
        for line in _wrap(draw, clue.statement, clue_font, text_width):
            draw.text((text_x, y), line, font=clue_font, fill=(55, 65, 81))
            y += 58
        y += 16

    answer_top = 500
    draw.rounded_rectangle(
        (left, answer_top, TEXT_WIDTH - left, answer_top + 88),
        radius=10,
        fill=(248, 249, 251),
        outline=(229, 231, 235),
        width=1,
    )
    draw.text(
        (left + 22, answer_top + 44),
        panel.answer_label.upper(),
        font=answer_label,
        fill=(107, 114, 128),
        anchor="lm",
    )
    draw.text(
        (TEXT_WIDTH - left - 22, answer_top + 44),
        panel.answer,
        font=answer_font,
        fill=(17, 24, 39),
        anchor="rm",
    )

    legend_y = 606
    x = left
    for entry in figure.scene.legend:
        color = _css(entry.color)
        draw.ellipse((x, legend_y + 6, x + 16, legend_y + 22), fill=color)
        draw.text((x + 26, legend_y), entry.label, font=legend_label, fill=(17, 24, 39))
        draw.text(
            (x + 26, legend_y + 28),
            entry.detail,
            font=legend_detail,
            fill=(107, 114, 128),
        )
        x += (
            26
            + max(
                int(draw.textlength(entry.label, font=legend_label)),
                int(draw.textlength(entry.detail, font=legend_detail)),
            )
            + 40
        )

    scale_x = pane_width / figure.scene.render.width
    scale_y = pane_height / figure.scene.render.height
    for projection in projections:
        centre = (
            TEXT_WIDTH + round(projection["x"] * scale_x),
            round(projection["y"] * scale_y),
        )
        kind = projection["kind"]
        radius = 24 if kind == "target" else 22
        _badge(
            draw,
            centre,
            projection["text"],
            _css(tuple(projection["color"])),
            radius,
            _font(SANS_BOLD, 18),
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path, dpi=(DPI, DPI))


def run_blender(scene_path: Path, render_path: Path, projection_path: Path) -> None:
    command = [
        "blender",
        "--background",
        "--factory-startup",
        "--python",
        str(BLENDER_SCRIPT),
        "--",
        str(scene_path),
        str(render_path),
        str(projection_path),
    ]
    subprocess.run(command, check=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--oracle",
        default="box-with-hole-edge-length",
        help="gold oracle slug (default: box-with-hole-edge-length)",
    )
    parser.add_argument(
        "--oracles",
        type=Path,
        default=ORACLE_DIR,
        help="directory of gold oracle records",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help="final PNG path",
    )
    parser.add_argument(
        "--work",
        type=Path,
        default=WORK_ROOT,
        help="intermediate scene, render, and projection directory",
    )
    parser.add_argument(
        "--skip-blender",
        action="store_true",
        help="reuse an existing render and projection",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    oracle = load_oracle(args.oracles, args.oracle)
    figure = build_figure(oracle)

    work = args.work / oracle.slug
    work.mkdir(parents=True, exist_ok=True)
    scene_path = work / "scene.json"
    render_path = work / "render.png"
    projection_path = work / "projection.json"
    scene_path.write_text(
        figure.scene.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )

    if not args.skip_blender:
        run_blender(scene_path, render_path, projection_path)
    compose(figure, render_path, projection_path, args.out)
    print(f"figure: {args.out}")
    print(f"scene:  {scene_path}")
    print(f"render: {render_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
