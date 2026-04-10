"""Tests for shared Holodeck export helpers."""
from pathlib import Path

from holodeck.core import (
    DEFAULT_MANIFEST_FILENAME,
    build_manifest_from_frames,
    finalize_render_export,
    get_render_dir,
    resolve_export_root,
    write_manifest_from_frames,
)
from holodeck.core.manifest_generator import ManifestGenerator


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
        assert "token" in manifest

    def test_get_render_dir(self, tmp_path):
        assert get_render_dir(tmp_path / "artifact") == tmp_path / "artifact" / "render"


class TestWriteManifestFromFrames:
    def test_build_manifest_from_frames_uses_frame_start_for_markers(self, tmp_path):
        manifest = build_manifest_from_frames(
            frame_paths=[
                str(tmp_path / "artifact" / "render" / "0001.png"),
                str(tmp_path / "artifact" / "render" / "0002.png"),
            ],
            fps=30,
            marker_frames=[100, 101, 105],
            frame_start=100,
            export_root=tmp_path / "artifact",
        )

        assert manifest["frames"] == ["render/0001.png", "render/0002.png"]
        assert manifest["markers"] == [0, 1]
        assert "token" in manifest

    def test_write_manifest_from_frames_creates_manifest(self, tmp_path):
        manifest_path, manifest = write_manifest_from_frames(
            frame_paths=[
                str(tmp_path / "artifact" / "render" / "0001.png"),
                str(tmp_path / "artifact" / "render" / "0002.png"),
            ],
            fps=24,
            marker_frames=[10, 11],
            frame_start=10,
            export_root=tmp_path / "artifact",
        )

        assert manifest_path == tmp_path / "artifact" / DEFAULT_MANIFEST_FILENAME
        assert manifest_path.exists()
        assert manifest["frames"] == ["render/0001.png", "render/0002.png"]
        assert "token" in manifest
