import pytest

from holodeck.core.frame_selection import (
    canonical_still_frames,
    split_animation_and_still_frames,
)


def test_canonical_still_frames_include_first_markers_and_last():
    frames = canonical_still_frames(
        frame_start=10,
        frame_end=20,
        marker_frames=[10, 12, 20, 99, 5, 12],
    )

    assert frames == [10, 12, 20]


def test_canonical_still_frames_reject_invalid_ranges():
    with pytest.raises(ValueError, match="Frame end"):
        canonical_still_frames(frame_start=20, frame_end=10, marker_frames=[])


def test_split_animation_and_still_frames_uses_two_pass_policy():
    animation_frames, still_frames = split_animation_and_still_frames(
        [10, 11, 12, 12, 20, 21],
        frame_start=10,
        frame_end=20,
        marker_frames=[12],
    )

    assert animation_frames == [10, 11, 12, 20, 21]
    assert still_frames == [10, 12, 20]
