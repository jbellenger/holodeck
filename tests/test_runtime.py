"""Tests for packaged runtime asset lookup."""

from pathlib import Path

from holodeck.core.runtime import get_package_path, get_package_root


class TestRuntimePaths:
    def test_package_root_defaults_to_source_tree(self):
        package_root = get_package_root()

        assert package_root.name == "holodeck"
        assert (package_root / "resources" / "index.html").exists()

    def test_package_root_uses_meipass_when_frozen(self, monkeypatch, tmp_path):
        bundle_root = tmp_path / "bundle"
        frozen_root = bundle_root / "holodeck"
        frozen_root.mkdir(parents=True)

        monkeypatch.setattr("holodeck.core.runtime.sys._MEIPASS", str(bundle_root), raising=False)

        assert get_package_root() == frozen_root

    def test_package_path_joins_parts(self, monkeypatch, tmp_path):
        bundle_root = tmp_path / "bundle"
        frozen_root = bundle_root / "holodeck"
        frozen_root.mkdir(parents=True)

        monkeypatch.setattr("holodeck.core.runtime.sys._MEIPASS", str(bundle_root), raising=False)

        assert get_package_path("resources", "index.html") == frozen_root / "resources" / "index.html"
