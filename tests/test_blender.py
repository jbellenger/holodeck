"""Tests for Blender subprocess helpers."""

import json
import os
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

        def fake_run(command, check, env):
            captured["command"] = command
            captured["check"] = check
            captured["env"] = env

        monkeypatch.setattr("holodeck.core.blender.subprocess.run", fake_run)

        run_blender_script(
            blend_file=blend_file,
            script_name="helper.py",
            script_args=["--output", str(tmp_path / "out")],
        )

        assert captured["check"] is True
        assert captured["command"] == [
            "/usr/bin/blender",
            "-b",
            "--python-use-system-env",
            str(blend_file),
            "--python",
            str(helper_script),
            "--",
            "--output",
            str(tmp_path / "out"),
        ]
        assert captured["env"]["PYTHONPATH"].split(os.pathsep)[0] == str(tmp_path / "package-root")


class TestRenderBlend:
    def test_uses_render_script(self, monkeypatch, tmp_path):
        blend_file = tmp_path / "demo.blend"
        blend_file.touch()
        output_dir = tmp_path / "dist"
        captured = {}

        def fake_run_blender_script(**kwargs):
            captured.update(kwargs)

        monkeypatch.setattr("holodeck.core.blender.run_blender_script", fake_run_blender_script)

        render_blend(blend_file=blend_file, output_dir=output_dir, scene="Deck", res_pct=50)

        assert captured["blend_file"] == blend_file
        assert captured["script_name"] == "render_frames.py"
        assert captured["script_args"] == [
            "--output",
            str(output_dir),
            "--res-pct",
            "50",
            "--scene",
            "Deck",
        ]


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
