# SentriX — Unified Surveillance System

SentriX is a streamlined surveillance system for turning any phone, tablet, or IP camera into a secure RTSP/HLS streaming source with object detection capabilities. It's built for people who need a simple, powerful wa, and private way to set up a surveillance system or a quick streaming solution.

> ⚠️ Note: SentriX uses a self-signed certificate for RTSPS by default, which can trigger security warnings in some clients. For production use, replace it with a certificate from a trusted CA.

## Table of Contents

- [What It Does](#what-it-does)
- [System Architecture](#system-architecture)
- [Prerequisites](#prerequisites)
- [Surveillance System](#surveillance-system)
- [Object Detection with YOLO](#object-detection-with-yolo)
- [Web Dashboard](#web-dashboard)
- [Troubleshooting](#troubleshooting)

## What It Does

SentriX wraps [MediaMTX](https://github.com/bluenviron/mediamtx), a powerful RTSP/HLS server, with:

- **Unified Surveillance System** — Start streaming server and object detection with a single command
- **Automatic credentials** — Randomly generated publisher/viewer passwords
- **Configuration file support** — Simple YAML configuration for all settings
- **Multiple streaming outputs** — RTSP (low latency), RTSPS (encrypted), and HLS (browser-compatible)
- **Mobile-ready** — Plug-and-play with Larix Broadcaster or other RTSP clients for phone-based streaming
- **YOLO Object Detection** — Process video streams with real-time object detection
- **Web Dashboard** — Modern interface to view all cameras in one place
- **Event-Based Recording** — Record video clips when objects are detected

## System Architecture

SentriX has been streamlined into a clean, modular architecture:

```
video-feed/
├── setup.py                    # Package setup
├── server.crt & server.key     # TLS certificates
└── videofeed/
    ├── surveillance.py         # 🎯 MAIN ENTRY POINT - Unified CLI
    ├── config.py               # 🔧 Configuration management
    ├── constants.py            # 📋 Shared constants  
    ├── utils.py                # 🛠️ Utility functions
    ├── api.py                  # 🔗 Recordings database API
    ├── recorder.py             # 📹 Event-based recording
    ├── visualizer.py           # 🌐 Web interface & API
    ├── detector.py             # 🎯 YOLO object detection
    ├── credentials.py          # 🔐 Secure credential management
    ├── cli.py                  # ⚠️ Deprecated (backward compatibility)
    └── templates/              # 🎨 Web interface templates
```

### Core Modules

- **`surveillance.py`**: Unified command-line interface with all commands:
  - `config` - Start with YAML configuration file
  - `start` - Start with command-line options
  - `quick` - Quick start with defaults
  - `run` - Start streaming server only
  - `detect` - Start object detection only
  - `reset` - Reset stored credentials

- **`config.py`**: Configuration management with `SurveillanceConfig` class for YAML parsing

- **`detector.py`**: YOLO-based object detection with multi-camera support

- **`recorder.py`**: Event-based recording triggered by object detection

- **`visualizer.py`**: FastAPI web interface with live video and recordings browser

## Prerequisites

### Required Software

(Tested on macOS Sequoia 15.4.1 during development)

1. **MediaMTX**: RTSP/HLS streaming server
   ```bash
   # macOS
   brew install mediamtx
   
   # Other platforms
   # See https://github.com/bluenviron/mediamtx?tab=readme-ov-file#installation
   ```

2. **Python 3.8+**: For running the CLI tool
   ```bash
   # Check your version
   python3 --version
   ```

3. **RTSP Client**: For publishing video 
   (Tested during development)
   - **Mobile**: [Larix Broadcaster](https://softvelum.com/larix/) to stream.
   - **Desktop**: [OBS Studio](https://obsproject.com/) to view the feed.

## Surveillance System

The new streamlined surveillance system makes it easy to manage multiple cameras with a single command.

### Quick Start

> The quick start camera path with be `video/camera-1`. You can edit this in `surveillance.py`.

```bash
# Start with default settings (1 camera)
./surveillance.sh quick

# Start using config from configuration file (surveillance.yml)
./surveillance.sh config

# Open the web dashboard
./surveillance.sh dashboard
```

### Configuration

Edit the `surveillance.yml` file to customize your setup:

```yaml
# Camera stream paths
cameras:
  - video/front-door
  - video/backyard
  - video/garage

# Network settings
network:
  bind: "0.0.0.0"  # Listen on all interfaces
  api_port: 3333    # API port for path discovery

# Object detection settings
detection:
  enabled: true
  port: 8080
  model: "yolov8n.pt"
  confidence: 0.4
  resolution:
    width: 960
    height: 540
```

### Features

- **Unified Command**: Start both streaming server and object detection with one command
- **Configuration File**: Easy YAML configuration for all settings
- **Web Dashboard**: Modern interface to view all cameras
- **Multiple Cameras**: Support for multiple camera streams
- **Secure Streaming**: RTSPS encryption with automatic credential management
- **Object Detection**: Real-time YOLO object detection

## Getting Started

Follow these steps to get started with SentriX:

1. **Clone the Repository and Set Up Environment**

```bash
# Clone the repository
git clone https://github.com/soos3d/SentriX-cli.git
cd SentriX-cli

# Set up virtual environment
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# or .\venv\Scripts\activate for Windows

# Install dependencies
pip install -r requirements.txt
```

2. **Using the Surveillance System**

```bash
# Quick start with defaults (1 camera)
./surveillance.sh quick

# Start with configuration file
./surveillance.sh config

# Custom options
./surveillance.sh custom --path video/front-door --path video/backyard
```

3. **Advanced Usage**

```bash
# Start streaming server only (no object detection)
python -m videofeed.surveillance run --path video/front-door --path video/backyard

# Start object detection only
python -m videofeed.surveillance detect --path video/front-door

# Reset credentials
python -m videofeed.surveillance reset
```

4. **Development Setup**

```bash
# Install in development mode
cd video-feed
pip install -e .

# Run directly from source
python -m videofeed.surveillance config
```

### Connection Information

When the server starts, it displays connection information for cameras and viewers:

- **For cameras**: Use the RTSP/RTSPS publishing URL with publisher credentials
- **For viewing**: Use the RTSP/RTSPS/HLS viewer URLs with viewer credentials

> 📱 **Mobile streaming**: Use [Larix Broadcaster](https://softvelum.com/larix/) with the publisher URL and credentials
> 
> 🖥️ **Desktop viewing**: Use [OBS Studio](https://obsproject.com/) or VLC with the viewer URL

## Object Detection with YOLO

SentriX includes real-time object detection capabilities using the [YOLO (You Only Look Once) model from Ultralytics](https://github.com/ultralytics/ultralytics). This feature allows you to process video streams and detect objects in real-time.

### Object Detection Features

- **Real-time Detection**: Process video streams with minimal latency
- **Multiple Models**: Support for various YOLO models (nano, small, medium, large)
- **Configurable Confidence**: Set detection thresholds to reduce false positives
- **Multi-Camera Support**: Process multiple streams simultaneously
- **Event-Based Recording**: Record video clips when objects are detected
- **Web Interface**: View detection results in a browser

### Using Object Detection

```bash
# Start surveillance with object detection enabled
./surveillance.sh config

# Start object detection only
python -m videofeed.surveillance detect --path video/front-door --path video/backyard

# Customize detection parameters
python -m videofeed.surveillance detect \
  --path video/front-door \
  --host 0.0.0.0 --port 8080 \
  --model yolov8n.pt --confidence 0.45 \
  --width 1280 --height 720

# Use direct RTSP URLs
python -m videofeed.surveillance detect \
  --rtsp-url "rtsps://viewer:password@192.168.0.11:8322/video/front-door" \
  --rtsp-url "rtsps://viewer:password@192.168.0.11:8322/video/backyard"
```

### Configuration

You can configure detection settings in `surveillance.yml`:

```yaml
detection:
  enabled: true
  port: 8080
  model: "yolov8n.pt"  # Options: yolov8n.pt, yolov8s.pt, yolov8m.pt, yolov8l.pt
  confidence: 0.4
  resolution:
    width: 960
    height: 540
```

### Recording Detected Objects

SentriX can automatically record video clips when objects are detected:

```bash
# Enable recording with object detection
python -m videofeed.surveillance detect \
  --path video/front-door \
  --record \
  --min-record-confidence 0.5 \
  --pre-buffer 5 \
  --post-buffer 10
```

Recordings are stored in a SQLite database with metadata about detected objects, making them easy to search and filter.

## Web Dashboard

SentriX includes a modern web dashboard for viewing all your camera feeds in one place.

### Dashboard Features

- **Grid View**: View multiple cameras simultaneously
- **Switching Views**: Toggle between live streams and object detection
- **Status Monitoring**: See FPS and detection statistics
- **Responsive Design**: Works on desktop and mobile devices
- **Recordings Browser**: View and manage recorded clips
- **Object Detection Overlays**: See detected objects with bounding boxes and labels

### Using the Dashboard

1. **Start the surveillance system with object detection**:
   ```bash
   ./surveillance.sh config
   ```

2. **Access the web interface**:
   Open your browser and navigate to the URL shown in the terminal output, typically:
   ```
   http://192.168.x.x:8080
   ```

3. **View your cameras** in the grid layout

4. **Browse recordings** by clicking on the Recordings tab

> You need to input the viewer password in the dashboard to view the feeds. This password is automatically generated when you run the surveillance system, is displayed in the terminal output, and it's stored in the local system keychain.

### Dashboard Architecture

The dashboard is built with FastAPI and uses:

- **MJPEG Streaming**: For low-latency video with object detection overlays
- **Jinja2 Templates**: For HTML rendering
- **SQLite Database**: For storing recording metadata
- **REST API**: For accessing recordings and statistics

> 💡 **Tip**: For best performance, use Chrome or Firefox browsers for the dashboard.

## Troubleshooting

### Common Issues

- **Authentication errors**: Ensure you're using the correct credentials shown in the terminal
- **No connection**: Make sure your device and streaming server are on the same network
- **Port issues**: 
  - RTSP: 8554 (unencrypted) / 8322 (encrypted)
  - HLS: 8888
  - Object detection: 8080
  - API: 3333
- **"No stream available"**: The publisher hasn't connected or started streaming yet
- **Detector not starting**: Make sure you have installed all dependencies (`pip install -r requirements.txt`)
- **Dashboard not showing cameras**: Verify the detector is running and accessible

### Surveillance System Issues

- **Script not running**: Make sure `surveillance.sh` is executable (`chmod +x surveillance.sh`)
- **Configuration not loading**: Verify `surveillance.yml` is in the correct location
- **Web dashboard blank**: Check browser console for errors; ensure detector is running
- **Database errors**: If you see SQLite errors, the database might be locked by another process

### Development Issues

- **Module not found errors**: Make sure you're in the right directory or use `python -m videofeed.surveillance`
- **Import errors**: Ensure you've installed the package with `pip install -e .` in the video-feed directory
- **MediaMTX not found**: Install MediaMTX and ensure it's in your PATH

### Network Setup

- Find your computer's IP address:
  ```bash
  ifconfig | grep "inet " | grep -v 127.0.0.1
  ```
- Ensure your firewall allows traffic on the required ports

### Getting Help

If you encounter issues not covered here:

1. Check the logs for error messages
2. Try running with verbose output: `./surveillance.sh custom --verbose`
3. Reset credentials if authentication issues persist: `python -m videofeed.surveillance reset`
