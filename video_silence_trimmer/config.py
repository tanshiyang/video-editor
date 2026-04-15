"""配置模型定义"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class TrimmerConfig:
    """静音切除配置"""

    # 静音检测参数
    silence_threshold_db: float = -40.0
    """静音判定阈值(dB)，能量低于此值判定为静音"""

    min_silence_duration: float = 0.5
    """最小静音持续时间(秒)，短于此值不切除"""

    keep_before_silence: float = 0.1
    """静音前保留的缓冲时间(秒)，避免截断感"""

    keep_after_silence: float = 0.1
    """静音后保留的缓冲时间(秒)"""

    # 音频分析参数
    sample_rate: int = 16000
    """音频采样率，16000Hz 足够用于静音检测"""

    # FFmpeg 参数
    ffmpeg_threads: int = 4
    """FFmpeg 编码线程数，Windows 建议 4"""

    # 临时文件
    temp_dir: Optional[Path] = None
    """临时文件目录，None 则使用系统临时目录"""

    # 输出参数
    output_format: str = "mp4"
    """输出视频格式"""

    video_codec: str = "libx264"
    """视频编码器"""

    audio_codec: str = "aac"
    """音频编码器"""

    crf: int = 23
    """视频质量 (0-51, 越低质量越好)"""

    def __post_init__(self):
        """验证配置参数"""
        if not -90 <= self.silence_threshold_db <= 0:
            raise ValueError("silence_threshold_db 必须在 -90 到 0 之间")
        if self.min_silence_duration < 0:
            raise ValueError("min_silence_duration 必须 >= 0")
        if self.keep_before_silence < 0 or self.keep_after_silence < 0:
            raise ValueError("keep_before/keep_after 必须 >= 0")
        if self.sample_rate not in (8000, 16000, 22050, 44100):
            raise ValueError(f"不支持的采样率: {self.sample_rate}")
