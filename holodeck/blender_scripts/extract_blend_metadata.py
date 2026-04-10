"""Extract Holodeck manifest metadata from a blend file."""

import argparse
import json
import sys
from pathlib import Path

import bpy

from holodeck.core.render_settings import configure_scene_for_holodeck_render


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Extract Holodeck metadata from a .blend file")
    parser.add_argument(
        "--output",
        required=True,
        help="Holodeck output directory containing render/.",
    )
    parser.add_argument(
        "--json-output",
        required=True,
        help="Path to a JSON file that will receive the extracted metadata.",
    )
    parser.add_argument(
        "--scene",
        help="Optional Blender scene name to inspect instead of the active scene.",
    )
    return parser.parse_args(argv)


def main(argv):
    args = parse_args(argv)
    output_dir = Path(args.output).expanduser().resolve()
    render_dir = output_dir / "render"
    render_dir.mkdir(parents=True, exist_ok=True)

    scene = bpy.data.scenes[args.scene] if args.scene else bpy.context.scene
    configure_scene_for_holodeck_render(scene, render_dir)

    frame_paths = [
        scene.render.frame_path(frame=frame_number)
        for frame_number in range(scene.frame_start, scene.frame_end + 1)
    ]
    payload = {
        "fps": scene.render.fps,
        "frame_start": scene.frame_start,
        "frame_end": scene.frame_end,
        "marker_frames": sorted(marker.frame for marker in scene.timeline_markers),
        "frame_paths": frame_paths,
    }

    json_output = Path(args.json_output).expanduser().resolve()
    json_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(payload), encoding="utf-8")


if __name__ == "__main__":
    argv = sys.argv
    args = argv[argv.index("--") + 1 :] if "--" in argv else []
    main(args)
