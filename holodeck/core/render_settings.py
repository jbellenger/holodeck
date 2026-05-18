"""Shared Holodeck render output settings."""

from __future__ import annotations

from pathlib import Path
from typing import Any


HOLODECK_RENDER_FILE_FORMAT = "AVIF"
HOLODECK_RENDER_MEDIA_TYPE = "IMAGE"
DEFAULT_ANIMATION_RESOLUTION_PERCENTAGE = 100
DEFAULT_STILL_RESOLUTION_PERCENTAGE = 100
DEFAULT_RESOLUTION_PERCENTAGE = DEFAULT_STILL_RESOLUTION_PERCENTAGE
RENDERER_CHOICES = ("eevee", "cycles", "workbench")
RENDERER_IDS = {
    "eevee": ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"),
    "cycles": ("CYCLES",),
    "workbench": ("BLENDER_WORKBENCH",),
}


def configure_scene_for_holodeck_render(
    scene: Any,
    render_dir: Path,
    *,
    resolution_percentage: int = DEFAULT_RESOLUTION_PERCENTAGE,
    renderer: str | None = None,
) -> None:
    """Force Blender scene output into a Holodeck-compatible image sequence."""
    if resolution_percentage <= 0:
        raise ValueError("Resolution percentage must be a positive integer.")
    if renderer is not None:
        _apply_renderer_override(scene, renderer)

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


def _apply_renderer_override(scene: Any, renderer: str) -> None:
    if renderer not in RENDERER_IDS:
        choices = ", ".join(RENDERER_CHOICES)
        raise ValueError(f"Renderer must be one of: {choices}.")

    render = scene.render
    for engine_id in RENDERER_IDS[renderer]:
        try:
            render.engine = engine_id
        except (AttributeError, TypeError, ValueError):
            continue
        return

    raise RuntimeError(f"Blender does not support the requested renderer: {renderer}.")
