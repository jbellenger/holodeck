"""Render frames for a blend file into a Holodeck output directory."""

import argparse
import sys
from pathlib import Path

import bpy

from holodeck.core.render_settings import configure_scene_for_holodeck_render


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Render Holodeck frames from a .blend file")
    parser.add_argument(
        "--output",
        required=True,
        help="Directory that will contain the render/ directory.",
    )
    parser.add_argument(
        "--scene",
        help="Optional Blender scene name to render instead of the active scene.",
    )
    return parser.parse_args(argv)


def main(argv):
    args = parse_args(argv)
    output_dir = Path(args.output).expanduser().resolve()
    render_dir = output_dir / "render"
    render_dir.mkdir(parents=True, exist_ok=True)

    scene = bpy.data.scenes[args.scene] if args.scene else bpy.context.scene
    configure_scene_for_holodeck_render(scene, render_dir)
    bpy.ops.render.render(animation=True, scene=scene.name)


if __name__ == "__main__":
    argv = sys.argv
    args = argv[argv.index("--") + 1 :] if "--" in argv else []
    main(args)
