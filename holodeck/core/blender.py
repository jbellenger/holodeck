"""Helpers for invoking Blender in background mode."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .runtime import get_package_path, get_package_root


@dataclass(frozen=True)
class BlendMetadata:
    """Blend scene metadata needed to generate a Holodeck manifest."""

    fps: int
    frame_start: int
    frame_end: int
    marker_frames: list[int]
    frame_paths: list[str]

    @property
    def frame_count(self) -> int:
        return self.frame_end - self.frame_start + 1

    @classmethod
    def from_dict(cls, payload: dict) -> "BlendMetadata":
        return cls(
            fps=int(payload["fps"]),
            frame_start=int(payload["frame_start"]),
            frame_end=int(payload["frame_end"]),
            marker_frames=[int(frame) for frame in payload["marker_frames"]],
            frame_paths=[str(path) for path in payload["frame_paths"]],
        )


def get_script_path(script_name: str) -> Path:
    """Return the path to a Blender helper script."""
    return get_package_path("blender_scripts", script_name)


def resolve_blender_executable(blender_executable: str) -> str:
    """Resolve the Blender executable path."""
    resolved = shutil.which(blender_executable)
    if resolved is None:
        raise FileNotFoundError(f"Blender executable not found on PATH: {blender_executable}")
    return resolved


def run_blender_script(
    *,
    blend_file: Path,
    script_name: str,
    blender_executable: str = "blender",
    script_args: list[str] | None = None,
) -> None:
    """Run a helper script inside Blender background mode."""
    script_path = get_script_path(script_name)
    if not script_path.is_file():
        raise FileNotFoundError(f"Blender helper script not found: {script_path}")

    blender_path = resolve_blender_executable(blender_executable)
    command = [
        blender_path,
        "-b",
        "--python-use-system-env",
        str(blend_file),
        "--python",
        str(script_path),
    ]
    if script_args:
        command.extend(["--", *script_args])

    env = os.environ.copy()
    package_parent = str(get_package_root().parent)
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        os.pathsep.join([package_parent, existing_pythonpath])
        if existing_pythonpath
        else package_parent
    )

    subprocess.run(command, check=True, env=env)


def render_blend(
    *,
    blend_file: Path,
    output_dir: Path,
    blender_executable: str = "blender",
    scene: str | None = None,
) -> None:
    """Render frames for a blend file into the output directory."""
    script_args = ["--output", str(output_dir)]
    if scene:
        script_args.extend(["--scene", scene])

    run_blender_script(
        blend_file=blend_file,
        script_name="render_frames.py",
        blender_executable=blender_executable,
        script_args=script_args,
    )


def extract_blend_metadata(
    *,
    blend_file: Path,
    output_dir: Path,
    blender_executable: str = "blender",
    scene: str | None = None,
) -> BlendMetadata:
    """Extract frame and marker metadata from a blend file."""
    with tempfile.TemporaryDirectory(prefix="holodeck-") as temp_dir:
        json_output = Path(temp_dir) / "blend-metadata.json"
        script_args = ["--output", str(output_dir), "--json-output", str(json_output)]
        if scene:
            script_args.extend(["--scene", scene])

        run_blender_script(
            blend_file=blend_file,
            script_name="extract_blend_metadata.py",
            blender_executable=blender_executable,
            script_args=script_args,
        )

        payload = json.loads(json_output.read_text(encoding="utf-8"))
        return BlendMetadata.from_dict(payload)
