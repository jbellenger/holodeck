import pytest

from holodeck.core.frame_spec import parse_frame_spec


class TestParseFrameSpec:
    def test_single_frame(self):
        assert parse_frame_spec("4") == [4]

    def test_range_is_inclusive(self):
        assert parse_frame_spec("4-10") == [4, 5, 6, 7, 8, 9, 10]

    def test_comma_list(self):
        assert parse_frame_spec("1,2,3") == [1, 2, 3]

    def test_mixed_segments_preserve_order(self):
        assert parse_frame_spec("7,1-3,5") == [7, 1, 2, 3, 5]

    def test_range_with_equal_endpoints(self):
        assert parse_frame_spec("5-5") == [5]

    def test_whitespace_is_tolerated(self):
        assert parse_frame_spec(" 1 , 3-4 ") == [1, 3, 4]

    @pytest.mark.parametrize(
        "spec",
        ["", " ", ",", "1,", "-", "1-", "-3", "a", "1-2-3", "1,,2", "1.5"],
    )
    def test_invalid_spec_raises(self, spec):
        with pytest.raises(ValueError):
            parse_frame_spec(spec)

    def test_reverse_range_raises(self):
        with pytest.raises(ValueError, match="start > end"):
            parse_frame_spec("10-4")
