"""命令行入口"""

import sys
from pathlib import Path

import click
from loguru import logger

from .config import TrimmerConfig
from .core.trimmer import VideoTrimmer, VideoLengthMismatchError
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
@click.version_option(version="0.2.0")
def cli():
    """视频静音切除工具

    自动检测并切除视频中的静音片段，保留有声音的部分。
    支持多视频联动模式：主视频分析，副视频同步剪切。

    文档: https://github.com/tanshiyang/video-editor
    """
    pass


@cli.command()
@click.argument("main_video", type=click.Path(exists=True))
@click.option(
    "-o", "--output",
    type=click.Path(),
    required=True,
    help="输出视频路径（主视频的输出路径）",
)
@click.option(
    "-s", "--secondary",
    type=click.Path(exists=True),
    multiple=True,
    help="副视频文件路径（可多次使用）。"
         "副视频将使用与主视频相同的静音区间进行同步剪切。",
)
@click.option(
    "-t", "--threshold",
    type=float,
    default=-40.0,
    help="静音阈值(dB)，默认 -40。"
         "值越低检测越严格（例如 -50 比 -40 更严格）。",
)
@click.option(
    "-d", "--min-duration",
    type=float,
    default=0.5,
    help="最小静音时长(秒)，默认 0.5。"
         "短于此值的静音片段将被保留。",
)
@click.option(
    "--keep-before",
    type=float,
    default=0.1,
    help="静音前保留时间(秒)，默认 0.1。"
         "在静音开始前保留一段时间，避免截断过于生硬。",
)
@click.option(
    "--keep-after",
    type=float,
    default=0.1,
    help="静音后保留时间(秒)，默认 0.1。"
         "在静音结束后保留一段时间，避免截断过于生硬。",
)
@click.option(
    "--output-suffix",
    type=str,
    default="_trimmed",
    help="副视频输出文件名的后缀，默认 '_trimmed'。"
         "例如：'video.mp4' 会输出为 'video_trimmed.mp4'",
)
@click.option(
    "-v", "--verbose",
    is_flag=True,
    help="启用详细日志输出，显示处理进度信息。",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="仅分析不执行剪切。显示将被切除的区间，但不实际剪切视频。",
)
def trim(
    main_video: str,
    output: str,
    secondary: tuple,
    threshold: float,
    min_duration: float,
    keep_before: float,
    keep_after: float,
    output_suffix: str,
    verbose: bool,
    dry_run: bool,
):
    """分析并剪切视频中的静音片段

    基于音频分析检测静音区间，只保留有声音的片段。

    \b
    单文件模式:
        video-trimmer trim input.mp4 -o output.mp4
        video-trimmer trim input.mp4 -o output.mp4 -t -50 -d 1.0
        video-trimmer trim input.mp4 -o output.mp4 --dry-run -v

    \b
    多视频联动模式（同步剪切）:
        video-trimmer trim main.mp4 -s secondary1.mp4 -s secondary2.mp4 -o main_out.mp4

        所有视频时长必须相同。主视频用于静音检测，
        副视频按相同的静音区间同步剪切。

    \b
    使用示例:
        # 基本用法
        video-trimmer trim recording.mp4 -o output.mp4

        # 严格静音检测（只去除非常安静的部分）
        video-trimmer trim recording.mp4 -o output.mp4 -t -50 -d 1.0

        # 预览将被去除的内容
        video-trimmer trim recording.mp4 -o output.mp4 --dry-run -v

        # 多视频联动并自定义后缀
        video-trimmer trim main.mp4 -s sub1.mp4 -s sub2.mp4 -o main.mp4 --output-suffix "_cut"

        # 激进剪切（去除更短的静音）
        video-trimmer trim video.mp4 -o output.mp4 -t -40 -d 0.3

    \b
    参数调优指南:
        -t -40 -d 0.5  : 去除长停顿（默认）
        -t -50 -d 1.0  : 只去除很长的静音
        -t -45 -d 0.3  : 也去除较短的静音
        --keep-before 0.2 --keep-after 0.2 : 自然过渡效果
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
        output_suffix=output_suffix,
    )

    # 创建处理器
    trimmer = VideoTrimmer(config)

    input_path = Path(main_video)
    output_path = Path(output)
    secondary_paths = [Path(s) for s in secondary]

    if dry_run:
        # 仅分析模式
        click.echo(f"分析视频: {input_path}")
        if secondary_paths:
            click.echo(f"副视频数: {len(secondary_paths)}")
        click.echo("-" * 50)

        result = trimmer.analyze(input_path)

        if not result["has_audio"]:
            click.echo("错误: 主视频不包含音频流")
            sys.exit(1)

        click.echo(f"原始时长: {result['original_duration']:.2f}s")
        click.echo(f"可切除时长: {result['removable_duration']:.2f}s")
        click.echo(f"静音片段数: {len(result['silence_segments'])}")
        click.echo("-" * 50)

        if result['silence_segments']:
            click.echo("静音区间（将被切除）:")
            for i, seg in enumerate(result['silence_segments']):
                click.echo(f"  {i+1}. {seg.start:.2f}s - {seg.end:.2f}s (时长: {seg.duration:.2f}s)")

        click.echo("-" * 50)
        click.echo("保留区间:")
        for i, seg in enumerate(result['kept_segments']):
            click.echo(f"  {i+1}. {seg.start:.2f}s - {seg.end:.2f}s (时长: {seg.duration:.2f}s)")

    else:
        # 执行剪切
        if secondary_paths:
            # 多视频联动模式
            click.echo(f"多视频联动模式:")
            click.echo(f"  主视频: {input_path} -> {output_path}")

            # 构建输出路径字典
            outputs = {str(input_path): output_path}

            # 为每个副视频生成输出路径
            secondary_outputs = []
            for sv in secondary_paths:
                sv_output = sv.parent / f"{sv.stem}{output_suffix}{sv.suffix}"
                outputs[str(sv)] = sv_output
                secondary_outputs.append(sv_output)
                click.echo(f"  副视频: {sv} -> {sv_output}")

            try:
                result = trimmer.trim_multi(
                    main_video=input_path,
                    secondary_videos=secondary_paths,
                    outputs=outputs,
                )

                click.echo("-" * 50)
                click.echo(f"主视频: {result.main_result.original_duration:.2f}s -> {result.main_result.output_duration:.2f}s")
                click.echo(f"副视频处理数: {len(result.secondary_results)}")
                for name, r in result.secondary_results.items():
                    click.echo(f"  {name}: {r.original_duration:.2f}s -> {r.output_duration:.2f}s")
                click.echo(f"总处理耗时: {result.total_processing_time:.2f}s")
                click.echo("-" * 50)

            except VideoLengthMismatchError as e:
                click.echo(f"错误: {e}", err=True)
                sys.exit(1)

        else:
            # 单文件模式
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
    """显示视频文件的详细信息

    显示格式、时长、大小、编码器、分辨率和音频信息。

    \b
    示例:
        video-trimmer info input.mp4
        video-trimmer info recording.mov

    \b
    输出字段说明:
        - File: 视频文件路径
        - Format: 容器格式（如 MP4、MKV、MOV）
        - Duration: 总时长（秒）
        - Size: 文件大小（MB）
        - Video Codec: 视频流编码器（如 h264、hevc）
        - Resolution: 帧分辨率（如 1920x1080）
        - Audio Codec: 音频流编码器（如 aac、mp3）
        - Has Audio: 是否包含音频轨道
    """
    from .utils.ffmpeg_utils import get_video_info

    try:
        video_info = get_video_info(Path(video_path))

        click.echo(f"文件: {video_path}")
        click.echo("-" * 50)
        click.echo(f"格式: {video_info['format']}")
        click.echo(f"时长: {video_info['duration']:.2f}s")
        click.echo(f"大小: {video_info['size'] / 1024 / 1024:.2f} MB")
        click.echo(f"视频编码: {video_info['video_codec']}")
        click.echo(f"分辨率: {video_info['width']}x{video_info['height']}")
        click.echo(f"音频编码: {video_info['audio_codec']}")
        click.echo(f"包含音频: {'是' if video_info['has_audio'] else '否'}")

    except Exception as e:
        click.echo(f"错误: {e}", err=True)
        sys.exit(1)


def main():
    """入口函数"""
    cli()


if __name__ == "__main__":
    main()
