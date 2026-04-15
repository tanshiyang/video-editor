# Video Silence Trimmer

自动检测并切除视频中的静音片段，保留有声音的部分。

## 功能特性

- **音频分析**：提取视频音轨，检测静音与非静音区间
- **智能剪切**：按静音区间自动切除视频片段
- **灵活配置**：支持自定义静音阈值、最小静音时长等参数
- **跨平台**：支持 Windows、Linux、macOS
- **命令行界面**：易于集成到自动化流程

## 安装

### 1. 安装 FFmpeg

**Windows:**
```bash
winget install ffmpeg
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

验证安装：
```bash
ffmpeg -version
```

### 2. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

或使用 conda：
```bash
conda install librosa numpy soundfile click loguru
```

### 3. 安装本工具（可选）

```bash
pip install -e .
```

## 使用方法

### 命令行

```bash
video-trimmer trim <input_video> [OPTIONS]
```

**参数说明：**

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `<input_video>` | 输入视频路径 | - |
| `-o, --output` | 输出视频路径 | 必填 |
| `-t, --threshold` | 静音阈值(dB)，越低越严格 | -40 |
| `-d, --min-duration` | 最小静音时长(秒) | 0.5 |
| `--keep-before` | 静音前保留时间(秒) | 0.1 |
| `--keep-after` | 静音后保留时间(秒) | 0.1 |
| `-v, --verbose` | 输出详细日志 | False |
| `--dry-run` | 仅分析，不执行剪切 | False |

**示例：**

```bash
# 基本用法
video-trimmer trim input.mp4 -o output.mp4

# 自定义阈值（更严格的静音检测）
video-trimmer trim input.mp4 -o output.mp4 -t -50 -d 1.0

# 仅分析模式（不执行剪切）
video-trimmer trim input.mp4 -o output.mp4 --dry-run -v

# 完整参数示例
video-trimmer trim input.mp4 -o output.mp4 -t -45 -d 0.3 --keep-before 0.2 --keep-after 0.2
```

### Python API

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

**自定义配置：**

```python
from video_silence_trimmer import TrimmerConfig, VideoTrimmer

config = TrimmerConfig(
    silence_threshold_db=-50,    # 更严格的阈值
    min_silence_duration=1.0,    # 只切除1秒以上的静音
    keep_before_silence=0.2,     # 静音前保留0.2秒
    keep_after_silence=0.2,      # 静音后保留0.2秒
)

trimmer = VideoTrimmer(config)
result = trimmer.trim("input.mp4", "output.mp4")
```

### 仅分析不剪切

```bash
video-trimmer trim input.mp4 -o output.mp4 --dry-run -v
```

输出示例：
```
分析视频: input.mp4
--------------------------------------------------
原始时长: 120.50s
可切除时长: 45.30s
静音片段数: 5
--------------------------------------------------
静音区间:
  1. 10.00s - 25.00s (时长: 15.00s)
  2. 50.00s - 55.00s (时长: 5.00s)
  ...
--------------------------------------------------
保留区间:
  1. 0.00s - 9.90s (时长: 9.90s)
  ...
```

### 查看视频信息

```bash
video-trimmer info input.mp4
```

输出示例：
```
文件: input.mp4
--------------------------------------------------
格式: QuickTime / MOV
时长: 120.50s
大小: 45.23 MB
视频编码: h264
分辨率: 1920x1080
音频编码: aac
包含音频: 是
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

**Q: 提示 "视频不包含音频流"？**
A: 本工具需要视频包含音轨。请检查视频文件是否损坏。

**Q: 静音片段没有被切除？**
A: 尝试降低阈值（如 `-t -50`）或减少最小静音时长（如 `-d 0.3`）。

**Q: 中文路径报错？**
A: 确保使用 pathlib 或在传给 FFmpeg 前将路径转为正斜杠格式。

## 开发

```bash
# 安装开发依赖
pip install pytest

# 运行测试
pytest tests/

# 以开发模式安装
pip install -e .
```

## License

MIT
