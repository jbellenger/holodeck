"""Shared Holodeck render output settings."""

from __future__ import annotations

from pathlib import Path
from typing import Any


HOLODECK_RENDER_FILE_FORMAT = "AVIF"
HOLODECK_RENDER_MEDIA_TYPE = "IMAGE"
DEFAULT_RESOLUTION_PERCENTAGE = 100
RENDER_ENGINE_CHOICES = ("eevee", "cycles", "workbench")
RENDER_ENGINE_IDS = {
    "eevee": ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"),
    "cycles": ("CYCLES",),
    "workbench": ("BLENDER_WORKBENCH",),
}


def configure_scene_for_holodeck_render(
    scene: Any,
    render_dir: Path,
    *,
    resolution_percentage: int = DEFAULT_RESOLUTION_PERCENTAGE,
    render_engine: str | None = None,
) -> None:
    """Force Blender scene output into a Holodeck-compatible image sequence."""
    if resolution_percentage <= 0:
        raise ValueError("Resolution percentage must be a positive integer.")
    if render_engine is not None:
        _apply_render_engine_override(scene, render_engine)

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


def _apply_render_engine_override(scene: Any, render_engine: str) -> None:
    if render_engine not in RENDER_ENGINE_IDS:
        choices = ", ".join(RENDER_ENGINE_CHOICES)
        raise ValueError(f"Render engine must be one of: {choices}.")

    render = scene.render
    for engine_id in RENDER_ENGINE_IDS[render_engine]:
        try:
            render.engine = engine_id
        except (AttributeError, TypeError, ValueError):
            continue
        return

    raise RuntimeError(f"Blender does not support the requested render engine: {render_engine}.")
