"""Helpers for selecting Holodeck animation and still frames."""

from __future__ import annotations

from collections.abc import Iterable


def canonical_still_frames(
    frame_start: int,
    frame_end: int,
    marker_frames: Iterable[int],
) -> list[int]:
    """Return first, in-range marker, and last frames in timeline order."""
    if frame_end < frame_start:
        raise ValueError("Frame end must be greater than or equal to frame start.")

    still_frames = {frame_start, frame_end}
    still_frames.update(
        frame for frame in marker_frames if frame_start <= frame <= frame_end
    )
    return sorted(still_frames)


def split_animation_and_still_frames(
    frames: Iterable[int],
    *,
    frame_start: int,
    frame_end: int,
    marker_frames: Iterable[int],
) -> tuple[list[int], list[int]]:
    """Return animation-pass frames and still-pass frames for a request."""
    still_frame_set = set(canonical_still_frames(frame_start, frame_end, marker_frames))
    animation_frames: list[int] = []
    still_frames: list[int] = []
    seen_frames: set[int] = set()

    for frame in frames:
        if frame in seen_frames:
            continue
        seen_frames.add(frame)

        animation_frames.append(frame)

        if frame in still_frame_set:
            still_frames.append(frame)

    return animation_frames, still_frames
