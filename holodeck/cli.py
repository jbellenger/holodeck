"""Command-line interface for Holodeck."""

from __future__ import annotations

import argparse
import subprocess
import sys
import textwrap
import webbrowser
from pathlib import Path

from .core import (
    check_player_exists,
    create_server,
    deploy_player,
    extract_blend_metadata,
    get_player_url,
    render_blend,
    write_manifest_from_frames,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="holodeck",
        description="Render Blender presentations into static Holodeck bundles.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command")
    command_parsers: list[argparse.ArgumentParser] = []

    render_parser = subparsers.add_parser(
        "render-frames",
        help="Render frames from a .blend file into an output directory.",
        description="Render frames from a .blend file into an output directory.",
    )
    _add_blend_arguments(render_parser)
    render_parser.set_defaults(func=render_frames_command)
    command_parsers.append(render_parser)

    manifest_parser = subparsers.add_parser(
        "gen-manifest",
        help="Generate manifest.json from a .blend file and rendered output.",
        description="Generate manifest.json from a .blend file and rendered output.",
    )
    _add_blend_arguments(manifest_parser)
    manifest_parser.set_defaults(func=gen_manifest_command)
    command_parsers.append(manifest_parser)

    build_parser = subparsers.add_parser(
        "build",
        help="Render frames and generate manifest.json in a single step.",
        description="Render frames and generate manifest.json in a single step.",
    )
    _add_blend_arguments(build_parser)
    build_parser.set_defaults(func=build_command)
    command_parsers.append(build_parser)

    serve_parser = subparsers.add_parser(
        "serve",
        help="Serve an output directory locally for development.",
        description="Serve an output directory locally for development.",
    )
    serve_parser.add_argument("output_dir", help="Holodeck output directory to serve.")
    serve_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind the local HTTP server to.",
    )
    serve_parser.add_argument(
        "--no-open",
        action="store_true",
        help="Do not open the player URL in a web browser.",
    )
    serve_parser.set_defaults(func=serve_command)
    command_parsers.append(serve_parser)

    parser.epilog = _build_comprehensive_help(command_parsers)

    return parser


def _build_comprehensive_help(command_parsers: list[argparse.ArgumentParser]) -> str:
    sections = "\n\n".join(_format_subcommand_help(command_parser) for command_parser in command_parsers)
    return f"Full subcommand reference:\n\n{sections}"


def _format_subcommand_help(parser: argparse.ArgumentParser) -> str:
    formatter = parser._get_formatter()
    width = formatter._width
    command_name = parser.prog.split()[-1]
    lines = [command_name]

    if parser.description:
        lines.extend(_wrap_text(parser.description, indent="  ", width=width))

    lines.append("")
    lines.extend(_format_usage_block(parser))

    positional_actions = [
        action for action in parser._positionals._group_actions if action.help != argparse.SUPPRESS
    ]
    optional_actions = [action for action in parser._optionals._group_actions if action.help != argparse.SUPPRESS]

    if positional_actions:
        lines.append("")
        lines.append("  positional arguments:")
        lines.extend(_format_action_block(parser, positional_actions, width=width))

    if optional_actions:
        lines.append("")
        lines.append("  options:")
        lines.extend(_format_action_block(parser, optional_actions, width=width))

    return "\n".join(lines)


def _format_usage_block(parser: argparse.ArgumentParser) -> list[str]:
    usage_lines = parser.format_usage().strip().splitlines()
    formatted_lines = [f"  {usage_lines[0]}"]
    formatted_lines.extend(f"  {line}" for line in usage_lines[1:])
    return formatted_lines


def _format_action_block(
    parser: argparse.ArgumentParser, actions: list[argparse.Action], width: int
) -> list[str]:
    formatter = parser._get_formatter()
    invocations = [formatter._format_action_invocation(action) for action in actions]
    help_texts = [formatter._expand_help(action) for action in actions]
    help_column = max(max(len(invocation) for invocation in invocations) + 2, 16)
    lines: list[str] = []

    for invocation, help_text in zip(invocations, help_texts):
        initial_indent = f"    {invocation.ljust(help_column)}"
        subsequent_indent = "    " + (" " * help_column)
        wrapper = textwrap.TextWrapper(
            width=width,
            initial_indent=initial_indent,
            subsequent_indent=subsequent_indent,
        )
        lines.extend(wrapper.wrap(help_text))

    return lines


