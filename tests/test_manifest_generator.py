"""
Unit tests for manifest generator (no Blender required).
Run with: pytest tests/
"""
import json
import tempfile
from pathlib import Path

import pytest

from holodeck.core.manifest_generator import ManifestGenerator


class TestManifestGenerator:
    """Tests for pure business logic."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = ManifestGenerator()

    def test_add_frame(self):
        """Test adding a single frame."""
        self.generator.add_frame("/path/to/render/0001.png")
        assert len(self.generator.frames) == 1
        assert self.generator.frames[0] == "/path/to/render/0001.png"

    def test_add_multiple_frames(self):
        """Test adding multiple frames preserves order."""
        paths = [
            "/path/to/render/0001.png",
            "/path/to/render/0002.png",
            "/path/to/render/0003.png",
        ]
        for path in paths:
            self.generator.add_frame(path)

        assert self.generator.frames == paths

    def test_add_none_frame_ignored(self):
        """None paths should be ignored."""
        self.generator.add_frame(None)
        assert len(self.generator.frames) == 0

    def test_add_empty_frame_ignored(self):
        """Empty string paths should be ignored."""
        self.generator.add_frame("")
        assert len(self.generator.frames) == 0

    def test_reset_clears_frames(self):
        """Test reset clears the frame list."""
        self.generator.add_frame("/path/to/render/0001.png")
        self.generator.add_frame("/path/to/render/0002.png")
        assert len(self.generator.frames) == 2

        self.generator.reset()
        assert len(self.generator.frames) == 0

    def test_generate_manifest_structure(self):
        """Test manifest has correct structure."""
        self.generator.add_frame("/path/to/render/0001.png")

        manifest = self.generator.generate_manifest(fps=60, markers=[30, 90])

        assert "fps" in manifest
        assert "markers" in manifest
        assert "frames" in manifest

    def test_generate_manifest_fps(self):
        """Test fps is captured correctly."""
        manifest = self.generator.generate_manifest(fps=24, markers=[])
        assert manifest["fps"] == 24

    def test_generate_manifest_markers(self):
        """Test markers are captured correctly."""
        manifest = self.generator.generate_manifest(fps=60, markers=[30, 60, 90])
        assert manifest["markers"] == [30, 60, 90]

    def test_relativize_paths_strips_prefix(self):
        """Test that absolute paths are relativized to the export root."""
        self.generator.add_frame("/Users/james/project/render/0001.png")
        self.generator.add_frame("/Users/james/project/render/0002.png")

        manifest = self.generator.generate_manifest(
            fps=60,
            markers=[],
            root_dir=Path("/Users/james/project"),
        )

        assert manifest["frames"][0] == "render/0001.png"
        assert manifest["frames"][1] == "render/0002.png"

    def test_relativize_handles_missing_render_dir(self):
        """Paths without 'render' should be preserved as-is."""
        self.generator.add_frame("/some/other/path/frame.png")

        manifest = self.generator.generate_manifest(
            fps=60,
            markers=[],
            root_dir=Path("/Users/james/project"),
        )

        assert manifest["frames"][0] == "/some/other/path/frame.png"

    def test_write_manifest_creates_file(self):
        """Test that write_manifest creates a JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "manifest.json"

            self.generator.add_frame("render/0001.png")
            manifest = self.generator.generate_manifest(fps=30, markers=[10])
            self.generator.write_manifest(manifest, str(output_path))

            assert output_path.exists()

    def test_write_manifest_content(self):
        """Test that written manifest has correct content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "manifest.json"

            self.generator.add_frame("render/0001.png")
            self.generator.add_frame("render/0002.png")
            manifest = self.generator.generate_manifest(fps=60, markers=[50])
            self.generator.write_manifest(manifest, str(output_path))

            data = json.loads(output_path.read_text())
            assert data["fps"] == 60
            assert data["markers"] == [50]
            assert data["frames"] == ["render/0001.png", "render/0002.png"]

    def test_write_manifest_is_formatted(self):
        """Test that JSON output is indented for readability."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "manifest.json"

            manifest = self.generator.generate_manifest(fps=60, markers=[])
            self.generator.write_manifest(manifest, str(output_path))

            content = output_path.read_text()
            assert "\n" in content  # Has newlines (formatted)


class TestManifestGeneratorEdgeCases:
    """Edge case tests."""

    def test_empty_render(self):
        """Test manifest generation with no frames."""
        generator = ManifestGenerator()
        manifest = generator.generate_manifest(fps=60, markers=[])

        assert manifest["frames"] == []

    def test_no_markers(self):
        """Test manifest generation with no markers."""
        generator = ManifestGenerator()
        generator.add_frame("render/0001.png")
        manifest = generator.generate_manifest(fps=60, markers=[])

        assert manifest["markers"] == []

    def test_normalize_markers_offsets_by_frame_start(self):
        """Marker frame numbers should become zero-based frame indexes."""
        generator = ManifestGenerator()
        generator.add_frame("render/0001.png")
        generator.add_frame("render/0002.png")
        generator.add_frame("render/0003.png")

        markers = generator.normalize_markers([10, 12], frame_start=10)

        assert markers == [0, 2]

    def test_normalize_markers_sorts_markers(self):
        """Markers should be sorted for player navigation."""
        generator = ManifestGenerator()
        generator.add_frame("render/0001.png")
        generator.add_frame("render/0002.png")
        generator.add_frame("render/0003.png")

        markers = generator.normalize_markers([12, 10, 11], frame_start=10)

        assert markers == [0, 1, 2]

    def test_normalize_markers_filters_outside_render_range(self):
        """Markers outside the rendered frame span should be ignored."""
        generator = ManifestGenerator()
        generator.add_frame("render/0001.png")
        generator.add_frame("render/0002.png")

        markers = generator.normalize_markers([9, 10, 11, 12], frame_start=10)

        assert markers == [0, 1]

    def test_multiple_render_in_path(self):
        """Paths should be made relative from the explicit export root."""
        generator = ManifestGenerator()
        generator.add_frame("/render/project/render/0001.png")
        manifest = generator.generate_manifest(
            fps=60,
            markers=[],
            root_dir=Path("/render/project"),
        )

        assert manifest["frames"][0] == "render/0001.png"
