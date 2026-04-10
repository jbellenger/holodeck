"""
Business logic for manifest generation.
This module contains NO bpy imports and can be tested independently.
"""
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
    ) -> Dict[str, Any]:
        """
        Generate manifest data.

        Args:
            fps: Frames per second from scene
            markers: List of zero-based marker frame indexes

        Returns:
            The generated manifest dict
        """
        return {
            "fps": fps,
            "markers": markers,
            "frames": self._relativize_paths(self.frames),
        }

    def _relativize_paths(self, frame_paths: List[str]) -> List[str]:
        """Convert absolute paths to relative paths starting from 'render/'."""
        rel_frames = []
        for fpath in frame_paths:
            try:
                idx = fpath.index("render")
                rel_frames.append(fpath[idx:])
            except ValueError:
                # Path doesn't contain 'render', preserve as-is
                rel_frames.append(fpath)
        return rel_frames

    def write_manifest(
        self,
        manifest: Dict[str, Any],
        output_path: str = "manifest.json",
    ) -> None:
        """Write manifest to JSON file."""
        output_file = Path(output_path)
        output_file.write_text(json.dumps(manifest, indent=4))