def _wrap_text(text: str, indent: str, width: int) -> list[str]:
    return textwrap.wrap(
        text,
        width=width,
        initial_indent=indent,
        subsequent_indent=indent,
    )


def _add_blend_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("blend_file", help="Source .blend file.")
    parser.add_argument("output_dir", help="Holodeck output directory.")
    parser.add_argument(
        "--blender",
        default="blender",
        help="Blender executable to invoke.",
    )
    parser.add_argument(
        "--scene",
        help="Optional Blender scene name to render or inspect.",
    )


def _resolve_blend_file(blend_file: str) -> Path:
    blend_path = Path(blend_file).expanduser().resolve()
    if not blend_path.is_file():
        raise FileNotFoundError(f"Blend file not found: {blend_path}")
    return blend_path


def _resolve_output_dir(output_dir: str) -> Path:
    resolved = Path(output_dir).expanduser().resolve()
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _ensure_output_dir(output_dir: str) -> Path:
    resolved = Path(output_dir).expanduser().resolve()
    if not resolved.is_dir():
        raise FileNotFoundError(f"Output directory not found: {resolved}")
    return resolved


def render_frames_command(args: argparse.Namespace) -> int:
    blend_file = _resolve_blend_file(args.blend_file)
    output_dir = _resolve_output_dir(args.output_dir)

    deploy_player(output_dir)
    render_blend(
        blend_file=blend_file,
        output_dir=output_dir,
        blender_executable=args.blender,
        scene=args.scene,
    )

    print(f"Rendered frames into {output_dir / 'render'}")
    return 0


def gen_manifest_command(args: argparse.Namespace) -> int:
    blend_file = _resolve_blend_file(args.blend_file)
    output_dir = _resolve_output_dir(args.output_dir)

    deploy_player(output_dir)
    metadata = extract_blend_metadata(
        blend_file=blend_file,
        output_dir=output_dir,
        blender_executable=args.blender,
        scene=args.scene,
    )

    missing_frames = [Path(frame_path) for frame_path in metadata.frame_paths if not Path(frame_path).is_file()]
    if missing_frames:
        missing_preview = ", ".join(path.name for path in missing_frames[:3])
        if len(missing_frames) > 3:
            missing_preview += ", ..."
        raise FileNotFoundError(
            f"Missing {len(missing_frames)} rendered frame(s) in {output_dir / 'render'}: {missing_preview}"
        )

    manifest_path, manifest = write_manifest_from_frames(
        frame_paths=metadata.frame_paths,
        fps=metadata.fps,
        marker_frames=metadata.marker_frames,
        frame_start=metadata.frame_start,
        export_root=output_dir,
    )
    print(f"Wrote {manifest_path} with {len(manifest['frames'])} frames")
    return 0


def build_command(args: argparse.Namespace) -> int:
    render_frames_command(args)
    gen_manifest_command(args)
    return 0


def serve_command(args: argparse.Namespace) -> int:
    output_dir = _ensure_output_dir(args.output_dir)
    if not check_player_exists(output_dir):
        raise FileNotFoundError(
            f"Player assets not found in {output_dir}. Run a Holodeck build step first."
        )

    server = create_server(args.port, output_dir)
    url = get_player_url(server.server_address[1])
    print(f"Serving {output_dir} at {url}")

    if not args.no_open:
        try:
            webbrowser.open(url)
        except webbrowser.Error as exc:
            print(f"warning: could not open browser: {exc}", file=sys.stderr)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped")
    finally:
        server.server_close()

    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    parser = build_parser()
    if not argv:
        print(parser.format_help(), end="")
        return 0

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (FileNotFoundError, RuntimeError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
