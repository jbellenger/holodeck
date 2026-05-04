"""Parse Blender-style frame selection specifiers."""

from __future__ import annotations


def parse_frame_spec(spec: str) -> list[int]:
    """Expand a spec like ``"4"``, ``"4-10"``, or ``"1,2,5-7"`` into frame numbers.

    Ranges are inclusive and segments are preserved in the order they appear.
    """
    if spec is None:
        raise ValueError("Frame spec must not be empty.")

    segments = [segment.strip() for segment in spec.split(",")]
    if not segments or any(segment == "" for segment in segments):
        raise ValueError(f"Invalid frame spec: {spec!r}")

    frames: list[int] = []
    for segment in segments:
        if "-" in segment:
            start_str, _, end_str = segment.partition("-")
            start = _parse_positive_int(start_str, segment)
            end = _parse_positive_int(end_str, segment)
            if start > end:
                raise ValueError(f"Invalid frame range: {segment!r} (start > end)")
            frames.extend(range(start, end + 1))
        else:
            frames.append(_parse_positive_int(segment, segment))

    return frames


def _parse_positive_int(value: str, segment: str) -> int:
    stripped = value.strip()
    if not stripped or not stripped.isdigit():
        raise ValueError(f"Invalid frame segment: {segment!r}")
    return int(stripped)
