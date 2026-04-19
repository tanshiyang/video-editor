"""
Video Silence Trimmer - 快速示例
"""
import sys
from pathlib import Path

# 初始化环境
current_dir = Path(__file__).parent.resolve()
skill_root = current_dir
for _ in range(5):
    if (skill_root / "SKILL.md").exists():
        break
    skill_root = skill_root.parent
else:
    raise ImportError("Could not find video-silence-trimmer skill root")

src_path = skill_root.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from video_silence_trimmer import VideoTrimmer, TrimmerConfig

if __name__ == "__main__":
    # 示例：剪切视频中的静音片段
    input_video = Path("input.mp4")
    output_video = Path("output.mp4")

    # 使用默认配置
    config = TrimmerConfig()
    trimmer = VideoTrimmer(config)

    # 执行剪切
    result = trimmer.trim(input_video, output_video)

    print(f"原始时长: {result.original_duration:.2f}s")
    print(f"输出时长: {result.output_duration:.2f}s")
    print(f"压缩比: {result.compression_ratio:.1%}")
