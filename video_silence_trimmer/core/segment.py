"""片段模型定义"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict


@dataclass
class Segment:
    """视频片段"""

    start: float
    """起始时间（秒）"""

    end: float
    """结束时间（秒）"""

    is_silent: bool = False
    """是否为静音片段"""

    @property
    def duration(self) -> float:
        """片段时长（秒）"""
        return self.end - self.start

    def __repr__(self) -> str:
        silent_str = "静音" if self.is_silent else "有声"
        return f"Segment({self.start:.2f}s - {self.end:.2f}s, {silent_str}, 时长={self.duration:.2f}s)"


@dataclass
class TrimResult:
    """剪切结果"""

    original_duration: float
    """原始视频时长（秒）"""

    output_duration: float
    """输出视频时长（秒）"""

    removed_segments: List[Segment] = field(default_factory=list)
    """被切除的片段列表"""

    kept_segments: List[Segment] = field(default_factory=list)
    """保留的片段列表"""

    processing_time: float = 0.0
    """处理耗时（秒）"""

    @property
    def removed_duration(self) -> float:
        """被切除的总时长"""
        return sum(seg.duration for seg in self.removed_segments)

    @property
    def compression_ratio(self) -> float:
        """压缩比（输出时长/原始时长）"""
        if self.original_duration == 0:
            return 0.0
        return self.output_duration / self.original_duration

    def __repr__(self) -> str:
        return (
            f"TrimResult(\n"
            f"  原始时长: {self.original_duration:.2f}s\n"
            f"  输出时长: {self.output_duration:.2f}s\n"
            f"  切除时长: {self.removed_duration:.2f}s\n"
            f"  压缩比: {self.compression_ratio:.1%}\n"
            f"  切除片段数: {len(self.removed_segments)}\n"
            f"  保留片段数: {len(self.kept_segments)}\n"
            f"  处理耗时: {self.processing_time:.2f}s\n"
            f")"
        )


@dataclass
class MultiTrimResult:
    """多视频联动剪切结果"""

    main_result: TrimResult
    """主视频剪切结果"""

    secondary_results: Dict[str, TrimResult] = field(default_factory=dict)
    """副视频剪切结果 {文件名: 结果}"""

    total_processing_time: float = 0.0
    """总处理耗时（秒）"""

    def __repr__(self) -> str:
        return (
            f"MultiTrimResult(\n"
            f"  主视频: {self.main_result.original_duration:.2f}s -> {self.main_result.output_duration:.2f}s\n"
            f"  副视频数: {len(self.secondary_results)}\n"
            f"  总处理耗时: {self.total_processing_time:.2f}s\n"
            f")"
        )
