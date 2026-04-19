---
name: video-silence-trimmer
description: |
  自动检测并切除视频中的静音片段，保留有声音的部分。
  支持多视频联动模式：主视频分析，副视频同步剪切。
metadata:
  {
    "openclaw": {
      "emoji": "🎬",
      "requires": { "bins": ["ffmpeg", "ffprobe"] },
      "install": [
        {
          "id": "ffmpeg-windows",
          "kind": "download",
          "label": "Install FFmpeg (Windows)",
          "command": "winget install ffmpeg"
        },
        {
          "id": "ffmpeg-macos",
          "kind": "brew",
          "formula": "ffmpeg",
          "label": "Install FFmpeg (macOS)"
        },
        {
          "id": "ffmpeg-linux",
          "kind": "apt",
          "command": "sudo apt install ffmpeg",
          "label": "Install FFmpeg (Linux)"
        }
      ]
    }
  }
user-invocable: true
---

# Video Silence Trimmer Skill

自动检测并切除视频中的静音片段，保留有声音的部分。

## 功能特性

- **音频分析**：提取视频音轨，检测静音与非静音区间
- **智能剪切**：按静音区间自动切除视频片段
- **灵活配置**：支持自定义静音阈值、最小静音时长等参数
- **跨平台**：支持 Windows、Linux、macOS
- **多视频联动**：支持主文件+副文件模式，副视频同步跟随主视频剪切
- **批量处理**：一次处理多个视频，保持时间轴同步

## 使用前提

1. **安装 FFmpeg**：
   - Windows: `winget install ffmpeg`
   - macOS: `brew install ffmpeg`
   - Linux: `sudo apt install ffmpeg`

2. **安装 Python 依赖**：
   ```bash
   pip install -r requirements.txt
   ```

## 命令行使用

### 单文件模式

```bash
video-trimmer trim <input_video> -o <output_video>
```

### 多视频联动模式

```bash
video-trimmer trim <main_video> -s <secondary_video1> -s <secondary_video2> -o <output>
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-o, --output` | 输出视频路径 | 必填 |
| `-s, --secondary` | 副视频文件路径（可多次使用） | - |
| `-t, --threshold` | 静音阈值(dB)，越低越严格 | -40 |
| `-d, --min-duration` | 最小静音时长(秒) | 0.5 |
| `--keep-before` | 静音前保留时间(秒) | 0.1 |
| `--keep-after` | 静音后保留时间(秒) | 0.1 |
| `--dry-run` | 仅分析，不执行剪切 | False |
| `-v, --verbose` | 输出详细日志 | False |

### 示例

```bash
# 基本用法
video-trimmer trim input.mp4 -o output.mp4

# 自定义阈值（更严格）
video-trimmer trim input.mp4 -o output.mp4 -t -50 -d 1.0

# 预览模式（仅分析不剪切）
video-trimmer trim input.mp4 -o output.mp4 --dry-run -v

# 多视频联动
video-trimmer trim main.mp4 -s sub1.mp4 -s sub2.mp4 -o main_out.mp4
```

## Python API 使用

```python
from video_silence_trimmer import VideoTrimmer, TrimmerConfig

# 默认配置
config = TrimmerConfig()
trimmer = VideoTrimmer(config)

# 执行剪切
result = trimmer.trim("input.mp4", "output.mp4")

print(f"原始时长: {result.original_duration:.2f}s")
print(f"输出时长: {result.output_duration:.2f}s")
print(f"压缩比: {result.compression_ratio:.1%}")
```

### 自定义配置

```python
config = TrimmerConfig(
    silence_threshold_db=-50,    # 更严格的阈值
    min_silence_duration=1.0,    # 只切除1秒以上的静音
    keep_before_silence=0.2,    # 静音前保留0.2秒
    keep_after_silence=0.2,      # 静音后保留0.2秒
)
```

### 多视频联动

```python
result = trimmer.trim_multi(
    main_video="main.mp4",
    secondary_videos=["secondary1.mp4", "secondary2.mp4"],
    outputs={
        "main.mp4": "main_trimmed.mp4",
        "secondary1.mp4": "secondary1_trimmed.mp4",
        "secondary2.mp4": "secondary2_trimmed.mp4",
    }
)
```

## 参数调优指南

| 场景 | 建议参数 |
|------|----------|
| 去除长停顿 | `-t -40 -d 1.0` |
| 去除短空白 | `-t -45 -d 0.3` |
| 保留自然过渡 | `--keep-before 0.2 --keep-after 0.2` |
| 激进压缩 | `-t -50 -d 0.5` |

## 工作原理

```
输入视频 → 提取音频 → librosa 分析 RMS 能量 → 检测静音区间 → FFmpeg 剪切合并 → 输出视频
```

1. **音频提取**：使用 FFmpeg 从视频中提取音轨
2. **能量分析**：使用 librosa 计算每帧的 RMS 能量
3. **静音检测**：低于阈值的连续帧判定为静音
4. **区间合并**：相邻静音区间合并，过滤短静音
5. **视频剪切**：FFmpeg 按保留区间剪切并合并

## 常见问题

**Q: 提示 "FFmpeg 未安装"？**
A: 确保 FFmpeg 已安装并配置到 PATH。Windows 用户可使用 `winget install ffmpeg`。

**Q: 静音片段没有被切除？**
A: 尝试降低阈值（如 `-t -50`）或减少最小静音时长（如 `-d 0.3`）。

**Q: 多视频联动时副视频时长与主视频不一致？**
A: 主视频和所有副视频的时长必须完全一致（允许 2 秒误差）。

## 项目结构

```
video_silence_trimmer/
├── __init__.py          # 包入口
├── __main__.py          # CLI 入口
├── cli.py               # Click 命令行定义
├── config.py            # TrimmerConfig 配置类
├── core/
│   ├── analyzer.py      # AudioAnalyzer 音频分析
│   ├── cutter.py        # VideoCutter 视频剪切
│   ├── segment.py       # Segment/TrimResult 数据模型
│   └── trimmer.py       # VideoTrimmer 主入口
└── utils/
    ├── audio_utils.py   # librosa 音频处理
    └── ffmpeg_utils.py  # FFmpeg 封装
```
