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


def write_empty_render_summary(script_args):
    if "--render-summary-json" in script_args:
        summary_path = Path(script_args[script_args.index("--render-summary-json") + 1])
        summary_path.write_text(
            json.dumps({"animation_frame_paths": [], "still_frame_paths": []}),
            encoding="utf-8",
        )


def without_render_summary(script_args):
    if "--render-summary-json" not in script_args:
        return script_args
    index = script_args.index("--render-summary-json")
    return script_args[:index] + script_args[index + 2 :]


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
            write_empty_render_summary(kwargs["script_args"])

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
        assert without_render_summary(captured["script_args"]) == [
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
            write_empty_render_summary(kwargs["script_args"])

        monkeypatch.setattr("holodeck.core.blender.run_blender_script", fake_run_blender_script)

        render_blend(blend_file=blend_file, output_dir=output_dir, frames="1,4-6")

        assert without_render_summary(captured["script_args"]) == [
            "--output",
            str(output_dir),
            "--animation-res-pct",
            "100",
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
            write_empty_render_summary(kwargs["script_args"])

        monkeypatch.setattr("holodeck.core.blender.run_blender_script", fake_run_blender_script)

        render_blend(blend_file=blend_file, output_dir=output_dir)

        filtered_args = without_render_summary(captured["script_args"])
        assert "--frames" not in filtered_args
        assert "--stills-only" not in filtered_args

    def test_forwards_stills_only_option(self, monkeypatch, tmp_path):
        blend_file = tmp_path / "demo.blend"
        blend_file.touch()
        output_dir = tmp_path / "dist"
        captured = {}

        def fake_run_blender_script(**kwargs):
            captured.update(kwargs)
            write_empty_render_summary(kwargs["script_args"])

        monkeypatch.setattr("holodeck.core.blender.run_blender_script", fake_run_blender_script)

        render_blend(blend_file=blend_file, output_dir=output_dir, stills_only=True)

        assert without_render_summary(captured["script_args"]) == [
            "--output",
            str(output_dir),
            "--animation-res-pct",
            "100",
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
            write_empty_render_summary(kwargs["script_args"])

        monkeypatch.setattr("holodeck.core.blender.run_blender_script", fake_run_blender_script)

        render_blend(
            blend_file=blend_file,
            output_dir=output_dir,
            animation_renderer="workbench",
            still_renderer="cycles",
        )

        assert without_render_summary(captured["script_args"]) == [
            "--output",
            str(output_dir),
            "--animation-res-pct",
            "100",
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

    def test_rejects_out_of_range_animation_scale(self, tmp_path):
        blend_file = tmp_path / "demo.blend"
        blend_file.touch()
        output_dir = tmp_path / "dist"

        with pytest.raises(ValueError, match="Animation scale"):
            render_blend(
                blend_file=blend_file,
                output_dir=output_dir,
                animation_scale_pct=101,
            )

    def test_preserves_and_scales_non_still_animation_frames(self, monkeypatch, tmp_path):
        blend_file = tmp_path / "demo.blend"
        blend_file.touch()
        output_dir = tmp_path / "dist"
        render_dir = output_dir / "render"
        render_dir.mkdir(parents=True)
        (render_dir / "0001.avif").write_bytes(b"still")
        (render_dir / "0002.avif").write_bytes(b"animation")
        captured = {}

        def fake_run_blender_script(**kwargs):
            script_args = kwargs["script_args"]
            summary_path = Path(script_args[script_args.index("--render-summary-json") + 1])
            payload = {
                "animation_frame_paths": [
                    str(render_dir / "0001.avif"),
                    str(render_dir / "0002.avif"),
                ],
                "still_frame_paths": [
                    str(render_dir / "0001.avif"),
                ],
            }
            summary_path.write_text(json.dumps(payload), encoding="utf-8")

        def fake_preserve_and_scale_animation_frames(**kwargs):
            captured.update(kwargs)

        monkeypatch.setattr("holodeck.core.blender.run_blender_script", fake_run_blender_script)
        monkeypatch.setattr(
            "holodeck.core.blender.preserve_and_scale_animation_frames",
            fake_preserve_and_scale_animation_frames,
        )

        render_blend(
            blend_file=blend_file,
            output_dir=output_dir,
            animation_scale_pct=50,
        )

        assert captured["render_frame_paths"] == [render_dir / "0002.avif"]
        assert captured["output_dir"] == output_dir
        assert captured["animation_scale_pct"] == 50


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
