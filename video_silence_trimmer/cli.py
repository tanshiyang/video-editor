"""命令行入口"""

import sys
from pathlib import Path

import click
from loguru import logger

from .config import TrimmerConfig
from .core.trimmer import VideoTrimmer
from .utils.ffmpeg_utils import FFmpegNotFoundError


def setup_logging(verbose: bool = False):
    """配置日志"""
    logger.remove()

    if verbose:
        logger.add(
            sys.stderr,
            level="DEBUG",
            format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        )
    else:
        logger.add(
            sys.stderr,
            level="INFO",
            format="<level>{message}</level>",
        )


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """视频静音切除工具

    自动检测并切除视频中的静音片段，保留有声音的部分。
    """
    pass


@cli.command()
@click.argument("input_video", type=click.Path(exists=True))
@click.option(
    "-o", "--output",
    type=click.Path(),
    required=True,
    help="输出视频路径",
)
@click.option(
    "-t", "--threshold",
    type=float,
    default=-40.0,
    help="静音阈值(dB)，默认 -40，越低越严格",
)
@click.option(
    "-d", "--min-duration",
    type=float,
    default=0.5,
    help="最小静音时长(秒)，默认 0.5",
)
@click.option(
    "--keep-before",
    type=float,
    default=0.1,
    help="静音前保留时间(秒)，默认 0.1",
)
@click.option(
    "--keep-after",
    type=float,
    default=0.1,
    help="静音后保留时间(秒)，默认 0.1",
)
@click.option(
    "-v", "--verbose",
    is_flag=True,
    help="输出详细日志",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="仅分析不执行剪切",
)
def trim(
    input_video: str,
    output: str,
    threshold: float,
    min_duration: float,
    keep_before: float,
    keep_after: float,
    verbose: bool,
    dry_run: bool,
):
    """分析并剪切视频中的静音片段

    示例:
        video-trimmer trim input.mp4 -o output.mp4
        video-trimmer trim input.mp4 -o output.mp4 -t -50 -d 1.0
        video-trimmer trim input.mp4 -o output.mp4 --dry-run -v
    """
    setup_logging(verbose)

    try:
        # 验证 FFmpeg
        from .utils.ffmpeg_utils import check_ffmpeg
        check_ffmpeg()
    except FFmpegNotFoundError as e:
        click.echo(f"错误: {e}", err=True)
        sys.exit(1)

    # 创建配置
    config = TrimmerConfig(
        silence_threshold_db=threshold,
        min_silence_duration=min_duration,
        keep_before_silence=keep_before,
        keep_after_silence=keep_after,
    )

    # 创建处理器
    trimmer = VideoTrimmer(config)

    input_path = Path(input_video)
    output_path = Path(output)

    if dry_run:
        # 仅分析模式
        click.echo(f"分析视频: {input_path}")
        click.echo("-" * 50)

        result = trimmer.analyze(input_path)

        if not result["has_audio"]:
            click.echo("错误: 视频不包含音频流")
            sys.exit(1)

        click.echo(f"原始时长: {result['original_duration']:.2f}s")
        click.echo(f"可切除时长: {result['removable_duration']:.2f}s")
        click.echo(f"静音片段数: {len(result['silence_segments'])}")
        click.echo("-" * 50)

        if result['silence_segments']:
            click.echo("静音区间:")
            for i, seg in enumerate(result['silence_segments']):
                click.echo(f"  {i+1}. {seg.start:.2f}s - {seg.end:.2f}s (时长: {seg.duration:.2f}s)")

        click.echo("-" * 50)
        click.echo("保留区间:")
        for i, seg in enumerate(result['kept_segments']):
            click.echo(f"  {i+1}. {seg.start:.2f}s - {seg.end:.2f}s (时长: {seg.duration:.2f}s)")

    else:
        # 执行剪切
        click.echo(f"处理视频: {input_path} -> {output_path}")

        try:
            result = trimmer.trim(input_path, output_path)

            click.echo("-" * 50)
            click.echo(f"原始时长: {result.original_duration:.2f}s")
            click.echo(f"输出时长: {result.output_duration:.2f}s")
            click.echo(f"切除时长: {result.removed_duration:.2f}s")
            click.echo(f"压缩比: {result.compression_ratio:.1%}")
            click.echo(f"处理耗时: {result.processing_time:.2f}s")
            click.echo("-" * 50)
            click.echo(f"输出文件: {output_path}")

        except Exception as e:
            click.echo(f"错误: {e}", err=True)
            sys.exit(1)


@cli.command()
@click.argument("video_path", type=click.Path(exists=True))
def info(video_path: str):
    """显示视频信息

    示例:
        video-trimmer info input.mp4
    """
    from .utils.ffmpeg_utils import get_video_info

    try:
        info = get_video_info(Path(video_path))

        click.echo(f"文件: {video_path}")
        click.echo("-" * 50)
        click.echo(f"格式: {info['format']}")
        click.echo(f"时长: {info['duration']:.2f}s")
        click.echo(f"大小: {info['size'] / 1024 / 1024:.2f} MB")
        click.echo(f"视频编码: {info['video_codec']}")
        click.echo(f"分辨率: {info['width']}x{info['height']}")
        click.echo(f"音频编码: {info['audio_codec']}")
        click.echo(f"包含音频: {'是' if info['has_audio'] else '否'}")

    except Exception as e:
        click.echo(f"错误: {e}", err=True)
        sys.exit(1)


def main():
    """入口函数"""
    cli()


if __name__ == "__main__":
    main()
