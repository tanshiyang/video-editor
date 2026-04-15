"""视频剪切与合并模块"""

import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import List, Optional

from loguru import logger

from ..config import TrimmerConfig
from ..utils.ffmpeg_utils import cut_segment, concat_segments, get_video_duration
from .segment import Segment


class VideoCutter:
    """视频剪切器 - 执行实际的剪切和合并"""

    def __init__(self, config: TrimmerConfig):
        """初始化视频剪切器

        Args:
            config: 配置对象
        """
        self.config = config

    def cut(
        self,
        video_path: Path,
        kept_segments: List[Segment],
        output_path: Path,
    ) -> float:
        """剪切并合并视频

        Args:
            video_path: 源视频路径
            kept_segments: 要保留的片段列表
            output_path: 输出视频路径

        Returns:
            输出视频时长（秒）
        """
        video_path = Path(video_path)
        output_path = Path(output_path)

        if not kept_segments:
            raise ValueError("没有要保留的片段")

        # 创建临时目录存放片段
        temp_dir = Path(tempfile.gettempdir()) / f"video_trimmer_{os.getpid()}"
        temp_dir.mkdir(parents=True, exist_ok=True)

        try:
            segment_files: List[Path] = []

            # 逐个剪切保留的片段
            for i, segment in enumerate(kept_segments):
                segment_file = temp_dir / f"segment_{i:04d}.mp4"

                logger.debug(
                    f"剪切片段 {i+1}/{len(kept_segments)}: "
                    f"{segment.start:.2f}s - {segment.end:.2f}s"
                )

                cut_segment(
                    video_path,
                    segment_file,
                    segment.start,
                    segment.end,
                    config={
                        "video_codec": self.config.video_codec,
                        "audio_codec": self.config.audio_codec,
                    },
                )

                segment_files.append(segment_file)

            # 合并所有片段
            logger.info(f"合并 {len(segment_files)} 个片段...")

            concat_segments(
                segment_files,
                output_path,
                config={
                    "video_codec": self.config.video_codec,
                    "audio_codec": self.config.audio_codec,
                    "crf": self.config.crf,
                },
            )

            # 获取输出视频时长
            output_duration = get_video_duration(output_path)

            logger.info(f"剪切完成: {output_path}")

            return output_duration

        finally:
            # 清理临时文件（Windows 需要延迟）
            time.sleep(0.1)
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception as e:
                logger.warning(f"清理临时文件失败: {e}")
