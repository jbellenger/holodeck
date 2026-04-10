"""Tests for the server module."""
import tempfile
import threading
import time
import urllib.request
import urllib.error
from pathlib import Path

import pytest

from holodeck.core.server import (
    DEFAULT_PLAYER_DIR,
    get_player_url,
    check_player_exists,
    create_server,
    deploy_player,
    get_resources_dir,
)


class TestGetPlayerUrl:
    """Tests for URL construction."""

    def test_default_player_path(self):
        url = get_player_url(8000)
        assert url == "http://localhost:8000/"

    def test_custom_port(self):
        url = get_player_url(3000)
        assert url == "http://localhost:3000/"

    def test_custom_player_path(self):
        url = get_player_url(8000, "my-player")
        assert url == "http://localhost:8000/my-player/"


class TestCheckPlayerExists:
    """Tests for player directory validation."""

    def test_missing_player_dir(self, tmp_path):
        assert check_player_exists(tmp_path) is False

    def test_empty_player_dir(self, tmp_path):
        (tmp_path / "styles.css").touch()
        assert check_player_exists(tmp_path) is False

    def test_player_dir_without_index(self, tmp_path):
        (tmp_path / "styles.css").touch()
        assert check_player_exists(tmp_path) is False

    def test_valid_player_dir(self, tmp_path):
        (tmp_path / "index.html").write_text("<html></html>")
        assert check_player_exists(tmp_path) is True

    def test_custom_player_path(self, tmp_path):
        player_dir = tmp_path / "custom-player"
        player_dir.mkdir()
        (player_dir / "index.html").write_text("<html></html>")
        assert check_player_exists(tmp_path, "custom-player") is True


class TestCreateServer:
    """Integration tests for server creation."""

    def test_server_serves_files(self, tmp_path):
        # Create test content
        (tmp_path / "test.txt").write_text("Hello, World!")

        # Create and start server
        server = create_server(0, tmp_path)  # Port 0 = random available port
        port = server.server_address[1]

        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            # Give server time to start
            time.sleep(0.1)

            # Fetch the test file
            url = f"http://localhost:{port}/test.txt"
            with urllib.request.urlopen(url, timeout=5) as response:
                content = response.read().decode()
                assert content == "Hello, World!"
        finally:
            server.shutdown()

    def test_server_serves_index_html(self, tmp_path):
        (tmp_path / "index.html").write_text("<html><body>Player</body></html>")

        # Create and start server
        server = create_server(0, tmp_path)
        port = server.server_address[1]

        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            time.sleep(0.1)

            url = f"http://localhost:{port}/"
            with urllib.request.urlopen(url, timeout=5) as response:
                content = response.read().decode()
                assert "Player" in content
        finally:
            server.shutdown()

    def test_server_404_for_missing_file(self, tmp_path):
        server = create_server(0, tmp_path)
        port = server.server_address[1]

        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            time.sleep(0.1)

            url = f"http://localhost:{port}/nonexistent.txt"
            with pytest.raises(urllib.error.HTTPError) as exc_info:
                urllib.request.urlopen(url, timeout=5)
            assert exc_info.value.code == 404
        finally:
            server.shutdown()

    def test_server_serves_nested_paths(self, tmp_path):
        # Create nested structure like render/manifest.json
        render_dir = tmp_path / "render"
        render_dir.mkdir()
        (render_dir / "manifest.json").write_text('{"fps": 24}')

        server = create_server(0, tmp_path)
        port = server.server_address[1]

        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            time.sleep(0.1)

            # This is the path the player will use: ../render/manifest.json
            # from holodeck/ resolves to /render/manifest.json
            url = f"http://localhost:{port}/render/manifest.json"
            with urllib.request.urlopen(url, timeout=5) as response:
                content = response.read().decode()
                assert '"fps": 24' in content
        finally:
            server.shutdown()

    def test_server_marks_frames_cacheable(self, tmp_path):
        render_dir = tmp_path / "render"
        render_dir.mkdir()
        (render_dir / "0001.png").write_bytes(b"frame")

        server = create_server(0, tmp_path)
        port = server.server_address[1]

        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            time.sleep(0.1)

            url = f"http://localhost:{port}/render/0001.png?v=token123"
            with urllib.request.urlopen(url, timeout=5) as response:
                assert response.headers["Cache-Control"] == "public, max-age=31536000, immutable"
        finally:
            server.shutdown()

    def test_server_marks_manifest_uncached(self, tmp_path):
        (tmp_path / "manifest.json").write_text('{"fps": 24}')

        server = create_server(0, tmp_path)
        port = server.server_address[1]

        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            time.sleep(0.1)

            url = f"http://localhost:{port}/manifest.json"
            with urllib.request.urlopen(url, timeout=5) as response:
                assert response.headers["Cache-Control"] == "no-cache"
        finally:
            server.shutdown()


