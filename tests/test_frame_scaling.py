"""Tests for mirrored source frame scaling."""

import json
from pathlib import Path

import pytest

import pillow_avif  # noqa: F401
from PIL import Image

from holodeck.core.frame_scaling import (
    preserve_and_scale_animation_frames,
    rescale_animation_frames_from_manifest,
    source_path_for_render_path,
)


def write_avif(path: Path, *, size=(10, 6), color=(30, 100, 180)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", size, color)
    image.save(path, format="AVIF")


def read_size(path: Path) -> tuple[int, int]:
    with Image.open(path) as image:
        return image.size


def write_manifest(output_dir: Path, *, frames: list[str], markers: list[int]) -> str | None:
    manifest = {
        "fps": 24,
        "markers": markers,
        "frames": frames,
        "token": "old-token",
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest["token"]


def test_source_path_mirrors_render_filename(tmp_path):
    output_dir = tmp_path / "dist"

    assert (
        source_path_for_render_path(output_dir / "render" / "0007.avif", output_dir)
        == output_dir / "render-source" / "0007.avif"
    )
    assert (
        source_path_for_render_path(Path("render/0008.avif"), output_dir)
        == output_dir / "render-source" / "0008.avif"
    )


def test_preserve_and_scale_animation_frames_from_render_outputs(tmp_path):
    output_dir = tmp_path / "dist"
    render_frame = output_dir / "render" / "0002.avif"
    write_avif(render_frame, size=(10, 6))

    result = preserve_and_scale_animation_frames(
        render_frame_paths=[render_frame],
        output_dir=output_dir,
        animation_scale_pct=50,
    )

    assert result.frame_count == 1
    assert read_size(output_dir / "render-source" / "0002.avif") == (10, 6)
    assert read_size(render_frame) == (5, 3)


def test_rescale_restores_from_source_with_byte_copy(tmp_path):
    output_dir = tmp_path / "dist"
    render_dir = output_dir / "render"
    source_dir = output_dir / "render-source"
    render_dir.mkdir(parents=True)
    source_dir.mkdir(parents=True)
    frames = [
        "render/0001.avif",
        "render/0002.avif",
        "render/0003.avif",
        "render/0004.avif",
    ]
    for frame in frames:
        (output_dir / frame).write_bytes(f"render-{frame}".encode("utf-8"))
    (source_dir / "0002.avif").write_bytes(b"full-size-animation-frame")
    old_token = write_manifest(output_dir, frames=frames, markers=[2])

    result = rescale_animation_frames_from_manifest(
        output_dir=output_dir,
        animation_scale_pct=100,
    )

    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert result.frame_count == 1
    assert (render_dir / "0002.avif").read_bytes() == b"full-size-animation-frame"
    assert (render_dir / "0001.avif").read_bytes() == b"render-render/0001.avif"
    assert manifest["token"] != old_token
    assert manifest["frames"] == frames
    assert manifest["markers"] == [2]


def test_rescale_scales_from_source_and_skips_still_key_frames(tmp_path):
    output_dir = tmp_path / "dist"
    render_dir = output_dir / "render"
    source_dir = output_dir / "render-source"
    frames = [
        "render/0001.avif",
        "render/0002.avif",
        "render/0003.avif",
    ]
    write_avif(render_dir / "0001.avif", size=(12, 8))
    write_avif(render_dir / "0002.avif", size=(12, 8))
    write_avif(render_dir / "0003.avif", size=(12, 8))
    write_avif(source_dir / "0002.avif", size=(12, 8), color=(200, 50, 50))
    write_manifest(output_dir, frames=frames, markers=[])

    result = rescale_animation_frames_from_manifest(
        output_dir=output_dir,
        animation_scale_pct=50,
    )

    assert result.frame_count == 1
    assert read_size(render_dir / "0001.avif") == (12, 8)
    assert read_size(render_dir / "0002.avif") == (6, 4)
    assert read_size(render_dir / "0003.avif") == (12, 8)


def test_rescale_fails_without_manifest(tmp_path):
    output_dir = tmp_path / "dist"
    output_dir.mkdir()

    with pytest.raises(FileNotFoundError, match="manifest.json is required"):
        rescale_animation_frames_from_manifest(
            output_dir=output_dir,
            animation_scale_pct=50,
        )


def test_rescale_fails_when_source_frames_are_missing(tmp_path):
    output_dir = tmp_path / "dist"
    render_dir = output_dir / "render"
    frames = [
        "render/0001.avif",
        "render/0002.avif",
        "render/0003.avif",
    ]
    render_dir.mkdir(parents=True)
    for frame in frames:
        (output_dir / frame).write_bytes(b"render")
    write_manifest(output_dir, frames=frames, markers=[])

    with pytest.raises(FileNotFoundError, match="Missing 1 source frame"):
        rescale_animation_frames_from_manifest(
            output_dir=output_dir,
            animation_scale_pct=100,
        )
