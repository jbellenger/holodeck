"""Blender-backed integration tests for render setting overrides."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from holodeck.core.blender import extract_blend_metadata, render_blend


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "blends"
BLENDER_PATH = shutil.which("blender")


pytestmark = pytest.mark.skipif(BLENDER_PATH is None, reason="Blender is required for integration tests")


def copy_blend_fixture(name: str, tmp_path: Path) -> Path:
    source = FIXTURE_DIR / name
    destination = tmp_path / name
    shutil.copyfile(source, destination)
    return destination


class TestBlenderRenderOverrides:
    def test_render_blend_overrides_saved_openexr_output(self, tmp_path):
        blend_file = copy_blend_fixture("open_exr_output.blend", tmp_path)
        output_dir = tmp_path / "render-output"

        render_blend(blend_file=blend_file, output_dir=output_dir, blender_executable=BLENDER_PATH)

        render_dir = output_dir / "render"
        rendered_frames = sorted(render_dir.glob("*.avif"))

        assert len(rendered_frames) == 3
        assert not list(render_dir.glob("*.exr"))
        assert not (tmp_path / "should-not-use").exists()

    def test_render_blend_with_frames_writes_numbered_output(self, tmp_path):
        blend_file = copy_blend_fixture("open_exr_output.blend", tmp_path)
        output_dir = tmp_path / "render-output"

        render_blend(
            blend_file=blend_file,
            output_dir=output_dir,
            blender_executable=BLENDER_PATH,
            frames="1,3",
        )

        render_dir = output_dir / "render"
        rendered_frames = sorted(p.name for p in render_dir.glob("*.avif"))

        assert rendered_frames == ["0001.avif", "0003.avif"]

    def test_extract_blend_metadata_uses_holodeck_render_paths(self, tmp_path):
        blend_file = copy_blend_fixture("named_png_output.blend", tmp_path)
        output_dir = tmp_path / "metadata-output"

        metadata = extract_blend_metadata(
            blend_file=blend_file,
            output_dir=output_dir,
            blender_executable=BLENDER_PATH,
        )

        expected_render_dir = output_dir / "render"

        assert metadata.frame_start == 5
        assert metadata.frame_end == 6
        assert metadata.marker_frames == [5, 6]
        assert len(metadata.frame_paths) == 2
        assert all(path.endswith(".avif") for path in metadata.frame_paths)
        assert all(Path(path).parent == expected_render_dir for path in metadata.frame_paths)
