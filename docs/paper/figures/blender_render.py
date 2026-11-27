"""Blender half of the paper figure: build the scene, render it, project labels.

Run through ``task_figure.py``; Blender executes this file with
``--background --factory-startup --python blender_render.py -- <scene.json>
<render.png> <projection.json>``.

The scene document is typed by :mod:`task_figure`; this file only turns it into
Blender objects. It contains no task-specific geometry.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector


def _arguments() -> tuple[Path, Path, Path]:
    if "--" not in sys.argv:
        raise SystemExit("expected -- <scene.json> <render.png> <projection.json>")
    values = sys.argv[sys.argv.index("--") + 1 :]
    if len(values) != 3:
        raise SystemExit("expected -- <scene.json> <render.png> <projection.json>")
    return Path(values[0]), Path(values[1]), Path(values[2])


def _clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.materials,
        bpy.data.lights,
        bpy.data.cameras,
    ):
        for block in list(datablocks):
            if block.users == 0:
                datablocks.remove(block)


def _material(
    name: str, color: tuple[float, float, float], roughness: float = 0.45
) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.diffuse_color = (*color, 1.0)
    nodes = material.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Metallic"].default_value = 0.0
        bsdf.inputs["Roughness"].default_value = roughness
        for input_name in ("Specular IOR Level", "Specular"):
            if input_name in bsdf.inputs:
                bsdf.inputs[input_name].default_value = 0.25
                break
    return material


def _mesh_part(part: dict, material: bpy.types.Material) -> None:
    mesh = bpy.data.meshes.new(part["name"])
    mesh.from_pydata(part["vertices"], [], part["triangles"])
    mesh.validate()
    mesh.update()
    for polygon in mesh.polygons:
        polygon.use_smooth = part["smooth"]
    obj = bpy.data.objects.new(part["name"], mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)


def _edge_group(group: dict, material: bpy.types.Material) -> None:
    curve = bpy.data.curves.new(group["name"], "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 1
    curve.bevel_depth = group["radius"]
    curve.bevel_resolution = 3
    curve.use_fill_caps = True
    for start, end in group["segments"]:
        spline = curve.splines.new("POLY")
        spline.points.add(1)
        spline.points[0].co = (*start, 1.0)
        spline.points[1].co = (*end, 1.0)
    obj = bpy.data.objects.new(group["name"], curve)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)


def _camera(
    scene: bpy.types.Scene, spec: dict, bounds_min: Vector, bounds_max: Vector
) -> bpy.types.Object:
    centre = (bounds_min + bounds_max) / 2
    extent = max(bounds_max - bounds_min)
    direction = Vector(spec["camera"]["direction"]).normalized()
    camera_data = bpy.data.cameras.new("Camera")
    camera_data.type = "ORTHO"
    camera = bpy.data.objects.new("Camera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.location = centre + direction * (extent * 4.0)
    camera.rotation_euler = (-direction).to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()

    inverse = camera.matrix_world.inverted()
    xs: list[float] = []
    ys: list[float] = []
    for x in (bounds_min.x, bounds_max.x):
        for y in (bounds_min.y, bounds_max.y):
            for z in (bounds_min.z, bounds_max.z):
                point = inverse @ Vector((x, y, z))
                xs.append(point.x)
                ys.append(point.y)
    width = max(xs) - min(xs)
    height = max(ys) - min(ys)
    aspect = spec["render"]["width"] / spec["render"]["height"]
    camera_data.ortho_scale = (
        max(width, height * aspect) * spec["camera"]["ortho_margin"]
    )
    return camera


def _workbench(scene: bpy.types.Scene) -> None:
    """Flat technical shading: no lights, no shadows, dark outlines."""

    shading = scene.display.shading
    shading.light = "FLAT"
    shading.color_type = "MATERIAL"
    shading.show_shadows = False
    shading.show_cavity = True
    shading.cavity_type = "BOTH"
    shading.show_object_outline = True
    shading.object_outline_color = (0.12, 0.14, 0.18)
    shading.background_type = "VIEWPORT"
    shading.background_color = (1.0, 1.0, 1.0)


def _render_settings(scene: bpy.types.Scene, spec: dict, render_path: Path) -> None:
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.render_aa = "16"
    scene.render.film_transparent = False
    scene.render.resolution_x = spec["render"]["width"]
    scene.render.resolution_y = spec["render"]["height"]
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.filepath = str(render_path)
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0.0


def _projections(
    scene: bpy.types.Scene, camera: bpy.types.Object, spec: dict
) -> list[dict]:
    width = spec["render"]["width"]
    height = spec["render"]["height"]
    rows: list[dict] = []
    for label in spec["labels"]:
        coordinate = world_to_camera_view(scene, camera, Vector(label["position"]))
        rows.append(
            {
                "text": label["text"],
                "kind": label["kind"],
                "color": label["color"],
                "x": coordinate.x * width,
                "y": (1.0 - coordinate.y) * height,
                "depth": coordinate.z,
            }
        )
    return rows


def main() -> int:
    scene_path, render_path, projection_path = _arguments()
    spec = json.loads(scene_path.read_text(encoding="utf-8"))

    _clear_scene()
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 0.001

    for part in spec["parts"]:
        _mesh_part(part, _material(part["name"], tuple(part["color"]), 0.42))
    for group in spec["edge_groups"]:
        _edge_group(group, _material(group["name"], tuple(group["color"]), 0.35))

    bounds_min = Vector(spec["bounds_min"])
    bounds_max = Vector(spec["bounds_max"])
    camera = _camera(scene, spec, bounds_min, bounds_max)
    _workbench(scene)
    _render_settings(scene, spec, render_path)

    bpy.ops.render.render(write_still=True)

    projection_path.write_text(
        json.dumps(_projections(scene, camera, spec), indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
