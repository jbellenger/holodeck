"""Post-process rendered animation frames while preserving full-size sources."""

from __future__ import annotations

import json
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .exporter import DEFAULT_MANIFEST_FILENAME
from .manifest_generator import ManifestGenerator


DEFAULT_ANIMATION_SCALE_PERCENTAGE = 100
SOURCE_RENDER_DIRNAME = "render-source"


@dataclass(frozen=True)
class FrameScaleResult:
    """Summary of a source-frame scaling operation."""

    frame_count: int
    manifest_path: Path | None = None


def validate_animation_scale_percentage(scale_percentage: int) -> None:
    """Validate an animation frame post-scale percentage."""
    if scale_percentage <= 0 or scale_percentage > 100:
        raise ValueError("Animation scale percentage must be between 1 and 100.")


def source_path_for_render_path(render_path: Path, output_dir: Path) -> Path:
    """Return the mirrored source path for a rendered frame path."""
    render_path = Path(render_path)
    output_dir = Path(output_dir)
    if not render_path.is_absolute():
        render_path = output_dir / render_path
    return output_dir / SOURCE_RENDER_DIRNAME / render_path.name


def preserve_and_scale_animation_frames(
    *,
    render_frame_paths: Iterable[Path],
    output_dir: Path,
    animation_scale_pct: int,
) -> FrameScaleResult:
    """Copy full-size render outputs to render-source/, then scale render/ copies."""
    validate_animation_scale_percentage(animation_scale_pct)
    render_paths = [Path(path) for path in render_frame_paths]
    missing_frames = [path for path in render_paths if not path.is_file()]
    if missing_frames:
        raise FileNotFoundError(_format_missing_frames_message("rendered frame", missing_frames))

    for render_path in render_paths:
        source_path = source_path_for_render_path(render_path, output_dir)
        source_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(render_path, source_path)

    if animation_scale_pct < 100:
        _write_scaled_frames_from_sources(
            render_frame_paths=render_paths,
            output_dir=output_dir,
            animation_scale_pct=animation_scale_pct,
        )

    return FrameScaleResult(frame_count=len(render_paths))


def rescale_animation_frames_from_manifest(
    *,
    output_dir: Path,
    animation_scale_pct: int,
) -> FrameScaleResult:
    """Regenerate playable animation frames from render-source/ without Blender."""
    validate_animation_scale_percentage(animation_scale_pct)
    output_dir = Path(output_dir)
    manifest_path = output_dir / DEFAULT_MANIFEST_FILENAME
    if not manifest_path.is_file():
        raise FileNotFoundError(
            f"{DEFAULT_MANIFEST_FILENAME} is required to identify still/key frames for rescaling."
        )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    frame_paths = _animation_frame_paths_from_manifest(output_dir, manifest)
    _write_frames_from_sources(
        render_frame_paths=frame_paths,
        output_dir=output_dir,
        animation_scale_pct=animation_scale_pct,
    )
    _rewrite_manifest_token(manifest_path, manifest, output_dir)
    return FrameScaleResult(frame_count=len(frame_paths), manifest_path=manifest_path)


def _animation_frame_paths_from_manifest(output_dir: Path, manifest: dict[str, Any]) -> list[Path]:
    frames = [str(frame) for frame in manifest.get("frames", [])]
    still_indexes = _still_frame_indexes(manifest, len(frames))
    return [
        output_dir / frame_path
        for index, frame_path in enumerate(frames)
        if index not in still_indexes
    ]


def _still_frame_indexes(manifest: dict[str, Any], frame_count: int) -> set[int]:
    if frame_count == 0:
        return set()

    still_indexes = {0, frame_count - 1}
    still_indexes.update(
        int(marker)
        for marker in manifest.get("markers", [])
        if 0 <= int(marker) < frame_count
    )
    return still_indexes


def _write_frames_from_sources(
    *,
    render_frame_paths: Iterable[Path],
    output_dir: Path,
    animation_scale_pct: int,
) -> None:
    render_paths = [Path(path) for path in render_frame_paths]
    missing_sources = [
        source_path_for_render_path(render_path, output_dir)
        for render_path in render_paths
        if not source_path_for_render_path(render_path, output_dir).is_file()
    ]
    if missing_sources:
        raise FileNotFoundError(_format_missing_frames_message("source frame", missing_sources))

    if animation_scale_pct == 100:
        for render_path in render_paths:
            source_path = source_path_for_render_path(render_path, output_dir)
            render_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, render_path)
        return

    _write_scaled_frames_from_sources(
        render_frame_paths=render_paths,
        output_dir=output_dir,
        animation_scale_pct=animation_scale_pct,
    )


def _write_scaled_frames_from_sources(
    *,
    render_frame_paths: Iterable[Path],
    output_dir: Path,
    animation_scale_pct: int,
) -> None:
    Image = _load_pillow_image_module()
    for render_path in render_frame_paths:
        source_path = source_path_for_render_path(render_path, output_dir)
        with Image.open(source_path) as image:
            width = max(1, image.width * animation_scale_pct // 100)
            height = max(1, image.height * animation_scale_pct // 100)
            resized = image.resize((width, height), Image.Resampling.LANCZOS)
            _save_image_atomically(
                resized,
                render_path,
                image_format=image.format,
            )


def _load_pillow_image_module():
    try:
        import pillow_avif  # noqa: F401
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError(
            "Animation frame scaling requires Pillow and pillow-avif-plugin."
        ) from exc
    return Image


def _save_image_atomically(image: Any, output_path: Path, *, image_format: str | None) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix=f".{output_path.stem}-",
        suffix=output_path.suffix,
        dir=output_path.parent,
        delete=False,
    ) as temp_file:
        temp_path = Path(temp_file.name)

    try:
        image.save(temp_path, format=image_format)
        temp_path.replace(output_path)
    finally:
        temp_path.unlink(missing_ok=True)


def _rewrite_manifest_token(
    manifest_path: Path,
    manifest: dict[str, Any],
    output_dir: Path,
) -> None:
    generator = ManifestGenerator()
    for frame_path in manifest.get("frames", []):
        generator.add_frame(str(frame_path))

    refreshed = generator.generate_manifest(
        fps=int(manifest["fps"]),
        markers=[int(marker) for marker in manifest.get("markers", [])],
        root_dir=output_dir,
    )
    generator.write_manifest(refreshed, str(manifest_path))


def _format_missing_frames_message(frame_label: str, frame_paths: Iterable[Path]) -> str:
    missing_frames = list(frame_paths)
    preview = ", ".join(path.name for path in missing_frames[:3])
    if len(missing_frames) > 3:
        preview += ", ..."
    return f"Missing {len(missing_frames)} {frame_label}(s): {preview}"
