"""
Blender render event handlers.
This module uses bpy but delegates business logic to ManifestGenerator.
"""
import bpy
from pathlib import Path
from ..core import ManifestGenerator, finalize_render_export

_generator = ManifestGenerator()
_OUTPUT_ROOT_KEY = "holodeck_output_root"


def on_render_init(scene: bpy.types.Scene) -> None:
    """Called when render begins."""
    _generator.reset()
    print(f"[holodeck] Render initialized")


def on_render_write(scene: bpy.types.Scene) -> None:
    """Called when each frame is written."""
    frame_path = scene.render.frame_path()
    _generator.add_frame(frame_path)
    print(f"[holodeck] Recorded frame: {frame_path}")


def on_render_complete(scene: bpy.types.Scene) -> None:
    """Called when render completes."""
    fps = scene.render.fps
    marker_frames = [marker.frame for marker in scene.timeline_markers]
    export_root_value = scene.get(_OUTPUT_ROOT_KEY)
    export_root = Path(export_root_value) if export_root_value else None
    manifest_path, manifest = finalize_render_export(
        _generator,
        fps=fps,
        marker_frames=marker_frames,
        frame_start=scene.frame_start,
        blend_filepath=bpy.data.filepath,
        export_root=export_root,
    )
    print(f"[holodeck] Manifest written to {manifest_path} with {len(manifest['frames'])} frames")


def register() -> None:
    """Register render handlers."""
    bpy.app.handlers.render_init.append(on_render_init)
    bpy.app.handlers.render_write.append(on_render_write)
    bpy.app.handlers.render_complete.append(on_render_complete)


def unregister() -> None:
    """Unregister render handlers."""
    handlers = [
        (bpy.app.handlers.render_init, on_render_init),
        (bpy.app.handlers.render_write, on_render_write),
        (bpy.app.handlers.render_complete, on_render_complete),
    ]
    for handler_list, callback in handlers:
        try:
            handler_list.remove(callback)
        except ValueError:
            pass
