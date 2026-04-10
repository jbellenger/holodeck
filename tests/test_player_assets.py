from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]


def test_player_assets_match_packaged_resources():
    for asset_name in ("index.html", "player.js", "styles.css"):
        player_asset = (ROOT_DIR / "holodeck-player" / asset_name).read_text(encoding="utf-8")
        resource_asset = (ROOT_DIR / "holodeck" / "resources" / asset_name).read_text(encoding="utf-8")
        assert player_asset == resource_asset
