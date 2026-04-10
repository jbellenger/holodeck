"""Shared Holodeck render output settings."""

from __future__ import annotations

from pathlib import Path
from typing import Any


HOLODECK_RENDER_FILE_FORMAT = "AVIF"


def configure_scene_for_holodeck_render(scene: Any, render_dir: Path) -> None:
    """Force Blender scene output into a Holodeck-compatible image sequence."""
    render = scene.render
    render.filepath = str(render_dir) + "/"
    render.use_file_extension = True

    try:
        render.image_settings.file_format = HOLODECK_RENDER_FILE_FORMAT
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            f"Blender does not support Holodeck's required {HOLODECK_RENDER_FILE_FORMAT} image output."
        ) from exc