class TestDeployPlayer:
    """Tests for player file deployment."""

    def test_resources_dir_exists(self):
        resources = get_resources_dir()
        assert resources.exists()
        assert (resources / "index.html").exists()

    def test_resources_dir_prefers_canonical_player_directory(self, tmp_path, monkeypatch):
        package_root = tmp_path / "repo" / "holodeck"
        package_root.mkdir(parents=True)
        canonical_player_dir = package_root.parent / "holodeck-player"
        canonical_player_dir.mkdir()
        (canonical_player_dir / "index.html").write_text("<html></html>")

        monkeypatch.setattr("holodeck.core.server.get_package_root", lambda: package_root)
        monkeypatch.setattr(
            "holodeck.core.server.get_package_path",
            lambda *parts: package_root.joinpath(*parts),
        )

        assert get_resources_dir() == canonical_player_dir

    def test_resources_dir_falls_back_to_packaged_resources(self, tmp_path, monkeypatch):
        package_root = tmp_path / "repo" / "holodeck"
        resources_dir = package_root / "resources"
        resources_dir.mkdir(parents=True)
        (resources_dir / "index.html").write_text("<html></html>")

        monkeypatch.setattr("holodeck.core.server.get_package_root", lambda: package_root)
        monkeypatch.setattr(
            "holodeck.core.server.get_package_path",
            lambda *parts: package_root.joinpath(*parts),
        )

        assert get_resources_dir() == resources_dir

    def test_deploy_creates_directory(self, tmp_path):
        player_dir = deploy_player(tmp_path)
        assert player_dir.exists()
        assert player_dir.is_dir()
        assert player_dir == tmp_path

    def test_deploy_copies_index_html(self, tmp_path):
        player_dir = deploy_player(tmp_path)
        index_file = player_dir / "index.html"
        assert index_file.exists()
        assert (player_dir / "player.js").exists()
        assert (player_dir / "styles.css").exists()
        content = index_file.read_text()
        assert "<html>" in content
        assert "player.js" in content

    def test_deploy_custom_dirname(self, tmp_path):
        player_dir = deploy_player(tmp_path, "my-player")
        assert player_dir.name == "my-player"
        assert (player_dir / "index.html").exists()
        assert (player_dir / "player.js").exists()

    def test_deploy_overwrites_existing(self, tmp_path):
        # Create existing player with old content
        player_dir = tmp_path
        (player_dir / "index.html").write_text("old content")

        # Deploy should overwrite
        deploy_player(tmp_path)
        content = (player_dir / "index.html").read_text()
        assert "old content" not in content
        assert "<html>" in content

    def test_deploy_idempotent(self, tmp_path):
        # Deploy twice should work without errors
        deploy_player(tmp_path)
        deploy_player(tmp_path)
        assert check_player_exists(tmp_path)

    def test_deploy_raises_if_resources_missing(self, tmp_path, monkeypatch):
        # Mock get_resources_dir to return a non-existent path
        monkeypatch.setattr(
            "holodeck.core.server.get_resources_dir",
            lambda: tmp_path / "nonexistent"
        )
        with pytest.raises(FileNotFoundError) as exc_info:
            deploy_player(tmp_path)
        assert "resources not found" in str(exc_info.value)


class TestEndToEnd:
    """End-to-end tests for the full server workflow."""

    def test_deploy_and_serve_player(self, tmp_path):
        """Test that deploying and serving allows accessing the player URL."""
        # Deploy player
        deploy_player(tmp_path)
        assert check_player_exists(tmp_path)

        # Start server
        server = create_server(0, tmp_path)
        port = server.server_address[1]

        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            time.sleep(0.1)

            url = get_player_url(port)
            with urllib.request.urlopen(url, timeout=5) as response:
                assert response.status == 200
                content = response.read().decode()
                # Verify it's the player HTML
                assert "<html>" in content
                assert "player.js" in content
        finally:
            server.shutdown()

    def test_full_workflow_with_manifest(self, tmp_path):
        """Test the complete workflow: deploy, create manifest, serve, access."""
        # Deploy player
        deploy_player(tmp_path)

        # Create render directory with manifest (simulating what render_handlers does)
        render_dir = tmp_path / "render"
        render_dir.mkdir()
        manifest = {
            "fps": 24,
            "markers": [0, 24],
            "frames": ["render/0001.png", "render/0002.png"]
        }
        import json
        (tmp_path / "manifest.json").write_text(json.dumps(manifest))

        # Create dummy frame files
        (render_dir / "0001.png").write_bytes(b"fake png 1")
        (render_dir / "0002.png").write_bytes(b"fake png 2")

        # Start server
        server = create_server(0, tmp_path)
        port = server.server_address[1]

        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            time.sleep(0.1)

            # Access player
            player_url = get_player_url(port)
            with urllib.request.urlopen(player_url, timeout=5) as response:
                assert response.status == 200

            manifest_url = f"http://localhost:{port}/manifest.json"
            with urllib.request.urlopen(manifest_url, timeout=5) as response:
                assert response.status == 200
                data = json.loads(response.read().decode())
                assert data["fps"] == 24

            frame_url = f"http://localhost:{port}/render/0001.png"
            with urllib.request.urlopen(frame_url, timeout=5) as response:
                assert response.status == 200
        finally:
            server.shutdown()
