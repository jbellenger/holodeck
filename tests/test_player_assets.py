from pathlib import Path

from holodeck.core.server import deploy_player


ROOT_DIR = Path(__file__).resolve().parents[1]


def test_packaged_player_assets_exist():
    for asset_name in ("index.html", "player.js", "styles.css"):
        assert (ROOT_DIR / "holodeck" / "resources" / asset_name).is_file()


def test_deployed_player_assets_match_packaged_resources(tmp_path):
    deployed_player_dir = deploy_player(tmp_path)

    for asset_name in ("index.html", "player.js", "styles.css"):
        deployed_asset = (deployed_player_dir / asset_name).read_text(encoding="utf-8")
        resource_asset = (ROOT_DIR / "holodeck" / "resources" / asset_name).read_text(encoding="utf-8")
        assert deployed_asset == resource_asset


def test_player_assets_use_relative_paths_for_static_hosts():
    index_html = (ROOT_DIR / "holodeck" / "resources" / "index.html").read_text(encoding="utf-8")
    player_js = (ROOT_DIR / "holodeck" / "resources" / "player.js").read_text(encoding="utf-8")

    assert 'href="styles.css"' in index_html
    assert 'src="player.js"' in index_html
    assert 'fetch("./manifest.json")' in player_js


def test_player_assets_include_expected_keyboard_controls_and_loading_delay():
    player_js = (ROOT_DIR / "holodeck" / "resources" / "player.js").read_text(encoding="utf-8")
    styles_css = (ROOT_DIR / "holodeck" / "resources" / "styles.css").read_text(encoding="utf-8")

    assert 'const loadingIndicatorDelayMillis = 32;' in player_js
    assert 'case "ArrowDown":' in player_js
    assert 'case "Enter":' in player_js
    assert 'case "KeyF":' in player_js
    assert "requestFullscreen" in player_js
    assert 'container.addEventListener("touchend"' in player_js
    assert "changedTouches[0].clientX" in player_js
    assert "jump(-1);" in player_js
    assert "touch-action: manipulation;" in styles_css
