"""
Business logic for manifest generation.
This module contains NO bpy imports and can be tested independently.
"""
import hashlib
import json
from pathlib import Path
from typing import List, Dict, Any, Optional


class ManifestGenerator:
    """Handles manifest generation logic independent of Blender."""

    def __init__(self):
        self.frames: List[str] = []

    def reset(self) -> None:
        """Clear frame list for next render."""
        self.frames = []

    def add_frame(self, frame_path: Optional[str]) -> None:
        """Record a rendered frame path."""
        if frame_path:
            self.frames.append(frame_path)

    def normalize_markers(
        self,
        marker_frames: List[int],
        frame_start: int,
    ) -> List[int]:
        """
        Convert Blender timeline frame numbers into zero-based frame indexes.

        Markers outside the rendered frame range are ignored.
        """
        frame_count = len(self.frames)
        if frame_count == 0:
            return []

        marker_indexes = []
        for frame in sorted(marker_frames):
            frame_index = frame - frame_start
            if 0 <= frame_index < frame_count:
                marker_indexes.append(frame_index)

        return marker_indexes

    def generate_manifest(
        self,
        fps: int,
        markers: List[int],
        root_dir: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """
        Generate manifest data.

        Args:
            fps: Frames per second from scene
            markers: List of zero-based marker frame indexes

        Returns:
            The generated manifest dict
        """
        manifest = {
            "fps": fps,
            "markers": markers,
            "frames": self._relativize_paths(self.frames, root_dir=root_dir),
        }
        manifest["token"] = self._build_token(manifest, root_dir=root_dir)
        return manifest

    def _build_token(
        self,
        manifest: Dict[str, Any],
        root_dir: Optional[Path] = None,
    ) -> str:
        """Build a stable token that changes whenever the manifest or rendered files change."""
        token_source = {
            "manifest": manifest,
            "frame_fingerprints": self._build_frame_fingerprints(
                manifest["frames"],
                root_dir=root_dir,
            ),
        }
        token_payload = json.dumps(token_source, separators=(",", ":"), sort_keys=True).encode("utf-8")
        return hashlib.sha256(token_payload).hexdigest()[:12]

    def _build_frame_fingerprints(
        self,
        frame_paths: List[str],
        root_dir: Optional[Path] = None,
    ) -> List[Dict[str, Any]]:
        """
        Capture lightweight file metadata for cache busting.

        The player serves frame URLs as immutable for aggressive browser caching, so
        the manifest token must change when a frame is overwritten in place.
        """
        fingerprints = []
        resolved_root = root_dir.resolve() if root_dir else None

        for frame_path in frame_paths:
            candidate_path = self._resolve_frame_path(frame_path, resolved_root)
            fingerprint: Dict[str, Any] = {"path": frame_path}

            if candidate_path is not None:
                try:
                    stat = candidate_path.stat()
                except OSError:
                    pass
                else:
                    fingerprint["size"] = stat.st_size
                    fingerprint["mtime_ns"] = stat.st_mtime_ns

            fingerprints.append(fingerprint)

        return fingerprints

    def _resolve_frame_path(
        self,
        frame_path: str,
        root_dir: Optional[Path] = None,
    ) -> Optional[Path]:
        path = Path(frame_path)
        if path.is_absolute():
            return path
        if root_dir is not None:
            return root_dir / path
        return None

    def _relativize_paths(
        self,
        frame_paths: List[str],
        root_dir: Optional[Path] = None,
    ) -> List[str]:
        """Convert frame paths to browser-safe relative paths when possible."""
        rel_frames = []
        resolved_root = root_dir.resolve() if root_dir else None
        for fpath in frame_paths:
            frame_path = Path(fpath)
            if resolved_root and frame_path.is_absolute():
                try:
                    rel_frames.append(frame_path.resolve().relative_to(resolved_root).as_posix())
                    continue
                except ValueError:
                    pass

            rel_frames.append(frame_path.as_posix())
        return rel_frames

    def write_manifest(
        self,
        manifest: Dict[str, Any],
        output_path: str = "manifest.json",
    ) -> None:
        """Write manifest to JSON file."""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(json.dumps(manifest, indent=4), encoding="utf-8")
