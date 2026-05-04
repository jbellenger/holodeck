"""Render frames for a blend file into a Holodeck output directory."""

import argparse
import sys
from pathlib import Path

import bpy

from holodeck.core.frame_spec import parse_frame_spec
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
    parser.add_argument(
        "--res-pct",
        type=int,
        default=100,
        help="Resolution percentage override for rendering.",
    )
    parser.add_argument(
        "--frames",
        help="Optional frame spec (e.g. '4', '4-10', '1,2,3') to render only those frames.",
    )
    return parser.parse_args(argv)


def main(argv):
    args = parse_args(argv)
    output_dir = Path(args.output).expanduser().resolve()
    render_dir = output_dir / "render"
    render_dir.mkdir(parents=True, exist_ok=True)

    if args.res_pct <= 0:
        raise ValueError("Resolution percentage must be a positive integer.")

    scene = bpy.data.scenes[args.scene] if args.scene else bpy.context.scene
    configure_scene_for_holodeck_render(
        scene,
        render_dir,
        resolution_percentage=args.res_pct,
    )

    if args.frames:
        for frame in parse_frame_spec(args.frames):
            scene.frame_set(frame)
            scene.render.filepath = f"{render_dir}/{frame:04d}"
            bpy.ops.render.render(write_still=True, scene=scene.name)
    else:
        bpy.ops.render.render(animation=True, scene=scene.name)


if __name__ == "__main__":
    argv = sys.argv
    args = argv[argv.index("--") + 1 :] if "--" in argv else []
    main(args)
