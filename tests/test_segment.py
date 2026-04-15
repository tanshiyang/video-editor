"""片段模型测试"""

import pytest
from video_silence_trimmer.core.segment import Segment, TrimResult


class TestSegment:
    """Segment 测试"""

    def test_segment_duration(self):
        seg = Segment(start=1.0, end=3.5, is_silent=False)
        assert seg.duration == 2.5

    def test_segment_repr(self):
        seg = Segment(start=0.0, end=2.0, is_silent=True)
        assert "静音" in repr(seg)
        assert "0.00s - 2.00s" in repr(seg)


class TestTrimResult:
    """TrimResult 测试"""

    def test_removed_duration(self):
        result = TrimResult(
            original_duration=10.0,
            output_duration=6.0,
            removed_segments=[
                Segment(2.0, 5.0, is_silent=True),
                Segment(7.0, 8.0, is_silent=True),
            ],
            kept_segments=[],
        )
        assert result.removed_duration == 4.0

    def test_compression_ratio(self):
        result = TrimResult(
            original_duration=10.0,
            output_duration=5.0,
        )
        assert result.compression_ratio == 0.5

    def test_compression_ratio_zero_duration(self):
        result = TrimResult(original_duration=0, output_duration=0)
        assert result.compression_ratio == 0.0
