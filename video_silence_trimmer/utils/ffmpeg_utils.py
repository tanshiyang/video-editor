"""FFmpeg 封装工具"""

import os
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, List, Tuple

from loguru import logger


class FFmpegNotFoundError(Exception):
    """FFmpeg 未找到异常"""
    pass


class FFmpegError(Exception):
    """FFmpeg 执行异常"""
    pass


def check_ffmpeg() -> str:
    """检测 FFmpeg 是否可用

    Returns:
        FFmpeg 路径

    Raises:
        FFmpegNotFoundError: FFmpeg 未安装或未配置 PATH
    """
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path is None:
        raise FFmpegNotFoundError(
            "FFmpeg 未安装或未配置 PATH。\n"
            "Windows 安装方式：\n"
            "  方式1: winget install ffmpeg\n"
            "  方式2: 下载 https://ffmpeg.org/download.html 并配置 PATH\n"
            "Linux/macOS: sudo apt install ffmpeg / brew install ffmpeg"
        )
    logger.debug(f"FFmpeg 路径: {ffmpeg_path}")
    return ffmpeg_path


def get_ffprobe_path() -> str:
    """获取 ffprobe 路径"""
    path = shutil.which("ffprobe")
    if path is None:
        raise FFmpegNotFoundError("FFprobe 未安装")
    return path


def run_ffmpeg(
    cmd: List[str],
    capture_output: bool = True,
    check: bool = True,
) -> subprocess.CompletedProcess:
    """执行 FFmpeg 命令

    Args:
        cmd: FFmpeg 命令列表
        capture_output: 是否捕获输出
        check: 是否检查返回码

    Returns:
        subprocess.CompletedProcess

    Raises:
        FFmpegError: 当 check=True 且命令失败时
    """
    check_ffmpeg()

    # Windows 下处理中文路径
    if platform.system() == "Windows":
        # 使用 shell=True 避免 Windows 对中文路径的处理问题
        # 但仍需确保路径字符串编码正确
        try:
            result = subprocess.run(
                cmd,
                check=check,
                capture_output=capture_output,
                text=True,
                encoding='utf-8',
                errors='replace',
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0,
            )
        except UnicodeDecodeError:
            # 降级处理
            result = subprocess.run(
                cmd,
                check=check,
                capture_output=capture_output,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0,
            )
    else:
        result = subprocess.run(
            cmd,
            check=check,
            capture_output=capture_output,
            text=True,
        )

    # 如果命令失败，提供详细错误信息
    if result.returncode != 0:
        error_msg = f"FFmpeg 命令执行失败 (返回码: {result.returncode})\n"
        error_msg += f"命令: {' '.join(cmd)}\n"
        if result.stderr:
            error_msg += f"错误输出:\n{result.stderr}"
        if result.stdout:
            error_msg += f"标准输出:\n{result.stdout}"
        raise FFmpegError(error_msg)

    return result


def get_video_duration(video_path: Path) -> float:
    """获取视频时长（秒）

    Args:
        video_path: 视频文件路径

    Returns:
        视频时长（秒）
    """
    ffprobe = get_ffprobe_path()
    cmd = [
        ffprobe,
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video_path),
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding='utf-8',
    )

    try:
        return float(result.stdout.strip())
    except ValueError:
        raise FFmpegError(f"无法获取视频时长: {result.stderr}")


def get_video_info(video_path: Path) -> dict:
    """获取视频信息

    Args:
        video_path: 视频文件路径

    Returns:
        包含 duration, width, height, codec 等信息的字典
    """
    ffprobe = get_ffprobe_path()
    cmd = [
        ffprobe,
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(video_path),
    ]

    import json
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding='utf-8',
    )

    try:
        info = json.loads(result.stdout)
        format_info = info.get("format", {})
        streams = info.get("streams", [])

        video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

        return {
            "duration": float(format_info.get("duration", 0)),
            "size": int(format_info.get("size", 0)),
            "format": format_info.get("format_long_name", ""),
            "video_codec": video_stream.get("codec_name", "") if video_stream else "",
            "audio_codec": audio_stream.get("codec_name", "") if audio_stream else "",
            "width": video_stream.get("width", 0) if video_stream else 0,
            "height": video_stream.get("height", 0) if video_stream else 0,
            "has_audio": audio_stream is not None,
        }
    except json.JSONDecodeError:
        raise FFmpegError(f"无法解析 ffprobe 输出: {result.stderr}")


def extract_audio(
    video_path: Path,
    audio_path: Path,
    sample_rate: int = 16000,
    channels: int = 1,
) -> None:
    """从视频中提取音频

    Args:
        video_path: 视频文件路径
        audio_path: 输出音频文件路径
        sample_rate: 采样率
        channels: 声道数
    """
    logger.info(f"提取音频: {video_path} -> {audio_path}")

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", str(sample_rate),
        "-ac", str(channels),
        str(audio_path),
    ]

    result = run_ffmpeg(cmd)
    if result.returncode != 0:
        raise FFmpegError(f"音频提取失败: {result.stderr}")


def cut_segment(
    video_path: Path,
    output_path: Path,
    start: float,
    end: float,
    config: Optional[dict] = None,
) -> None:
    """剪切视频片段

    Args:
        video_path: 源视频路径
        output_path: 输出视频路径
        start: 起始时间（秒）
        end: 结束时间（秒）
        config: 配置参数
    """
    duration = end - start
    logger.debug(f"剪切片段: {start:.2f}s - {end:.2f}s (时长: {duration:.2f}s)")

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start),
        "-i", str(video_path),
        "-t", str(duration),
        "-c:v", "copy" if not config else config.get("video_codec", "copy"),
        "-c:a", "copy" if not config else config.get("audio_codec", "aac"),
        str(output_path),
    ]

    result = run_ffmpeg(cmd)
    if result.returncode != 0:
        raise FFmpegError(f"片段剪切失败: {result.stderr}")


def concat_segments(
    segment_files: List[Path],
    output_path: Path,
    config: Optional[dict] = None,
) -> None:
    """合并多个视频片段

    使用 FFmpeg concat demuxer 模式

    Args:
        segment_files: 片段文件路径列表
        output_path: 输出文件路径
        config: 配置参数
    """
    if not segment_files:
        raise ValueError("没有片段需要合并")

    logger.info(f"合并 {len(segment_files)} 个片段 -> {output_path}")

    # 创建临时文件列表
    with tempfile.NamedTemporaryFile(
        mode='w',
        suffix='.txt',
        delete=False,
        encoding='utf-8',
    ) as f:
        list_path = Path(f.name)
        for seg_file in segment_files:
            # Windows 下 FFmpeg concat 需要正斜杠路径
            seg_path_str = str(seg_file).replace("\\", "/")
            f.write(f"file '{seg_path_str}'\n")

    try:
        # concat demuxer 模式
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_path),
        ]

        # 添加编码参数
        if config:
            cmd.extend(["-c:v", config.get("video_codec", "libx264")])
            cmd.extend(["-c:a", config.get("audio_codec", "aac")])
            cmd.extend(["-crf", str(config.get("crf", 23))])
        else:
            cmd.extend(["-c:v", "libx264", "-c:a", "aac"])

        cmd.append(str(output_path))

        result = run_ffmpeg(cmd)
        if result.returncode != 0:
            raise FFmpegError(f"片段合并失败: {result.stderr}")
    finally:
        # 清理临时列表文件
        list_path.unlink(missing_ok=True)
