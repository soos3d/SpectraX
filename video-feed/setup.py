"""Setup script for video-feed package."""

from setuptools import setup, find_packages

setup(
    name="videofeed",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "typer",
        "keyring",
        "pyyaml",
    ],
    entry_points={
        "console_scripts": [
            "videofeed=videofeed.cli:app",
        ],
    },
    python_requires=">=3.7",
    description="Simple RTSP/HLS streaming service based on MediaMTX",
    author="Perimeter AI",
)
