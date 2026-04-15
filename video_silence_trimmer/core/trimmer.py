"""主入口模块 - 整合分析器和剪切器"""

import time
from pathlib import Path
from typing import Optional

from loguru import logger

from ..config import TrimmerConfig
from ..utils.ffmpeg_utils import get_video_duration, get_video_info
from .analyzer import AudioAnalyzer, NoAudioStreamError
from .cutter import VideoCutter
from .segment import Segment, TrimResult


class VideoTrimmer:
    """视频静音切除器 - 主入口类"""

    def __init__(self, config: Optional[TrimmerConfig] = None):
        """初始化

        Args:
            config: 配置对象，如果为 None 则使用默认配置
        """
        self.config = config or TrimmerConfig()
        self.analyzer = AudioAnalyzer(self.config)
        self.cutter = VideoCutter(self.config)

    def trim(
        self,
        input_video: Path,
        output_video: Path,
    ) -> TrimResult:
        """执行静音切除

        Args:
            input_video: 输入视频路径
            output_video: 输出视频路径

        Returns:
            TrimResult 结果对象
        """
        start_time = time.time()

        input_video = Path(input_video)
        output_video = Path(output_video)

        logger.info(f"处理视频: {input_video} -> {output_video}")

        # 获取原始时长
        original_duration = get_video_duration(input_video)

        # 分析音频
        silence_segments, kept_segments = self.analyzer.analyze(input_video)

        # 执行剪切
        output_duration = self.cutter.cut(
            input_video,
            kept_segments,
            output_video,
        )

        processing_time = time.time() - start_time

        result = TrimResult(
            original_duration=original_duration,
            output_duration=output_duration,
            removed_segments=silence_segments,
            kept_segments=kept_segments,
            processing_time=processing_time,
        )

        logger.info(f"处理完成: {result}")

        return result

    def analyze(
        self,
        input_video: Path,
    ) -> dict:
        """仅分析不剪切（dry-run 模式）

        Args:
            input_video: 输入视频路径

        Returns:
            分析结果字典
        """
        input_video = Path(input_video)
        return self.analyzer.analyze_dry_run(input_video)
