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


class TestAudioUtils:
    """音频工具测试"""

    def test_db_conversion(self):
        from video_silence_trimmer.utils.audio_utils import db_to_amplitude, amplitude_to_db
        
        # 测试分贝转换
        assert abs(db_to_amplitude(0) - 1.0) < 1e-6
        assert abs(amplitude_to_db(1.0) - 0) < 1e-6
        assert abs(amplitude_to_db(0.1) - (-20)) < 1e-6

    def test_detect_silence_frames(self):
        import numpy as np
        from video_silence_trimmer.utils.audio_utils import detect_silence_frames
        
        # 创建测试RMS数据
        rms = np.array([0.01, 0.5, 0.01, 0.01])  # -40dB, -6dB, -40dB, -40dB
        
        # 测试基本阈值检测
        is_silent = detect_silence_frames(rms, threshold_db=-20.0)
        expected = np.array([True, False, True, True])
        np.testing.assert_array_equal(is_silent, expected)

    def test_merge_silence_intervals_edge_cases(self):
        from video_silence_trimmer.utils.audio_utils import merge_silence_intervals
        import numpy as np
        
        # 测试空输入
        result = merge_silence_intervals(
            np.array([]), np.array([]), min_duration=0.5
        )
        assert result == []
        
        # 测试全程静音
        is_silent = np.array([True, True, True])
        times = np.array([0.0, 0.1, 0.2])
        result = merge_silence_intervals(is_silent, times, min_duration=0.1)
        assert len(result) == 1
        assert result[0] == (0.0, 0.2 + 512/16000)  # 加上帧持续时间

    def test_invert_silence_intervals(self):
        from video_silence_trimmer.utils.audio_utils import invert_silence_intervals
        
        # 测试基本反转
        silence_intervals = [(1.0, 2.0), (3.0, 4.0)]
        result = invert_silence_intervals(silence_intervals, 5.0)
        expected = [(0.0, 1.0), (2.0, 3.0), (4.0, 5.0)]
        assert result == expected
        
        # 测试无静音区间
        result = invert_silence_intervals([], 5.0)
        assert result == [(0.0, 5.0)]
