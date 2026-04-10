"""Tests for packaged runtime asset lookup."""

from contextlib import contextmanager
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

    def test_package_root_falls_back_to_importlib_resources(self, monkeypatch, tmp_path):
        extracted_root = tmp_path / "extracted" / "holodeck"
        extracted_root.mkdir(parents=True)
        traversable = object()

        @contextmanager
        def fake_as_file(resource):
            assert resource is traversable
            yield extracted_root

        monkeypatch.setattr("holodeck.core.runtime._RESOURCE_PACKAGE_ROOT", None)
        monkeypatch.setattr(
            "holodeck.core.runtime._get_source_package_root",
            lambda: tmp_path / "missing-package-root",
        )
        monkeypatch.setattr("holodeck.core.runtime.resources.files", lambda package: traversable)
        monkeypatch.setattr("holodeck.core.runtime.resources.as_file", fake_as_file)

        assert get_package_root() == extracted_root
