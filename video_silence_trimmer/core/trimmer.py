"""主入口模块 - 整合分析器和剪切器"""

import time
from pathlib import Path
from typing import Optional, List, Dict

from loguru import logger

from ..config import TrimmerConfig
from ..utils.ffmpeg_utils import get_video_duration, get_video_info
from .analyzer import AudioAnalyzer, NoAudioStreamError
from .cutter import VideoCutter
from .segment import Segment, TrimResult, MultiTrimResult


class VideoLengthMismatchError(Exception):
    """视频时长不匹配异常"""
    pass


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

    def trim_multi(
        self,
        main_video: Path,
        secondary_videos: List[Path],
        outputs: Dict[str, Path],
    ) -> MultiTrimResult:
        """多视频联动模式：主视频分析，副视频同步剪切

        Args:
            main_video: 主视频路径（用于音频分析）
            secondary_videos: 副视频路径列表
            outputs: 输出路径字典 {原视频路径: 输出路径}

        Returns:
            MultiTrimResult 结果对象
        """
        start_time = time.time()

        main_video = Path(main_video)
        logger.info(f"多视频联动处理:")
        logger.info(f"  主视频: {main_video}")
        for sv in secondary_videos:
            logger.info(f"  副视频: {sv}")

        # 获取主视频时长
        main_duration = get_video_duration(main_video)
        logger.info(f"主视频时长: {main_duration:.2f}s")

        # 验证所有副视频时长与主视频一致
        # 允许最大 2 秒误差（OBS 等同时录制的视频常有微小时长差异）
        for sv in secondary_videos:
            sv_duration = get_video_duration(sv)
            duration_diff = abs(sv_duration - main_duration)
            if duration_diff > 2.0:
                raise VideoLengthMismatchError(
                    f"副视频 {sv.name} 时长 ({sv_duration:.2f}s) "
                    f"与主视频时长 ({main_duration:.2f}s) 相差 {duration_diff:.2f}s，"
                    f"超过允许的 2 秒误差范围。"
                )
            elif duration_diff > 0.1:
                logger.warning(
                    f"副视频 {sv.name} 时长 ({sv_duration:.2f}s) "
                    f"与主视频 ({main_duration:.2f}s) 相差 {duration_diff:.2f}s，"
                    f"将在共同范围内处理。"
                )

        # 分析主视频音频，获取保留片段
        silence_segments, kept_segments = self.analyzer.analyze(main_video)

        logger.info(f"主视频分析完成，静音片段数: {len(silence_segments)}")
        logger.info(f"保留片段数: {len(kept_segments)}")

        # 处理主视频
        main_output = outputs.get(str(main_video))
        if main_output:
            main_output_duration = self.cutter.cut(main_video, kept_segments, main_output)
            main_result = TrimResult(
                original_duration=main_duration,
                output_duration=main_output_duration,
                removed_segments=silence_segments,
                kept_segments=kept_segments,
                processing_time=0.0,
            )
        else:
            main_result = TrimResult(
                original_duration=main_duration,
                output_duration=main_duration,
                removed_segments=[],
                kept_segments=[Segment(0, main_duration, False)],
                processing_time=0.0,
            )

        # 处理所有副视频
        secondary_results: Dict[str, TrimResult] = {}

        for sv in secondary_videos:
            sv = Path(sv)
            sv_duration = get_video_duration(sv)
            sv_output = outputs.get(str(sv))

            logger.info(f"处理副视频: {sv.name}")

            # 剪辑保留区间到副视频的实际时长范围
            clipped_segments = self._clip_segments_to_duration(kept_segments, sv_duration)

            if sv_output:
                # 副视频使用与主视频相同的保留片段进行剪切
                sv_output_duration = self.cutter.cut(sv, clipped_segments, sv_output)

                # 副视频的静音片段与主视频相同（时间轴对齐）
                sv_result = TrimResult(
                    original_duration=sv_duration,
                    output_duration=sv_output_duration,
                    removed_segments=silence_segments,  # 静音片段相同
                    kept_segments=clipped_segments,  # 使用剪辑后的片段
                    processing_time=0.0,
                )
            else:
                sv_result = TrimResult(
                    original_duration=sv_duration,
                    output_duration=sv_duration,
                    removed_segments=[],
                    kept_segments=clipped_segments,
                    processing_time=0.0,
                )

            secondary_results[sv.name] = sv_result

        total_time = time.time() - start_time

        result = MultiTrimResult(
            main_result=main_result,
            secondary_results=secondary_results,
            total_processing_time=total_time,
        )

        logger.info(f"多视频处理完成: {result}")

        return result

    def _clip_segments_to_duration(
        self,
        segments: List[Segment],
        max_duration: float,
    ) -> List[Segment]:
        """将片段剪辑到指定最大时长范围内

        Args:
            segments: 原始片段列表
            max_duration: 最大时长

        Returns:
            剪辑后的片段列表
        """
        if not segments:
            return []

        clipped = []
        for seg in segments:
            if seg.end <= max_duration:
                # 片段完全在范围内
                clipped.append(seg)
            elif seg.start < max_duration:
                # 片段部分超出范围，剪辑 end
                clipped.append(Segment(
                    start=seg.start,
                    end=max_duration,
                    is_silent=seg.is_silent,
                ))
            # else: 片段完全超出范围，跳过

        return clipped

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
