# QuickCast — Video Stream Manager & Surveillance System

QuickCast is a lightweight CLI tool for turning any phone or webcam into a secure RTSP/HLS streaming source in seconds. It's built for developers who need a simple, no-fuss way to stream video from a camera to a local machine for processing, testing, or development.

The new streamlined surveillance system makes it even easier to set up and manage multiple cameras with object detection.

> ⚠️ Note: QuickCast uses a self-signed certificate for RTSPS by default, which can trigger security warnings in some clients. For production use, replace it with a certificate from a trusted CA.

## Table of Contents

- [What It Does](#what-it-does)
- [Prerequisites](#prerequisites)
- [Surveillance System](#surveillance-system)
- [Quickstart](#quickstart)
- [Object Detection with YOLO](#object-detection-with-yolo)
- [Web Dashboard](#web-dashboard)
- [Manual Configuration](#manual-configuration)
- [Troubleshooting](#troubleshooting)

## What It Does

QuickCast wraps [MediaMTX](https://github.com/bluenviron/mediamtx), a powerful RTSP/HLS server, with:

- **Unified Surveillance System** — Start streaming server and object detection with a single command
- **Automatic credentials** — Randomly generated publisher/viewer passwords
- **Configuration file support** — Simple YAML configuration for all settings
- **Multiple streaming outputs** — RTSP (low latency), RTSPS (encrypted), and HLS (browser-compatible)
- **Mobile-ready** — Plug-and-play with Larix Broadcaster or other RTSP clients for phone-based streaming
- **YOLO Object Detection** — Process video streams with real-time object detection
- **Web Dashboard** — Modern interface to view all cameras in one place

### Usage Options

- **Surveillance System**: Complete solution for multiple cameras with object detection
  → Found in `video-feed/videofeed/surveillance.py`
- **Python Package**: For integrating streaming into your own Python projects
  → Found in `video-feed/videofeed/`
- **CLI-Only Tool**: Standalone script for quick use (limited features)
  → Found in `cli-only/`
- **Web Dashboard**: HTML/JavaScript interface for viewing all cameras
  → Found in `dashboard.html`

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

```bash
# Start with default settings (1 camera)
./surveillance.sh quick

# Start with configuration file
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

## Quickstart

Follow these steps to get started with QuickCast:

1. **Clone the Repository and Set Up Environment**

```bash
# Clone the repository
git clone https://github.com/soos3d/quickcast-cli.git
cd quickcast-cli

# Set up virtual environment
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# or .\venv\Scripts\activate for Windows

# Install dependencies
pip install -r requirements.txt
```

2. **Basic Usage**

```bash
# Start the streaming server (basic mode)
python3 video-feed/feed_cli.py run

# Start with multiple camera paths
python3 video-feed/feed_cli.py run --path video/front-door --path video/backyard

# Enable the API for web dashboard
python3 video-feed/feed_cli.py run --api-port 3333
```

3. **Object Detection**

```bash
# Start object detection on a stream
python3 video-feed/feed_cli.py detect --path video/front-door
```

4. **Using the Surveillance System**

```bash
# Quick start with defaults
./surveillance.sh quick

# Use the configuration file
./surveillance.sh config
```

### Connection Information

When the server starts, it displays connection information for cameras and viewers:

- **For cameras**: Use the RTSP/RTSPS publishing URL with publisher credentials
- **For viewing**: Use the RTSP/RTSPS/HLS viewer URLs with viewer credentials

> 📱 **Mobile streaming**: Use [Larix Broadcaster](https://softvelum.com/larix/) with the publisher URL and credentials
> 
> 🖥️ **Desktop viewing**: Use [OBS Studio](https://obsproject.com/) or VLC with the viewer URL

## Object Detection with YOLO

QuickCast includes real-time object detection capabilities using the [YOLO (You Only Look Once) model from Ultralytics](https://github.com/ultralytics/ultralytics). This feature allows you to process video streams and detect objects in real-time.

### Basic Object Detection

```bash
# Start object detection on a single stream
python3 video-feed/feed_cli.py detect --path video/front-door

# Customize detection parameters
python3 video-feed/feed_cli.py detect \
  --path video/front-door \
  --host 0.0.0.0 --port 8080 \
  --model yolov8n.pt --confidence 0.45 \
  --width 1280 --height 720
```

### Multi-feed Object Detection

```bash
# Process multiple camera feeds
python3 video-feed/feed_cli.py detect --path video/front-door --path video/backyard

# Use direct RTSP URLs
python3 video-feed/feed_cli.py detect \
  --rtsp-url "rtsps://viewer:password@192.168.0.11:8322/video/front-door" \
  --rtsp-url "rtsps://viewer:password@192.168.0.11:8322/video/backyard"
```

### Using the Surveillance System

The new surveillance system makes it easier to run object detection:

```bash
# Start surveillance with object detection enabled
./surveillance.sh config
```

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

## Web Dashboard

QuickCast includes a modern web dashboard for viewing all your camera feeds in one place.

### Features

- **Grid View**: View multiple cameras simultaneously
- **Switching Views**: Toggle between live streams and object detection
- **Status Monitoring**: See FPS and detection statistics
- **Responsive Design**: Works on desktop and mobile devices

### Using the Dashboard

1. **Start the server with API enabled**:
   ```bash
   python3 video-feed/feed_cli.py run --api-port 3333
   ```

2. **Open the dashboard**:
   ```bash
   ./surveillance.sh dashboard
   # Or open dashboard.html directly in your browser
   ```

3. **Enter viewer credentials** when prompted

4. **View your cameras** in the grid layout

### Customizing the Dashboard

The dashboard automatically detects available camera streams through the API. You can customize the layout and view settings directly in the interface.

> 💡 **Tip**: For best performance, use Chrome or Firefox browsers for the dashboard.

## Manual Configuration

While the surveillance system provides a streamlined experience, you can still manually configure the MediaMTX server if needed.

Create a `mediamtx.yml` file with your custom configuration:

```yaml
# Server configuration with multiple stream paths

# Network & protocol settings
rtspAddress: 0.0.0.0:8554
rtsp: true
hls: true

rtspEncryption: optional
rtspServerKey: server.key # Path to your TLS key
rtspServerCert: server.crt # Path to your TLS certificate

# Multiple stream paths
paths:
  front-door:
    source: publisher
  backyard:
    source: publisher
  garage:
    source: publisher

# Authentication users
authInternalUsers:
  - user: publisher
    pass: YOUR_PUBLISHER_PASSWORD
    permissions:
      - action: publish
        path: front-door
      - action: publish
        path: backyard
      - action: publish
        path: garage

  - user: viewer
    pass: YOUR_VIEWER_PASSWORD
    permissions:
      - action: read
        path: front-door
      - action: read
        path: backyard
      - action: read
        path: garage
```

Then run the server with your custom configuration:

```bash
python3 video-feed/feed_cli.py run --config ./mediamtx.yml
```

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
- **Detector not starting**: Make sure you have installed `ultralytics`, `fastapi`, and `uvicorn`
- **Dashboard not showing cameras**: Verify the API is running with `--api-port 3333`

### Surveillance System Issues

- **Script not running**: Make sure `surveillance.sh` is executable (`chmod +x surveillance.sh`)
- **Configuration not loading**: Verify `surveillance.yml` is in the correct location
- **Web dashboard blank**: Check browser console for errors; ensure API is running

### Network Setup

- Find your computer's IP address:
  ```bash
  ifconfig | grep "inet " | grep -v 127.0.0.1
  ```
- Ensure your firewall allows traffic on the required ports
