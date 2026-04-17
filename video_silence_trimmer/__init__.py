"""
Video Silence Trimmer - 自动检测并切除视频中的静音片段
"""

__version__ = "0.2.0"

from .config import TrimmerConfig
from .core.segment import Segment, TrimResult, MultiTrimResult
from .core.analyzer import AudioAnalyzer
from .core.cutter import VideoCutter
from .core.trimmer import VideoTrimmer, VideoLengthMismatchError

__all__ = [
    "TrimmerConfig",
    "Segment",
    "TrimResult",
    "MultiTrimResult",
    "AudioAnalyzer",
    "VideoCutter",
    "VideoTrimmer",
    "VideoLengthMismatchError",
]
