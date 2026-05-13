import importlib.util
from pathlib import Path


ADDON_PATH = Path(__file__).resolve().parents[1] / "blender-support" / "nla_frame_tools.py"


def load_addon():
    spec = importlib.util.spec_from_file_location("nla_frame_tools_under_test", ADDON_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeStrip:
    def __init__(self, name, frame_start, frame_end):
        self.name = name
        self.frame_start = float(frame_start)
        self.frame_end = float(frame_end)


class FakeTrack:
    def __init__(self, name, strips):
        self.name = name
        self.strips = strips


class FakeAnimationData:
    def __init__(self, tracks):
        self.nla_tracks = tracks


class FakeSource:
    def __init__(self, name, tracks):
        self.name = name
        self.animation_data = FakeAnimationData(tracks)


class FakeMarker:
    def __init__(self, frame):
        self.frame = frame


def frames(strips):
    return [(strip.name, strip.frame_start, strip.frame_end) for strip in strips]


def test_insert_moves_strips_from_right_to_left_without_shortening():
    addon = load_addon()
    strips = [
        FakeStrip("A", 100, 119),
        FakeStrip("B", 125, 144),
    ]
    source = FakeSource("Object", [FakeTrack("Track", strips)])

    report = addon.shift_sources_and_markers([source], [], current_frame=90, frame_delta=20)

    assert report.shifted_strips == 2
    assert report.skipped_strips == 0
    assert frames(strips) == [
        ("A", 120, 139),
        ("B", 145, 164),
    ]


def test_delete_uses_deleted_range_cutoff_instead_of_moving_inside_range():
    addon = load_addon()
    strips = [
        FakeStrip("before", 80, 99),
        FakeStrip("inside_deleted_range", 105, 124),
    ]
    source = FakeSource("Object", [FakeTrack("Track", strips)])

    report = addon.shift_sources_and_markers([source], [], current_frame=100, frame_delta=-10)

    assert report.shifted_strips == 0
    assert report.skipped_strips == 0
    assert frames(strips) == [
        ("before", 80, 99),
        ("inside_deleted_range", 105, 124),
    ]


def test_delete_shifts_strips_after_deleted_range_when_target_is_clear():
    addon = load_addon()
    strips = [
        FakeStrip("before", 80, 99),
        FakeStrip("after_deleted_range", 115, 134),
    ]
    source = FakeSource("Object", [FakeTrack("Track", strips)])

    report = addon.shift_sources_and_markers([source], [], current_frame=100, frame_delta=-10)

    assert report.shifted_strips == 1
    assert report.skipped_strips == 0
    assert frames(strips) == [
        ("before", 80, 99),
        ("after_deleted_range", 105, 124),
    ]


def test_delete_skips_shift_that_would_overlap_instead_of_clamping_strip():
    addon = load_addon()
    strips = [
        FakeStrip("straddling", 80, 105),
        FakeStrip("after_deleted_range", 110, 129),
    ]
    source = FakeSource("Object", [FakeTrack("Track", strips)])

    report = addon.shift_sources_and_markers([source], [], current_frame=100, frame_delta=-10)

    assert report.shifted_strips == 0
    assert report.skipped_strips == 1
    assert "would overlap straddling" in report.warnings[0]
    assert frames(strips) == [
        ("straddling", 80, 105),
        ("after_deleted_range", 110, 129),
    ]


def test_insert_shifts_markers_after_playhead_only():
    addon = load_addon()
    markers = [FakeMarker(100), FakeMarker(101), FakeMarker(125)]

    report = addon.shift_sources_and_markers([], markers, current_frame=100, frame_delta=10)

    assert report.shifted_markers == 2
    assert [marker.frame for marker in markers] == [100, 111, 135]


def test_delete_clamps_markers_inside_deleted_range_and_shifts_later_markers():
    addon = load_addon()
    markers = [FakeMarker(100), FakeMarker(105), FakeMarker(110), FakeMarker(125)]

    report = addon.shift_sources_and_markers([], markers, current_frame=100, frame_delta=-10)

    assert report.clamped_markers == 2
    assert report.shifted_markers == 1
    assert [marker.frame for marker in markers] == [100, 100, 100, 115]
