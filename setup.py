"""安装配置"""

from setuptools import setup, find_packages

setup(
    name="video-silence-trimmer",
    version="0.1.0",
    description="自动检测并切除视频中的静音片段",
    long_description=open("DESIGN.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="",
    author_email="",
    url="",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "librosa>=0.10.0",
        "numpy>=1.24.0",
        "soundfile>=0.12.0",
        "click>=8.0.0",
        "loguru>=0.7.0",
    ],
    entry_points={
        "console_scripts": [
            "video-trimmer=video_silence_trimmer.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
