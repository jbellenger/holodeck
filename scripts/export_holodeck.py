"""
Render a Blender presentation into a static Holodeck export directory.

Usage:
    blender -b presentation.blend --python scripts/export_holodeck.py -- --output build/holodeck
"""
import argparse
import sys
from pathlib import Path

import bpy


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Export a Holodeck bundle from a .blend file")
    parser.add_argument(
        "--output",
        required=True,
        help="Directory that will contain index.html, manifest.json, and render/",
    )
    parser.add_argument(
        "--scene",
        help="Optional Blender scene name to render instead of the active scene",
    )
    return parser.parse_args(argv)


def main(argv):
    args = parse_args(argv)

    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from holodeck.core import deploy_player, get_render_dir
    from holodeck.handlers import render_handlers

    output_dir = Path(args.output).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    deploy_player(output_dir)

    scene = bpy.data.scenes[args.scene] if args.scene else bpy.context.scene

    scene[_OUTPUT_ROOT_KEY] = str(output_dir)
    scene.render.filepath = str(get_render_dir(output_dir)) + "/"

    render_handlers.register()
    try:
        bpy.ops.render.render(animation=True, scene=scene.name)
    finally:
        render_handlers.unregister()


_OUTPUT_ROOT_KEY = "holodeck_output_root"


if __name__ == "__main__":
    argv = sys.argv
    args = argv[argv.index("--") + 1 :] if "--" in argv else []
    main(args)
