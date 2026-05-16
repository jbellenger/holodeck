"""Tests for Blender subprocess helpers."""

import json
from pathlib import Path

import pytest

from holodeck.core.blender import (
    BlendMetadata,
    extract_blend_metadata,
    render_blend,
    resolve_blender_executable,
    run_blender_script,
)


class TestResolveBlenderExecutable:
    def test_raises_when_blender_is_missing(self, monkeypatch):
        monkeypatch.setattr("holodeck.core.blender.shutil.which", lambda _: None)

        with pytest.raises(FileNotFoundError):
            resolve_blender_executable("blender")


class TestRunBlenderScript:
    def test_builds_expected_command(self, monkeypatch, tmp_path):
        blend_file = tmp_path / "demo.blend"
        blend_file.touch()
        helper_script = tmp_path / "helper.py"
        helper_script.write_text("print('hello')", encoding="utf-8")
        captured = {}

        monkeypatch.setattr("holodeck.core.blender.get_script_path", lambda _: helper_script)
        monkeypatch.setattr(
            "holodeck.core.blender.get_package_root",
            lambda: tmp_path / "package-root" / "holodeck",
        )
        monkeypatch.setattr(
            "holodeck.core.blender.resolve_blender_executable",
            lambda _: "/usr/bin/blender",
        )

        def fake_run(command, check):
            captured["command"] = command
            captured["check"] = check

        monkeypatch.setattr("holodeck.core.blender.subprocess.run", fake_run)

        run_blender_script(
            blend_file=blend_file,
            script_name="helper.py",
            script_args=["--output", str(tmp_path / "out")],
        )

        assert captured["check"] is True
        expected_bootstrap_expr = (
            f'import sys; sys.path.insert(0, {json.dumps(str(tmp_path / "package-root"))})'
        )
        assert captured["command"] == [
            "/usr/bin/blender",
            "-b",
            str(blend_file),
            "--python-expr",
            expected_bootstrap_expr,
            "--python",
            str(helper_script),
            "--",
            "--output",
            str(tmp_path / "out"),
        ]


