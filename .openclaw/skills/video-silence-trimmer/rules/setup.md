---
name: setup
description: Python script initialization and environment setup rules.
metadata:
  tags: setup, python, import, sys.path
---

# Environment Initialization

## Bootstrap Template

在业务脚本开头使用以下模板来初始化环境：

```python
import os
import sys
from pathlib import Path

# 获取项目根目录（向上查找 SKILL.md 所在目录）
current_dir = Path(__file__).parent.resolve()
skill_root = current_dir
for _ in range(5):  # 最多向上5层
    if (skill_root / "SKILL.md").exists():
        break
    skill_root = skill_root.parent
else:
    raise ImportError("Could not find video-silence-trimmer skill root")

# 将项目路径添加到 sys.path
src_path = skill_root.parent  # 项目根目录
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from video_silence_trimmer import VideoTrimmer, TrimmerConfig
```

## 依赖要求

- **Python 3.8+**
- **FFmpeg** 和 **FFprobe** 必须在 PATH 中
- **Python 包**: librosa, numpy, click, loguru

## 安装检查

```bash
# 验证 FFmpeg
ffmpeg -version

# 验证 Python 依赖
pip install -r requirements.txt
```
