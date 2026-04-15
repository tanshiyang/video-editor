"""
Video Silence Trimmer - 自动检测并切除视频中的静音片段
"""

__version__ = "0.1.0"

from .config import TrimmerConfig
from .core.segment import Segment, TrimResult
from .core.analyzer import AudioAnalyzer
from .core.cutter import VideoCutter
from .core.trimmer import VideoTrimmer

__all__ = [
    "TrimmerConfig",
    "Segment",
    "TrimResult",
    "AudioAnalyzer",
    "VideoCutter",
    "VideoTrimmer",
]
