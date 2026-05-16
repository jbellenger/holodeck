"""Render frames for a blend file into a Holodeck output directory."""

import argparse
import sys
from pathlib import Path

import bpy

from holodeck.core.frame_selection import (
    canonical_still_frames,
    split_animation_and_still_frames,
)
from holodeck.core.frame_spec import parse_frame_spec
from holodeck.core.render_settings import (
    DEFAULT_ANIMATION_RESOLUTION_PERCENTAGE,
    DEFAULT_STILL_RESOLUTION_PERCENTAGE,
    RENDERER_CHOICES,
    configure_scene_for_holodeck_render,
)


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
        "--animation-res-pct",
        type=int,
        default=DEFAULT_ANIMATION_RESOLUTION_PERCENTAGE,
        help="Resolution percentage for animation frames.",
    )
    parser.add_argument(
        "--still-res-pct",
        type=int,
        default=DEFAULT_STILL_RESOLUTION_PERCENTAGE,
        help="Resolution percentage for first, marker, and last frames.",
    )
    parser.add_argument(
        "--animation-renderer",
        choices=RENDERER_CHOICES,
        help="Optional renderer override for animation frames.",
    )
    parser.add_argument(
        "--still-renderer",
        choices=RENDERER_CHOICES,
        help="Optional renderer override for first, marker, and last frames.",
    )
    parser.add_argument(
        "--frames",
        help="Optional frame spec (e.g. '4', '4-10', '1,2,3') to render only those frames.",
    )
    parser.add_argument(
        "--stills-only",
        action="store_true",
        help="Render only first, timeline marker, and last frames.",
    )
    return parser.parse_args(argv)


def main(argv):
    args = parse_args(argv)
    output_dir = Path(args.output).expanduser().resolve()
    render_dir = output_dir / "render"
    render_dir.mkdir(parents=True, exist_ok=True)

    if args.animation_res_pct <= 0:
        raise ValueError("Animation resolution percentage must be a positive integer.")
    if args.still_res_pct <= 0:
        raise ValueError("Still resolution percentage must be a positive integer.")

    scene = bpy.data.scenes[args.scene] if args.scene else bpy.context.scene
    original_renderer = scene.render.engine

    selected_frame_modes = [
        mode
        for mode, enabled in (
            ("--frames", bool(args.frames)),
            ("--stills-only", args.stills_only),
        )
        if enabled
    ]
    if len(selected_frame_modes) > 1:
        raise ValueError(f"Cannot combine {', '.join(selected_frame_modes)}.")

    still_frames = canonical_still_frames(
        scene.frame_start,
        scene.frame_end,
        _timeline_marker_frames(scene),
    )
    if args.frames:
        animation_frames, still_pass_frames = split_animation_and_still_frames(
            parse_frame_spec(args.frames),
            frame_start=scene.frame_start,
            frame_end=scene.frame_end,
            marker_frames=_timeline_marker_frames(scene),
        )
    elif args.stills_only:
        animation_frames = still_frames
        still_pass_frames = still_frames
    else:
        animation_frames = None
        still_pass_frames = still_frames

    _configure_render_pass(
        scene,
        render_dir,
        resolution_percentage=args.animation_res_pct,
        renderer=args.animation_renderer,
        original_renderer=original_renderer,
    )
    _render_frames(scene, render_dir, animation_frames)

    _configure_render_pass(
        scene,
        render_dir,
        resolution_percentage=args.still_res_pct,
        renderer=args.still_renderer,
        original_renderer=original_renderer,
    )
    _render_frames(scene, render_dir, still_pass_frames)


def _configure_render_pass(
    scene,
    render_dir,
    *,
    resolution_percentage,
    renderer,
    original_renderer,
):
    if renderer is None:
        scene.render.engine = original_renderer

    configure_scene_for_holodeck_render(
        scene,
        render_dir,
        resolution_percentage=resolution_percentage,
        renderer=renderer,
    )


def _render_frames(scene, render_dir, frames):
    if frames is None:
        bpy.ops.render.render(animation=True, scene=scene.name)
        return

    for frame in frames:
        scene.frame_set(frame)
        scene.render.filepath = f"{render_dir}/{frame:04d}"
        bpy.ops.render.render(write_still=True, scene=scene.name)


def _timeline_marker_frames(scene):
    return {
        marker.frame
        for marker in scene.timeline_markers
        if scene.frame_start <= marker.frame <= scene.frame_end
    }


if __name__ == "__main__":
    argv = sys.argv
    args = argv[argv.index("--") + 1 :] if "--" in argv else []
    main(args)
