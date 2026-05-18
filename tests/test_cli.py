"""Tests for the Holodeck CLI."""

import json
from pathlib import Path

import pytest

from holodeck.cli import main
from holodeck.core.blender import BlendMetadata


class TestCliHelp:
    def test_no_args_prints_comprehensive_help(self, capsys):
        exit_code = main([])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "Full subcommand reference:" in captured.out
        assert "usage: holodeck render-frames" in captured.out
        assert "usage: holodeck refresh" in captured.out
        assert "usage: holodeck build" in captured.out
        assert "usage: holodeck rescale-frames" in captured.out
        assert "usage: holodeck serve" in captured.out
        assert "--blender BLENDER" in captured.out
        assert "--animation-res-pct ANIMATION_RES_PCT" in captured.out
        assert "--animation-scale-pct ANIMATION_SCALE_PCT" in captured.out
        assert "--still-res-pct STILL_RES_PCT" in captured.out
        assert "--res-pct" not in captured.out
        assert "--animation-renderer {eevee,cycles,workbench}" in captured.out
        assert "--still-renderer {eevee,cycles,workbench}" in captured.out
        assert "--render-engine" not in captured.out
        assert "--scene SCENE" in captured.out
        assert "--title TITLE" in captured.out
        assert "--port PORT" in captured.out
        assert "--no-open" in captured.out
        assert "render-frames\n  Render frames from a .blend file into an output directory." in captured.out
        assert "  positional arguments:\n    blend_file" in captured.out
        assert "  options:\n    -h, --help" in captured.out

    def test_top_level_help_includes_all_subcommand_options(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main(["-h"])

        captured = capsys.readouterr()
        assert exc_info.value.code == 0
        assert "Full subcommand reference:" in captured.out
        assert "usage: holodeck render-frames" in captured.out
        assert "usage: holodeck refresh" in captured.out
        assert "usage: holodeck build" in captured.out
        assert "usage: holodeck rescale-frames" in captured.out
        assert "usage: holodeck serve" in captured.out
        assert "--blender BLENDER" in captured.out
        assert "--animation-res-pct ANIMATION_RES_PCT" in captured.out
        assert "--animation-scale-pct ANIMATION_SCALE_PCT" in captured.out
        assert "--still-res-pct STILL_RES_PCT" in captured.out
        assert "--res-pct" not in captured.out
        assert "--animation-renderer {eevee,cycles,workbench}" in captured.out
        assert "--still-renderer {eevee,cycles,workbench}" in captured.out
        assert "--render-engine" not in captured.out
        assert "--scene SCENE" in captured.out
        assert "--title TITLE" in captured.out
        assert "--port PORT" in captured.out
        assert "--no-open" in captured.out
        assert "serve\n  Serve an output directory locally for development." in captured.out
        assert "  positional arguments:\n    output_dir" in captured.out
        assert "  options:\n    -h, --help" in captured.out


class TestRenderFramesCommand:
    def test_renders_frames_and_deploys_player(self, monkeypatch, tmp_path):
        blend_file = tmp_path / "demo.blend"
        blend_file.touch()
        output_dir = tmp_path / "dist"
        calls = []

        monkeypatch.setattr("holodeck.cli.deploy_player", lambda path: calls.append(("deploy", path)))
        monkeypatch.setattr(
            "holodeck.cli.render_blend",
            lambda **kwargs: calls.append(("render", kwargs)),
        )

        exit_code = main(
            [
                "render-frames",
                str(blend_file),
                str(output_dir),
                "--animation-res-pct",
                "60",
                "--still-res-pct",
                "125",
                "--animation-scale-pct",
                "75",
            ]
        )

        assert exit_code == 0
        assert calls[0] == ("deploy", output_dir.resolve())
        assert calls[1][0] == "render"
        assert calls[1][1]["blend_file"] == blend_file.resolve()
        assert calls[1][1]["animation_res_pct"] == 60
        assert calls[1][1]["still_res_pct"] == 125
        assert calls[1][1]["animation_scale_pct"] == 75

    def test_passes_title_option_to_player_deploy(self, monkeypatch, tmp_path):
        blend_file = tmp_path / "demo.blend"
        blend_file.touch()
        output_dir = tmp_path / "dist"
        calls = []

        monkeypatch.setattr(
            "holodeck.cli.deploy_player",
            lambda path, title=None: calls.append(("deploy", path, title)),
        )
        monkeypatch.setattr("holodeck.cli.render_blend", lambda **kwargs: None)

        exit_code = main(
            ["render-frames", str(blend_file), str(output_dir), "--title", "Demo Deck"]
        )

        assert exit_code == 0
        assert calls == [("deploy", output_dir.resolve(), "Demo Deck")]

    def test_rejects_non_positive_animation_resolution_percentage(self, tmp_path, capsys):
        blend_file = tmp_path / "demo.blend"
        blend_file.touch()
        output_dir = tmp_path / "dist"

        with pytest.raises(SystemExit) as exc_info:
            main(["render-frames", str(blend_file), str(output_dir), "--animation-res-pct", "0"])

        captured = capsys.readouterr()
        assert exc_info.value.code == 2
        assert "must be a positive integer" in captured.err

    def test_rejects_non_positive_still_resolution_percentage(self, tmp_path, capsys):
        blend_file = tmp_path / "demo.blend"
        blend_file.touch()
        output_dir = tmp_path / "dist"

        with pytest.raises(SystemExit) as exc_info:
            main(["render-frames", str(blend_file), str(output_dir), "--still-res-pct", "0"])

        captured = capsys.readouterr()
        assert exc_info.value.code == 2
        assert "must be a positive integer" in captured.err

    def test_rejects_out_of_range_animation_scale_percentage(self, tmp_path, capsys):
        blend_file = tmp_path / "demo.blend"
        blend_file.touch()
        output_dir = tmp_path / "dist"

        with pytest.raises(SystemExit) as exc_info:
            main(["render-frames", str(blend_file), str(output_dir), "--animation-scale-pct", "101"])

        captured = capsys.readouterr()
        assert exc_info.value.code == 2
        assert "must be between 1 and 100" in captured.err

    def test_rejects_removed_res_pct_option(self, tmp_path, capsys):
        blend_file = tmp_path / "demo.blend"
        blend_file.touch()
        output_dir = tmp_path / "dist"

        with pytest.raises(SystemExit) as exc_info:
            main(["render-frames", str(blend_file), str(output_dir), "--res-pct", "50"])

        captured = capsys.readouterr()
        assert exc_info.value.code == 2
        assert "unrecognized arguments" in captured.err

    def test_passes_frames_option_through_to_render(self, monkeypatch, tmp_path):
        blend_file = tmp_path / "demo.blend"
        blend_file.touch()
        output_dir = tmp_path / "dist"
        calls = []

        monkeypatch.setattr("holodeck.cli.deploy_player", lambda _: None)
        monkeypatch.setattr(
            "holodeck.cli.render_blend",
            lambda **kwargs: calls.append(kwargs),
        )

        exit_code = main(
            ["render-frames", str(blend_file), str(output_dir), "--frames", "1,4-6"]
        )

        assert exit_code == 0
        assert calls[0]["frames"] == "1,4-6"

    def test_defaults_frames_option_to_none(self, monkeypatch, tmp_path):
        blend_file = tmp_path / "demo.blend"
        blend_file.touch()
        output_dir = tmp_path / "dist"
        calls = []

        monkeypatch.setattr("holodeck.cli.deploy_player", lambda _: None)
        monkeypatch.setattr(
            "holodeck.cli.render_blend",
            lambda **kwargs: calls.append(kwargs),
        )

        exit_code = main(["render-frames", str(blend_file), str(output_dir)])

        assert exit_code == 0
        assert calls[0]["frames"] is None
        assert calls[0]["stills_only"] is False
        assert calls[0]["animation_res_pct"] == 100
        assert calls[0]["still_res_pct"] == 100
        assert calls[0]["animation_scale_pct"] == 100
        assert calls[0]["animation_renderer"] is None
        assert calls[0]["still_renderer"] is None

    def test_passes_renderer_options_through_to_render(self, monkeypatch, tmp_path):
        blend_file = tmp_path / "demo.blend"
        blend_file.touch()
        output_dir = tmp_path / "dist"
        calls = []

        monkeypatch.setattr("holodeck.cli.deploy_player", lambda _: None)
        monkeypatch.setattr(
            "holodeck.cli.render_blend",
            lambda **kwargs: calls.append(kwargs),
        )

        exit_code = main(
            [
                "render-frames",
                str(blend_file),
                str(output_dir),
                "--animation-renderer",
                "eevee",
                "--still-renderer",
                "cycles",
            ]
        )

        assert exit_code == 0
        assert calls[0]["animation_renderer"] == "eevee"
        assert calls[0]["still_renderer"] == "cycles"

    def test_rejects_invalid_renderer(self, tmp_path, capsys):
        blend_file = tmp_path / "demo.blend"
        blend_file.touch()
        output_dir = tmp_path / "dist"

        with pytest.raises(SystemExit) as exc_info:
            main(
                [
                    "render-frames",
                    str(blend_file),
                    str(output_dir),
                    "--animation-renderer",
                    "internal",
                ]
            )

        captured = capsys.readouterr()
        assert exc_info.value.code == 2
        assert "invalid choice" in captured.err

    def test_rejects_removed_render_engine_option(self, tmp_path, capsys):
        blend_file = tmp_path / "demo.blend"
        blend_file.touch()
        output_dir = tmp_path / "dist"

        with pytest.raises(SystemExit) as exc_info:
            main(["render-frames", str(blend_file), str(output_dir), "--render-engine", "eevee"])

        captured = capsys.readouterr()
        assert exc_info.value.code == 2
        assert "unrecognized arguments" in captured.err

    def test_passes_stills_only_option_through_to_render(self, monkeypatch, tmp_path):
        blend_file = tmp_path / "demo.blend"
        blend_file.touch()
        output_dir = tmp_path / "dist"
        calls = []

        monkeypatch.setattr("holodeck.cli.deploy_player", lambda _: None)
        monkeypatch.setattr(
            "holodeck.cli.render_blend",
            lambda **kwargs: calls.append(kwargs),
        )

        exit_code = main(
            ["render-frames", str(blend_file), str(output_dir), "--stills-only"]
        )

        assert exit_code == 0
        assert calls[0]["stills_only"] is True
        assert calls[0]["frames"] is None

    def test_rejects_combining_frames_and_stills_only(self, tmp_path, capsys):
        blend_file = tmp_path / "demo.blend"
        blend_file.touch()
        output_dir = tmp_path / "dist"

        with pytest.raises(SystemExit) as exc_info:
            main(
                [
                    "render-frames",
                    str(blend_file),
                    str(output_dir),
                    "--frames",
                    "1",
                    "--stills-only",
                ]
            )

        captured = capsys.readouterr()
        assert exc_info.value.code == 2
        assert "not allowed with" in captured.err

    def test_rejects_removed_markers_only_option(self, tmp_path, capsys):
        blend_file = tmp_path / "demo.blend"
        blend_file.touch()
        output_dir = tmp_path / "dist"

        with pytest.raises(SystemExit) as exc_info:
            main(["render-frames", str(blend_file), str(output_dir), "--markers-only"])

        captured = capsys.readouterr()
        assert exc_info.value.code == 2
        assert "unrecognized arguments" in captured.err

    def test_rejects_invalid_frames_spec(self, tmp_path, capsys):
        blend_file = tmp_path / "demo.blend"
        blend_file.touch()
        output_dir = tmp_path / "dist"

        with pytest.raises(SystemExit) as exc_info:
            main(["render-frames", str(blend_file), str(output_dir), "--frames", "1-"])

        captured = capsys.readouterr()
        assert exc_info.value.code == 2
        assert "Invalid frame" in captured.err


class TestRefreshCommand:
    def test_writes_manifest_from_expected_frames(self, monkeypatch, tmp_path):
        blend_file = tmp_path / "demo.blend"
        blend_file.touch()
        output_dir = tmp_path / "dist"
        render_dir = output_dir / "render"
        render_dir.mkdir(parents=True)
        (render_dir / "0001.png").write_bytes(b"frame-1")
        (render_dir / "0002.png").write_bytes(b"frame-2")

        monkeypatch.setattr("holodeck.cli.deploy_player", lambda _: None)
        monkeypatch.setattr(
            "holodeck.cli.extract_blend_metadata",
            lambda **kwargs: BlendMetadata(
                fps=24,
                frame_start=1,
                frame_end=2,
                marker_frames=[1, 2],
                frame_paths=[
                    str(render_dir / "0001.png"),
                    str(render_dir / "0002.png"),
                ],
            ),
        )

        exit_code = main(["refresh", str(blend_file), str(output_dir)])

        assert exit_code == 0
        manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["frames"] == ["render/0001.png", "render/0002.png"]
        assert manifest["markers"] == [0, 1]
        assert "token" in manifest

    def test_rejects_stills_only_option(self, tmp_path, capsys):
        blend_file = tmp_path / "demo.blend"
        blend_file.touch()
        output_dir = tmp_path / "dist"

        with pytest.raises(SystemExit) as exc_info:
            main(["refresh", str(blend_file), str(output_dir), "--stills-only"])

        captured = capsys.readouterr()
        assert exc_info.value.code == 2
        assert "unrecognized arguments" in captured.err

    def test_fails_when_expected_frames_are_missing(self, monkeypatch, tmp_path, capsys):
        blend_file = tmp_path / "demo.blend"
        blend_file.touch()
        output_dir = tmp_path / "dist"

        monkeypatch.setattr("holodeck.cli.deploy_player", lambda _: None)
        monkeypatch.setattr(
            "holodeck.cli.extract_blend_metadata",
            lambda **kwargs: BlendMetadata(
                fps=24,
                frame_start=1,
                frame_end=2,
                marker_frames=[1],
                frame_paths=[
                    str(output_dir / "render" / "0001.png"),
                    str(output_dir / "render" / "0002.png"),
                ],
            ),
        )

        exit_code = main(["refresh", str(blend_file), str(output_dir)])

        captured = capsys.readouterr()
        assert exit_code == 1
        assert "Missing 2 rendered frame(s)" in captured.err


class TestBuildCommand:
    def test_runs_render_then_refresh(self, monkeypatch, tmp_path):
        blend_file = tmp_path / "demo.blend"
        output_dir = tmp_path / "dist"
        calls = []

        monkeypatch.setattr(
            "holodeck.cli.render_frames_command",
            lambda args: calls.append(
                (
                    "render",
                    args.blend_file,
                    args.output_dir,
                    args.animation_res_pct,
                    args.still_res_pct,
                    args.animation_scale_pct,
                )
            )
            or 0,
        )
        monkeypatch.setattr(
            "holodeck.cli._refresh_output",
            lambda args, *, stills_only: calls.append(
                (
                    "manifest",
                    args.blend_file,
                    args.output_dir,
                    args.animation_res_pct,
                    args.still_res_pct,
                    args.animation_scale_pct,
                    stills_only,
                )
            )
            or 0,
        )

        exit_code = main(
            [
                "build",
                str(blend_file),
                str(output_dir),
                "--animation-res-pct",
                "40",
                "--still-res-pct",
                "150",
                "--animation-scale-pct",
                "50",
            ]
        )

        assert exit_code == 0
        assert calls == [
            ("render", str(blend_file), str(output_dir), 40, 150, 50),
            ("manifest", str(blend_file), str(output_dir), 40, 150, 50, False),
        ]

    def test_propagates_stills_only_to_render_and_private_refresh(self, monkeypatch, tmp_path):
        blend_file = tmp_path / "demo.blend"
        output_dir = tmp_path / "dist"
        calls = []

        monkeypatch.setattr(
            "holodeck.cli.render_frames_command",
            lambda args: calls.append(("render", args.stills_only)) or 0,
        )
        monkeypatch.setattr(
            "holodeck.cli._refresh_output",
            lambda args, *, stills_only: calls.append(("manifest", stills_only)) or 0,
        )

        exit_code = main(["build", str(blend_file), str(output_dir), "--stills-only"])

        assert exit_code == 0
        assert calls == [("render", True), ("manifest", True)]

    def test_propagates_title_to_render_and_refresh(self, monkeypatch, tmp_path):
        blend_file = tmp_path / "demo.blend"
        output_dir = tmp_path / "dist"
        calls = []

        monkeypatch.setattr(
            "holodeck.cli.render_frames_command",
            lambda args: calls.append(("render", args.title)) or 0,
        )
        monkeypatch.setattr(
            "holodeck.cli._refresh_output",
            lambda args, *, stills_only: calls.append(("manifest", args.title, stills_only)) or 0,
        )

        exit_code = main(["build", str(blend_file), str(output_dir), "--title", "Demo Deck"])

        assert exit_code == 0
        assert calls == [("render", "Demo Deck"), ("manifest", "Demo Deck", False)]

    def test_propagates_renderer_to_render_and_refresh(self, monkeypatch, tmp_path):
        blend_file = tmp_path / "demo.blend"
        output_dir = tmp_path / "dist"
        calls = []

        monkeypatch.setattr(
            "holodeck.cli.render_frames_command",
            lambda args: calls.append(("render", args.animation_renderer, args.still_renderer)) or 0,
        )
        monkeypatch.setattr(
            "holodeck.cli._refresh_output",
            lambda args, *, stills_only: calls.append(
                ("manifest", args.animation_renderer, args.still_renderer, stills_only)
            )
            or 0,
        )

        exit_code = main(
            [
                "build",
                str(blend_file),
                str(output_dir),
                "--animation-renderer",
                "workbench",
                "--still-renderer",
                "cycles",
            ]
        )

        assert exit_code == 0
        assert calls == [
            ("render", "workbench", "cycles"),
            ("manifest", "workbench", "cycles", False),
        ]

    def test_stills_only_build_writes_stills_only_manifest(self, monkeypatch, tmp_path):
        blend_file = tmp_path / "demo.blend"
        blend_file.touch()
        output_dir = tmp_path / "dist"
        render_dir = output_dir / "render"
        render_dir.mkdir(parents=True)
        (render_dir / "0001.png").write_bytes(b"frame-1")
        (render_dir / "0003.png").write_bytes(b"frame-3")
        (render_dir / "0004.png").write_bytes(b"frame-4")

        monkeypatch.setattr("holodeck.cli.deploy_player", lambda *args, **kwargs: None)
        monkeypatch.setattr("holodeck.cli.render_blend", lambda **kwargs: None)
        monkeypatch.setattr(
            "holodeck.cli.extract_blend_metadata",
            lambda **kwargs: BlendMetadata(
                fps=24,
                frame_start=1,
                frame_end=4,
                marker_frames=[3],
                frame_paths=[
                    str(render_dir / "0001.png"),
                    str(render_dir / "0002.png"),
                    str(render_dir / "0003.png"),
                    str(render_dir / "0004.png"),
                ],
            ),
        )

        exit_code = main(["build", str(blend_file), str(output_dir), "--stills-only"])

        assert exit_code == 0
        manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["frames"] == ["render/0001.png", "render/0003.png", "render/0004.png"]
        assert manifest["markers"] == [0, 1, 2]


class TestRescaleFramesCommand:
    def test_rescales_frames_from_existing_output(self, monkeypatch, tmp_path, capsys):
        output_dir = tmp_path / "dist"
        output_dir.mkdir()
        calls = []

        def fake_rescale_animation_frames_from_manifest(**kwargs):
            calls.append(kwargs)
            return type("Result", (), {"frame_count": 3, "manifest_path": output_dir / "manifest.json"})()

        monkeypatch.setattr(
            "holodeck.cli.rescale_animation_frames_from_manifest",
            fake_rescale_animation_frames_from_manifest,
        )

        exit_code = main(
            ["rescale-frames", str(output_dir), "--animation-scale-pct", "50"]
        )

        captured = capsys.readouterr()
        assert exit_code == 0
        assert calls == [
            {
                "output_dir": output_dir.resolve(),
                "animation_scale_pct": 50,
            }
        ]
        assert "Rescaled 3 animation frame(s)" in captured.out
        assert "Updated" in captured.out

    def test_rejects_out_of_range_animation_scale(self, tmp_path, capsys):
        output_dir = tmp_path / "dist"
        output_dir.mkdir()

        with pytest.raises(SystemExit) as exc_info:
            main(["rescale-frames", str(output_dir), "--animation-scale-pct", "101"])

        captured = capsys.readouterr()
        assert exc_info.value.code == 2
        assert "must be between 1 and 100" in captured.err

    def test_fails_when_output_dir_is_missing(self, tmp_path, capsys):
        exit_code = main(
            ["rescale-frames", str(tmp_path / "missing"), "--animation-scale-pct", "50"]
        )

        captured = capsys.readouterr()
        assert exit_code == 1
        assert "Output directory not found" in captured.err


class TestServeCommand:
    class _FakeServer:
        def __init__(self, port):
            self.server_address = ("", port)
            self.serve_forever_called = False
            self.server_close_called = False

        def serve_forever(self):
            self.serve_forever_called = True

        def server_close(self):
            self.server_close_called = True

    def test_opens_browser_by_default(self, monkeypatch, tmp_path):
        output_dir = tmp_path / "dist"
        output_dir.mkdir()
        (output_dir / "index.html").write_text("<html></html>", encoding="utf-8")
        server = self._FakeServer(port=8123)
        opened_urls = []

        monkeypatch.setattr("holodeck.cli.create_server", lambda port, directory: server)
        monkeypatch.setattr("holodeck.cli.webbrowser.open", lambda url: opened_urls.append(url) or True)

        exit_code = main(["serve", str(output_dir)])

        assert exit_code == 0
        assert opened_urls == ["http://localhost:8123/"]
        assert server.serve_forever_called is True
        assert server.server_close_called is True

    def test_skips_browser_open_when_disabled(self, monkeypatch, tmp_path):
        output_dir = tmp_path / "dist"
        output_dir.mkdir()
        (output_dir / "index.html").write_text("<html></html>", encoding="utf-8")
        server = self._FakeServer(port=8123)

        monkeypatch.setattr("holodeck.cli.create_server", lambda port, directory: server)
        monkeypatch.setattr(
            "holodeck.cli.webbrowser.open",
            lambda url: pytest.fail("webbrowser.open should not be called when --no-open is set"),
        )

        exit_code = main(["serve", str(output_dir), "--no-open"])

        assert exit_code == 0
        assert server.serve_forever_called is True
        assert server.server_close_called is True
