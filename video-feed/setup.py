"""Setup script for video-feed package."""

from setuptools import setup, find_packages

setup(
    name="videofeed",
    version="0.2.0",
    packages=find_packages(),
    install_requires=[
        "typer",
        "keyring", 
        "pyyaml",
        "fastapi",
        "uvicorn",
        "opencv-python-headless",
        "torch",
        "ultralytics",
        "Pillow",
        "Jinja2",
    ],
    entry_points={
        "console_scripts": [
            "videofeed=videofeed.surveillance:app",
            "surveillance=videofeed.surveillance:app",
        ],
    },
    python_requires=">=3.8",
    description="Unified surveillance system with RTSP/HLS streaming and YOLO object detection",
    author="Perimeter AI",
    long_description="A comprehensive surveillance system featuring MediaMTX-based streaming, YOLO object detection, event-based recording, and a web dashboard.",
)
