"""Tests for the player asset sync script."""

import importlib.util
from pathlib import Path


def load_sync_player_assets_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "sync_player_assets.py"
    spec = importlib.util.spec_from_file_location("sync_player_assets", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestSyncPlayerAssets:
    def test_copy_player_assets_overwrites_destination_files(self, tmp_path):
        module = load_sync_player_assets_module()
        source_dir = tmp_path / "holodeck-player"
        destination_dir = tmp_path / "docs"
        source_dir.mkdir()
        destination_dir.mkdir()

        for asset_name in module.ASSET_NAMES:
            (source_dir / asset_name).write_text(f"canonical {asset_name}", encoding="utf-8")
            (destination_dir / asset_name).write_text("stale", encoding="utf-8")

        module.copy_player_assets(source_dir, destination_dir)

        for asset_name in module.ASSET_NAMES:
            assert (destination_dir / asset_name).read_text(encoding="utf-8") == (
                f"canonical {asset_name}"
            )

    def test_sync_player_assets_copies_into_generated_directories(self, tmp_path):
        module = load_sync_player_assets_module()
        source_dir = tmp_path / module.CANONICAL_PLAYER_DIRNAME
        source_dir.mkdir()

        for asset_name in module.ASSET_NAMES:
            (source_dir / asset_name).write_text(f"canonical {asset_name}", encoding="utf-8")

        destination_dirs = module.sync_player_assets(tmp_path)

        assert destination_dirs == [tmp_path / "holodeck" / "resources"]

        for destination_dir in destination_dirs:
            for asset_name in module.ASSET_NAMES:
                assert (destination_dir / asset_name).read_text(encoding="utf-8") == (
                    f"canonical {asset_name}"
                )
