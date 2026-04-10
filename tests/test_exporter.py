"""Tests for shared Holodeck export helpers."""
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "holodeck"))

from core import (
    DEFAULT_MANIFEST_FILENAME,
    finalize_render_export,
    get_render_dir,
    resolve_export_root,
)
from core.manifest_generator import ManifestGenerator


class TestResolveExportRoot:
    def test_prefers_explicit_export_root(self, tmp_path):
        export_root = resolve_export_root([], export_root=tmp_path / "artifact")
        assert export_root == tmp_path / "artifact"

    def test_uses_render_parent_when_frames_exist(self, tmp_path):
        frame_path = tmp_path / "artifact" / "render" / "0001.png"
        export_root = resolve_export_root([str(frame_path)])
        assert export_root == tmp_path / "artifact"

    def test_falls_back_to_blend_parent(self, tmp_path):
        blend_file = tmp_path / "presentation.blend"
        blend_file.touch()
        export_root = resolve_export_root([], blend_filepath=str(blend_file))
        assert export_root == tmp_path


class TestFinalizeRenderExport:
    def test_writes_manifest_at_export_root(self, tmp_path):
        generator = ManifestGenerator()
        generator.add_frame(str(tmp_path / "artifact" / "render" / "0001.png"))
        generator.add_frame(str(tmp_path / "artifact" / "render" / "0002.png"))

        manifest_path, manifest = finalize_render_export(
            generator,
            fps=24,
            marker_frames=[10, 11],
            frame_start=10,
            export_root=tmp_path / "artifact",
        )

        assert manifest_path == tmp_path / "artifact" / DEFAULT_MANIFEST_FILENAME
        assert manifest_path.exists()
        assert manifest["frames"] == ["render/0001.png", "render/0002.png"]
        assert manifest["markers"] == [0, 1]

    def test_get_render_dir(self, tmp_path):
        assert get_render_dir(tmp_path / "artifact") == tmp_path / "artifact" / "render"
