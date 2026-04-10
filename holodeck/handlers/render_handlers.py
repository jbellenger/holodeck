"""
Blender render event handlers.
This module uses bpy but delegates business logic to ManifestGenerator.
"""
import bpy
from pathlib import Path
from ..core import ManifestGenerator

_generator = ManifestGenerator()


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
    markers = _generator.normalize_markers(marker_frames, scene.frame_start)

    manifest = _generator.generate_manifest(fps, markers)

    # Write manifest next to the rendered frames
    if _generator.frames:
        first_frame = Path(_generator.frames[0])
        manifest_path = first_frame.parent / "manifest.json"
    else:
        # Fallback: write next to blend file
        manifest_path = Path(bpy.data.filepath).parent / "manifest.json"

    _generator.write_manifest(manifest, str(manifest_path))
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
