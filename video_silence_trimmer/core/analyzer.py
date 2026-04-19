"""音频分析模块 - 静音检测"""

import tempfile
from pathlib import Path
from typing import List, Tuple

import numpy as np
from loguru import logger

from ..config import TrimmerConfig
from ..utils.audio_utils import (
    compute_rms,
    detect_silence_frames,
    merge_silence_intervals,
    invert_silence_intervals,
)
from ..utils.ffmpeg_utils import extract_audio, get_video_duration, get_video_info
from .segment import Segment


class NoAudioStreamError(Exception):
    """视频无音频流异常"""
    pass


class AudioAnalyzer:
    """音频分析器 - 检测静音区间"""

    def __init__(self, config: TrimmerConfig):
        """初始化音频分析器

        Args:
            config: 配置对象
        """
        self.config = config

    def analyze(
        self,
        video_path: Path,
        audio_path: Path = None,
    ) -> Tuple[List[Segment], List[Segment], float]:
        """分析视频音频，检测静音区间

        Args:
            video_path: 视频文件路径
            audio_path: 音频文件路径（可选，如果不提供则临时提取）

        Returns:
            (静音片段列表, 保留片段列表, 原始时长)
        """
        video_path = Path(video_path)
        logger.info(f"开始分析视频: {video_path}")

        # 检查视频信息
        info = get_video_info(video_path)
        if not info.get("has_audio"):
            raise NoAudioStreamError(
                f"视频 {video_path.name} 不包含音频流，"
                "无法进行静音检测。请检查视频文件。"
            )

        original_duration = info["duration"]
        logger.info(f"视频时长: {original_duration:.2f}s")

        # 提取音频（如果未提供）
        temp_audio = False
        if audio_path is None:
            audio_path = Path(tempfile.gettempdir()) / f"audio_extract_{id(video_path)}.wav"
            extract_audio(
                video_path,
                audio_path,
                sample_rate=self.config.sample_rate,
            )
            temp_audio = True

        try:
            # 计算 RMS 能量
            rms, times = compute_rms(
                audio_path,
                sample_rate=self.config.sample_rate,
            )

            # 检测静音帧
            is_silent = detect_silence_frames(
                rms,
                threshold_db=self.config.silence_threshold_db,
            )

            # 合并静音区间
            silence_intervals = merge_silence_intervals(
                is_silent,
                times,
                min_duration=self.config.min_silence_duration,
                hop_length=512,
                sample_rate=self.config.sample_rate,
            )

            # 计算保留区间
            kept_intervals = invert_silence_intervals(
                silence_intervals,
                original_duration,
                keep_before=self.config.keep_before_silence,
                keep_after=self.config.keep_after_silence,
            )

            # 构建片段对象
            silence_segments = [
                Segment(start=start, end=end, is_silent=True)
                for start, end in silence_intervals
            ]

            kept_segments = [
                Segment(start=start, end=end, is_silent=False)
                for start, end in kept_intervals
            ]

            # 统计
            total_silence = sum(s.duration for s in silence_segments)
            total_kept = sum(s.duration for s in kept_segments)

            logger.info(
                f"分析完成:\n"
                f"  静音片段数: {len(silence_segments)}\n"
                f"  静音总时长: {total_silence:.2f}s\n"
                f"  保留片段数: {len(kept_segments)}\n"
                f"  保留总时长: {total_kept:.2f}s\n"
                f"  可压缩: {100*total_silence/original_duration:.1f}%"
            )

            return silence_segments, kept_segments, original_duration

        finally:
            # 清理临时音频文件
            if temp_audio and audio_path.exists():
                audio_path.unlink(missing_ok=True)

    def analyze_dry_run(
        self,
        video_path: Path,
    ) -> dict:
        """仅分析不剪切（dry-run 模式）

        Args:
            video_path: 视频文件路径

        Returns:
            包含分析结果的字典
        """
        video_path = Path(video_path)

        try:
            silence_segments, kept_segments, original_duration = self.analyze(video_path)
        except NoAudioStreamError:
            original_duration = get_video_duration(video_path)
            return {
                "has_audio": False,
                "original_duration": original_duration,
                "silence_segments": [],
                "kept_segments": [Segment(0, original_duration, False)],
                "removable_duration": 0,
            }

        removable_duration = sum(s.duration for s in silence_segments)

        return {
            "has_audio": True,
            "original_duration": original_duration,
            "silence_segments": silence_segments,
            "kept_segments": kept_segments,
            "removable_duration": removable_duration,
        }
