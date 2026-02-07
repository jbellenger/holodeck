"""
Blender render event handlers.
This module uses bpy but delegates business logic to ManifestGenerator.
"""
import bpy
from ..core import ManifestGenerator

_generator = ManifestGenerator()


def on_render_init(scene: bpy.types.Scene) -> None:
    """Called when render begins."""
    _generator.reset()
    print(f"[deckgen] Render initialized")


def on_render_write(scene: bpy.types.Scene) -> None:
    """Called when each frame is written."""
    frame_path = scene.render.frame_path()
    _generator.add_frame(frame_path)
    print(f"[deckgen] Recorded frame: {frame_path}")


def on_render_complete(scene: bpy.types.Scene) -> None:
    """Called when render completes."""
    fps = scene.render.fps
    markers = [v.frame for k, v in scene.timeline_markers.items()]

    manifest = _generator.generate_manifest(fps, markers)
    _generator.write_manifest(manifest)

    print(f"[deckgen] Manifest written with {len(manifest['frames'])} frames")


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
