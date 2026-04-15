"""音频处理工具"""

from pathlib import Path
from typing import List, Tuple

import librosa
import numpy as np
from loguru import logger


def db_to_amplitude(db: float) -> float:
    """分贝值转振幅

    Args:
        db: 分贝值

    Returns:
        对应振幅值
    """
    return 10 ** (db / 20)


def amplitude_to_db(amplitude: float) -> float:
    """振幅转分贝值

    Args:
        amplitude: 振幅值

    Returns:
        分贝值
    """
    if amplitude <= 0:
        return -np.inf
    return 20 * np.log10(amplitude)


def compute_rms(
    audio_path: Path,
    sample_rate: int = 16000,
    hop_length: int = 512,
) -> Tuple[np.ndarray, np.ndarray]:
    """计算音频的 RMS 能量

    Args:
        audio_path: 音频文件路径
        sample_rate: 采样率
        hop_length: 帧移

    Returns:
        (rms能量数组, 时间轴数组)
    """
    logger.debug(f"加载音频: {audio_path}")

    y, sr = librosa.load(
        audio_path,
        sr=sample_rate,
        mono=True,
    )

    # 计算 RMS 能量
    rms = librosa.feature.rms(
        y=y,
        hop_length=hop_length,
        frame_length=2048,
    )[0]

    # 计算时间轴（与 RMS 帧对齐）
    times = librosa.times_like(rms, sr=sr, hop_length=hop_length)

    logger.debug(f"音频时长: {times[-1]:.2f}s, RMS帧数: {len(rms)}")

    return rms, times


def detect_silence_frames(
    rms: np.ndarray,
    threshold_db: float = -40.0,
) -> np.ndarray:
    """检测静音帧

    Args:
        rms: RMS 能量数组
        threshold_db: 静音阈值（分贝）

    Returns:
        布尔数组，True 表示静音帧
    """
    threshold_amplitude = db_to_amplitude(threshold_db)
    is_silent = rms < threshold_amplitude

    silent_count = np.sum(is_silent)
    total_count = len(is_silent)
    logger.debug(
        f"静音检测: 阈值={threshold_db}dB, "
        f"静音帧={silent_count}/{total_count} ({100*silent_count/total_count:.1f}%)"
    )

    return is_silent


def merge_silence_intervals(
    is_silent: np.ndarray,
    times: np.ndarray,
    min_duration: float,
    hop_length: int = 512,
    sample_rate: int = 16000,
) -> List[Tuple[float, float]]:
    """合并静音区间

    将连续静音帧合并为区间，过滤短于最小持续时间的静音区间

    Args:
        is_silent: 静音帧标记数组
        times: 时间轴数组
        min_duration: 最小静音持续时间（秒）
        hop_length: 帧移
        sample_rate: 采样率

    Returns:
        静音区间列表 [(start, end), ...]
    """
    # 计算每帧对应的 hop 长度（秒）
    frame_duration = hop_length / sample_rate

    # 找出静音区间的起始和结束索引
    silent_changes = np.diff(is_silent.astype(int))
    silent_starts = np.where(silent_changes == 1)[0]  # 变为静音的帧
    silent_ends = np.where(silent_changes == -1)[0]   # 结束静音的帧

    # 处理首尾情况
    if len(silent_starts) == 0 and len(silent_ends) == 0:
        if is_silent[0]:
            # 全程静音
            return [(times[0], times[-1] + frame_duration)]
        return []

    # 修正：如果音频开头是静音
    if is_silent[0]:
        silent_starts = np.concatenate([[0], silent_starts])

    # 修正：如果音频结尾是静音
    if is_silent[-1]:
        silent_ends = np.concatenate([silent_ends, [len(times) - 1]])

    if len(silent_starts) != len(silent_ends):
        # 边界情况，调整使数量一致
        if len(silent_starts) > len(silent_ends):
            silent_ends = np.concatenate([silent_ends, [len(times) - 1]])
        else:
            silent_starts = np.concatenate([[0], silent_starts])

    # 构建区间列表并过滤
    silence_intervals = []
    for start_idx, end_idx in zip(silent_starts, silent_ends):
        start_time = times[start_idx]
        end_time = times[end_idx] + frame_duration
        duration = end_time - start_time

        if duration >= min_duration:
            silence_intervals.append((start_time, end_time))
            logger.debug(f"静音区间: {start_time:.2f}s - {end_time:.2f}s (持续 {duration:.2f}s)")

    return silence_intervals


def invert_silence_intervals(
    silence_intervals: List[Tuple[float, float]],
    total_duration: float,
    keep_before: float = 0.0,
    keep_after: float = 0.0,
) -> List[Tuple[float, float]]:
    """根据静音区间计算保留（非静音）区间

    Args:
        silence_intervals: 静音区间列表
        total_duration: 音频总时长
        keep_before: 静音前保留时间
        keep_after: 静音后保留时间

    Returns:
        保留区间列表
    """
    if not silence_intervals:
        return [(0.0, total_duration)]

    kept_intervals = []
    current_time = 0.0

    for silence_start, silence_end in silence_intervals:
        # 在静音开始前保留一段时间（缓冲）
        buffer_start = max(current_time, silence_start - keep_before)

        # 如果当前时间到静音开始前有间隔，保留这段
        if buffer_start > current_time:
            kept_intervals.append((current_time, buffer_start))

        # 静音区间结束后保留一段时间
        current_time = silence_end + keep_after

    # 处理最后的非静音部分
    if current_time < total_duration:
        kept_intervals.append((current_time, total_duration))

    return kept_intervals
