"""Shared Holodeck render output settings."""

from __future__ import annotations

from pathlib import Path
from typing import Any


HOLODECK_RENDER_FILE_FORMAT = "AVIF"
HOLODECK_RENDER_MEDIA_TYPE = "IMAGE"
DEFAULT_RESOLUTION_PERCENTAGE = 100


def configure_scene_for_holodeck_render(
    scene: Any,
    render_dir: Path,
    *,
    resolution_percentage: int = DEFAULT_RESOLUTION_PERCENTAGE,
) -> None:
    """Force Blender scene output into a Holodeck-compatible image sequence."""
    if resolution_percentage <= 0:
        raise ValueError("Resolution percentage must be a positive integer.")

    render = scene.render
    image_settings = render.image_settings
    render.filepath = str(render_dir) + "/"
    render.use_file_extension = True
    render.resolution_percentage = resolution_percentage

    try:
        if hasattr(image_settings, "media_type"):
            image_settings.media_type = HOLODECK_RENDER_MEDIA_TYPE
        image_settings.file_format = HOLODECK_RENDER_FILE_FORMAT
    except (AttributeError, TypeError, ValueError) as exc:
        raise RuntimeError(
            f"Blender does not support Holodeck's required {HOLODECK_RENDER_FILE_FORMAT} image output."
        ) from exc