class TestRenderBlend:
    def test_uses_render_script(self, monkeypatch, tmp_path):
        blend_file = tmp_path / "demo.blend"
        blend_file.touch()
        output_dir = tmp_path / "dist"
        captured = {}

        def fake_run_blender_script(**kwargs):
            captured.update(kwargs)

        monkeypatch.setattr("holodeck.core.blender.run_blender_script", fake_run_blender_script)

        render_blend(
            blend_file=blend_file,
            output_dir=output_dir,
            scene="Deck",
            animation_res_pct=50,
            still_res_pct=125,
        )

        assert captured["blend_file"] == blend_file
        assert captured["script_name"] == "render_frames.py"
        assert captured["script_args"] == [
            "--output",
            str(output_dir),
            "--animation-res-pct",
            "50",
            "--still-res-pct",
            "125",
            "--scene",
            "Deck",
        ]

    def test_forwards_frames_option(self, monkeypatch, tmp_path):
        blend_file = tmp_path / "demo.blend"
        blend_file.touch()
        output_dir = tmp_path / "dist"
        captured = {}

        def fake_run_blender_script(**kwargs):
            captured.update(kwargs)

        monkeypatch.setattr("holodeck.core.blender.run_blender_script", fake_run_blender_script)

        render_blend(blend_file=blend_file, output_dir=output_dir, frames="1,4-6")

        assert captured["script_args"] == [
            "--output",
            str(output_dir),
            "--animation-res-pct",
            "50",
            "--still-res-pct",
            "100",
            "--frames",
            "1,4-6",
        ]

    def test_omits_frames_option_when_unset(self, monkeypatch, tmp_path):
        blend_file = tmp_path / "demo.blend"
        blend_file.touch()
        output_dir = tmp_path / "dist"
        captured = {}

        def fake_run_blender_script(**kwargs):
            captured.update(kwargs)

        monkeypatch.setattr("holodeck.core.blender.run_blender_script", fake_run_blender_script)

        render_blend(blend_file=blend_file, output_dir=output_dir)

        assert "--frames" not in captured["script_args"]
        assert "--stills-only" not in captured["script_args"]

    def test_forwards_stills_only_option(self, monkeypatch, tmp_path):
        blend_file = tmp_path / "demo.blend"
        blend_file.touch()
        output_dir = tmp_path / "dist"
        captured = {}

        def fake_run_blender_script(**kwargs):
            captured.update(kwargs)

        monkeypatch.setattr("holodeck.core.blender.run_blender_script", fake_run_blender_script)

        render_blend(blend_file=blend_file, output_dir=output_dir, stills_only=True)

        assert captured["script_args"] == [
            "--output",
            str(output_dir),
            "--animation-res-pct",
            "50",
            "--still-res-pct",
            "100",
            "--stills-only",
        ]

    def test_forwards_renderer_options(self, monkeypatch, tmp_path):
        blend_file = tmp_path / "demo.blend"
        blend_file.touch()
        output_dir = tmp_path / "dist"
        captured = {}

        def fake_run_blender_script(**kwargs):
            captured.update(kwargs)

        monkeypatch.setattr("holodeck.core.blender.run_blender_script", fake_run_blender_script)

        render_blend(
            blend_file=blend_file,
            output_dir=output_dir,
            animation_renderer="workbench",
            still_renderer="cycles",
        )

        assert captured["script_args"] == [
            "--output",
            str(output_dir),
            "--animation-res-pct",
            "50",
            "--still-res-pct",
            "100",
            "--animation-renderer",
            "workbench",
            "--still-renderer",
            "cycles",
        ]

    def test_rejects_unknown_renderer(self, tmp_path):
        blend_file = tmp_path / "demo.blend"
        blend_file.touch()
        output_dir = tmp_path / "dist"

        with pytest.raises(ValueError, match="Renderer"):
            render_blend(
                blend_file=blend_file,
                output_dir=output_dir,
                animation_renderer="internal",
            )

    def test_rejects_combining_frame_selection_modes(self, tmp_path):
        blend_file = tmp_path / "demo.blend"
        blend_file.touch()
        output_dir = tmp_path / "dist"

        with pytest.raises(ValueError, match="frame selection"):
            render_blend(
                blend_file=blend_file,
                output_dir=output_dir,
                frames="1",
                stills_only=True,
            )

    def test_rejects_non_positive_animation_resolution(self, tmp_path):
        blend_file = tmp_path / "demo.blend"
        blend_file.touch()
        output_dir = tmp_path / "dist"

        with pytest.raises(ValueError, match="Animation resolution"):
            render_blend(
                blend_file=blend_file,
                output_dir=output_dir,
                animation_res_pct=0,
            )

    def test_rejects_non_positive_still_resolution(self, tmp_path):
        blend_file = tmp_path / "demo.blend"
        blend_file.touch()
        output_dir = tmp_path / "dist"

        with pytest.raises(ValueError, match="Still resolution"):
            render_blend(
                blend_file=blend_file,
                output_dir=output_dir,
                still_res_pct=0,
            )


class TestExtractBlendMetadata:
    def test_reads_metadata_json(self, monkeypatch, tmp_path):
        blend_file = tmp_path / "demo.blend"
        blend_file.touch()
        output_dir = tmp_path / "dist"

        def fake_run_blender_script(**kwargs):
            script_args = kwargs["script_args"]
            json_output = Path(script_args[script_args.index("--json-output") + 1])
            payload = {
                "fps": 24,
                "frame_start": 10,
                "frame_end": 12,
                "marker_frames": [10, 12],
                "frame_paths": [
                    str(output_dir / "render" / "0010.png"),
                    str(output_dir / "render" / "0011.png"),
                    str(output_dir / "render" / "0012.png"),
                ],
            }
            json_output.write_text(json.dumps(payload), encoding="utf-8")

        monkeypatch.setattr("holodeck.core.blender.run_blender_script", fake_run_blender_script)

        metadata = extract_blend_metadata(blend_file=blend_file, output_dir=output_dir)

        assert isinstance(metadata, BlendMetadata)
        assert metadata.frame_count == 3
        assert metadata.marker_frames == [10, 12]
        assert metadata.frame_paths[-1].endswith("0012.png")
