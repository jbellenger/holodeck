"""
Shared export helpers for interactive and headless Holodeck workflows.
"""
from pathlib import Path
from typing import Iterable, Optional, Tuple, Dict, Any

from .manifest_generator import ManifestGenerator

DEFAULT_MANIFEST_FILENAME = "manifest.json"
DEFAULT_RENDER_DIRNAME = "render"


def get_render_dir(
    export_root: Path,
    render_dirname: str = DEFAULT_RENDER_DIRNAME,
) -> Path:
    """Return the render directory inside an export root."""
    return export_root / render_dirname


def resolve_export_root(
    frame_paths: Iterable[str],
    blend_filepath: Optional[str] = None,
    export_root: Optional[Path] = None,
    render_dirname: str = DEFAULT_RENDER_DIRNAME,
) -> Path:
    """
    Determine the export root that should contain index.html and manifest.json.
    """
    if export_root is not None:
        return Path(export_root)

    frame_paths = list(frame_paths)
    if frame_paths:
        frame_dir = Path(frame_paths[0]).parent
        if frame_dir.name == render_dirname:
            return frame_dir.parent
        return frame_dir

    if blend_filepath:
        blend_path = Path(blend_filepath)
        if blend_path.exists():
            return blend_path.parent

    raise ValueError("Unable to determine Holodeck export root")


def finalize_render_export(
    generator: ManifestGenerator,
    fps: int,
    marker_frames: Iterable[int],
    frame_start: int,
    blend_filepath: Optional[str] = None,
    export_root: Optional[Path] = None,
    render_dirname: str = DEFAULT_RENDER_DIRNAME,
) -> Tuple[Path, Dict[str, Any]]:
    """
    Build and write the Holodeck manifest for a completed render.
    """
    resolved_root = resolve_export_root(
        frame_paths=generator.frames,
        blend_filepath=blend_filepath,
        export_root=export_root,
        render_dirname=render_dirname,
    )
    markers = generator.normalize_markers(list(marker_frames), frame_start)
    manifest = generator.generate_manifest(fps, markers, root_dir=resolved_root)
    manifest_path = resolved_root / DEFAULT_MANIFEST_FILENAME
    generator.write_manifest(manifest, str(manifest_path))
    return manifest_path, manifest


def build_manifest_from_frames(
    frame_paths: Iterable[str],
    fps: int,
    marker_frames: Iterable[int],
    frame_start: int,
    export_root: Path,
) -> Dict[str, Any]:
    """Build a manifest from a fixed list of rendered frame paths."""
    generator = ManifestGenerator()
    for frame_path in frame_paths:
        generator.add_frame(frame_path)

    markers = generator.normalize_markers(list(marker_frames), frame_start)
    return generator.generate_manifest(fps, markers, root_dir=export_root)


def write_manifest_from_frames(
    frame_paths: Iterable[str],
    fps: int,
    marker_frames: Iterable[int],
    frame_start: int,
    export_root: Path,
) -> Tuple[Path, Dict[str, Any]]:
    """Write a manifest from a fixed list of rendered frame paths."""
    manifest = build_manifest_from_frames(
        frame_paths=frame_paths,
        fps=fps,
        marker_frames=marker_frames,
        frame_start=frame_start,
        export_root=export_root,
    )
    manifest_path = Path(export_root) / DEFAULT_MANIFEST_FILENAME
    ManifestGenerator().write_manifest(manifest, str(manifest_path))
    return manifest_path, manifest
