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
    index_html = (ROOT_DIR / "holodeck" / "resources" / "index.html").read_text(encoding="utf-8")
    styles_css = (ROOT_DIR / "holodeck" / "resources" / "styles.css").read_text(encoding="utf-8")

    assert '<canvas id="canvas"></canvas>' in index_html
    assert 'const loadingIndicatorDelayMillis = 32;' in player_js
    assert 'const optimisticPreloadSegmentCount = 2;' in player_js
    assert 'const swipeThresholdPixels = 48;' in player_js
    assert 'const decodedFrameBufferAhead = 6;' in player_js
    assert 'const decodedFrameBufferBehind = 1;' in player_js
    assert 'const decodedFrameConcurrency = 3;' in player_js
    assert 'case "ArrowDown":' in player_js
    assert 'case "Enter":' in player_js
    assert 'case "KeyF":' in player_js
    assert 'requestAnimationFrame(loop);' in player_js
    assert "createImageBitmap" in player_js
    assert 'document.getElementById("canvas")' in player_js
    assert "requestFullscreen" in player_js
    assert 'screen.orientation.lock("landscape")' in player_js
    assert "screen.orientation.unlock();" in player_js
    assert 'container.addEventListener("touchstart"' in player_js
    assert 'container.addEventListener("touchcancel"' in player_js
    assert 'container.addEventListener("touchend"' in player_js
    assert "event.touches[0].clientX" in player_js
    assert "event.touches[0].clientY" in player_js
    assert "handleTouchGesture(event.changedTouches[0])" in player_js
    assert "jump(-1);" in player_js
    assert "scheduleOptimisticPreload" in player_js
    assert "scheduleDecodedBuffer" in player_js
    assert 'const warmedBlob = await warmFrame(frameIndex);' in player_js
    assert 'const workerCount = Math.min(decodedFrameConcurrency, pendingFrames.length);' in player_js
    assert "touch-action: manipulation;" in styles_css
