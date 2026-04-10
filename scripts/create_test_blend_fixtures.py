"""Generate Blender fixture files for Holodeck render override tests.

Run with:
    blender -b --factory-startup --python scripts/create_test_blend_fixtures.py
"""

from __future__ import annotations

from pathlib import Path

import bpy


ROOT_DIR = Path(__file__).resolve().parent.parent
FIXTURE_DIR = ROOT_DIR / "tests" / "fixtures" / "blends"


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.world = bpy.data.worlds.new("FixtureWorld")
    scene.world.color = (0.02, 0.02, 0.02)
    return scene


def configure_common_scene(scene, *, frame_start: int, frame_end: int) -> None:
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 64
    scene.render.resolution_y = 64
    scene.render.resolution_percentage = 100
    scene.render.fps = 12
    scene.frame_start = frame_start
    scene.frame_end = frame_end
    scene.timeline_markers.clear()
    scene.timeline_markers.new("Start", frame=frame_start)
    scene.timeline_markers.new("End", frame=frame_end)

    bpy.ops.mesh.primitive_cube_add(location=(0.0, 0.0, 0.0))
    cube = bpy.context.object
    cube.location.x = -1.25
    cube.keyframe_insert(data_path="location", frame=frame_start)
    cube.location.x = 1.25
    cube.keyframe_insert(data_path="location", frame=frame_end)

    bpy.ops.object.camera_add(location=(0.0, -6.0, 0.0), rotation=(1.5708, 0.0, 0.0))
    scene.camera = bpy.context.object

    bpy.ops.object.light_add(type="SUN", location=(0.0, 0.0, 4.0))
    bpy.context.object.data.energy = 2.0


def save_fixture(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(path))

    backup_path = path.with_suffix(".blend1")
    if backup_path.exists():
        backup_path.unlink()


def create_open_exr_fixture() -> None:
    scene = reset_scene()
    scene.name = "OpenExrOutput"
    configure_common_scene(scene, frame_start=1, frame_end=3)
    scene.render.use_file_extension = True
    scene.render.filepath = "//should-not-use/exr/output.exr"
    scene.render.image_settings.file_format = "OPEN_EXR"
    save_fixture(FIXTURE_DIR / "open_exr_output.blend")


def create_named_png_fixture() -> None:
    scene = reset_scene()
    scene.name = "NamedPngOutput"
    configure_common_scene(scene, frame_start=5, frame_end=6)
    scene.render.use_file_extension = True
    scene.render.filepath = "//should-not-use/stills/frame.png"
    scene.render.image_settings.file_format = "PNG"
    save_fixture(FIXTURE_DIR / "named_png_output.blend")


def main() -> None:
    create_open_exr_fixture()
    create_named_png_fixture()
    print(f"Wrote Blender fixtures to {FIXTURE_DIR}")


if __name__ == "__main__":
    main()
