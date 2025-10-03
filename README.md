# SpectraX — Unified Surveillance System

SpectraX is a streamlined surveillance system for turning any phone, tablet, or IP camera into a secure RTSP/HLS streaming source with object detection capabilities. It's built for people who need a simple, powerful, and private way to set up a surveillance system or a quick streaming solution.

> ⚠️ Note: SpectraX uses a self-signed certificate for RTSPS by default, which can trigger security warnings in some clients. For production use, replace it with a certificate from a trusted CA.

## Table of Contents

- [What It Does](#what-it-does)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [Object Detection](#object-detection)
- [Event-Based Recording](#event-based-recording)
- [Web Dashboard](#web-dashboard)
- [Advanced Usage](#advanced-usage)
- [Troubleshooting](#troubleshooting)

## What It Does

SpectraX wraps [MediaMTX](https://github.com/bluenviron/mediamtx), a powerful RTSP/HLS server, with intelligent object detection and recording capabilities. Turn any device with a camera into a smart surveillance system in minutes.

## Key Features

### 🎥 Streaming
- **Multiple Protocols**: RTSP (low latency), RTSPS (encrypted), and HLS (browser-compatible)
- **Mobile-Ready**: Works with Larix Broadcaster and other RTSP apps
- **Multi-Camera Support**: Monitor multiple streams simultaneously
- **Automatic Credentials**: Secure, randomly generated passwords stored in system keychain

### 🤖 AI Object Detection
- **YOLO Integration**: Real-time object detection using YOLOv8 models
- **Customizable Models**: Choose from nano (fast) to large (accurate) models
- **Smart Filtering**: Detect specific objects (person, car, dog, etc.)
- **Visual Overlays**: Bounding boxes and labels on detected objects
- **Adjustable Confidence**: Fine-tune detection sensitivity

### 📹 Event-Based Recording
- **Intelligent Recording**: Automatically record when objects are detected
- **Pre/Post Buffers**: Capture 10 seconds before and after detections
- **Selective Recording**: Only record specific object types
- **SQLite Database**: Searchable metadata for all recordings
- **Storage Management**: Automatic cleanup when storage limits reached

### 🌐 Web Dashboard
- **Live Viewing**: Real-time video with AI detection overlays
- **Recordings Browser**: View and manage all recorded clips
- **Multi-Camera Grid**: Monitor all cameras in one interface
- **REST API**: Access recordings and statistics programmatically
- **Responsive Design**: Works on desktop and mobile browsers

### 🔐 Security
- **RTSPS Encryption**: TLS-encrypted RTSP streams
- **Credential Management**: Secure storage using OS keyring
- **Network Isolation**: Bind to localhost or specific interfaces
- **Self-Signed Certificates**: Included for immediate use

## System Architecture

SpectraX has been streamlined into a clean, modular architecture:

```
root/
├── video-feed/                 # 📦 Main Python package
│   ├── videofeed/              # Core modules
│   │   ├── surveillance.py    # 🎯 MAIN ENTRY POINT - Unified CLI
│   │   ├── config.py          # 🔧 Configuration management
│   │   ├── detector.py        # 🎯 YOLO object detection
│   │   ├── recorder.py        # 📹 Event-based recording
│   │   ├── visualizer.py      # 🌐 Web interface & API
│   │   ├── credentials.py     # 🔐 Secure credential management
│   │   ├── api.py             # 🔗 Recordings database API
│   │   ├── utils.py           # 🛠️ Utility functions
│   │   ├── constants.py       # 📋 Shared constants
│   │   └── templates/         # 🎨 Web interface templates
│   ├── config/                # ⚙️ Configuration files
│   │   └── surveillance.yml   # Main config file
│   ├── models/                # 🤖 YOLO models
│   ├── ui/                    # 🖥️ Web dashboards
│   ├── tests/                 # 🧪 Test suite
│   ├── setup.py               # Package setup
│   └── requirements.txt       # Python dependencies
├── scripts/                   # 🚀 Helper scripts
│   ├── surveillance.sh        # Main launcher
│   └── surveillance.service   # Systemd service
├── docs/                      # 📚 Documentation
└── README.md                  # This file
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

## Getting Started

### Prerequisites

**System Requirements:**
- macOS, Linux, or Windows
- Python 3.8 or higher
- 4GB RAM minimum (8GB recommended for multiple cameras)
- Tested on macOS Sequoia 15.4.1

**Required Software:**

1. **MediaMTX** - RTSP/HLS streaming server
   ```bash
   # macOS
   brew install mediamtx
   
   # Linux
   # Download from https://github.com/bluenviron/mediamtx/releases
   
   # Windows
   # Download from https://github.com/bluenviron/mediamtx/releases
   ```

2. **Python 3.8+**
   ```bash
   python3 --version  # Check your version
   ```

**Recommended Clients:**
- **Mobile Publishing**: [Larix Broadcaster](https://softvelum.com/larix/) (iOS/Android)
- **Desktop Viewing**: [OBS Studio](https://obsproject.com/) or VLC Media Player

### Installation

1. **Clone and Setup**

```bash
# Clone the repository
git clone https://github.com/soos3d/SpectraX.git
cd SpectraX

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# or: .\venv\Scripts\activate  # Windows

# Install dependencies
cd video-feed
pip install -r requirements.txt
cd ..
```

2. **Download YOLO Models** (optional - will auto-download on first use)

```bash
cd video-feed/models
wget https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n.pt
wget https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8l.pt
cd ../..
```

3. **Configure Your System**

Edit `video-feed/config/surveillance.yml` to set your camera paths and preferences.

### Quick Start

```bash
# Start with configuration file (recommended)
./scripts/surveillance.sh config

# Quick start with defaults (1 camera at video/camera-1)
./scripts/surveillance.sh quick

# Open standalone web dashboard
./scripts/surveillance.sh dashboard
```

The system will display connection URLs for your cameras and the web interface.

## Configuration

All settings are managed in `video-feed/config/surveillance.yml`. This is the **only file you need to edit**.

### Basic Configuration

```yaml
# Camera stream paths
cameras:
  - video/front-door
  - video/backyard
  - video/garage

# Network settings
network:
  bind: "127.0.0.1"  # localhost only (secure)
  # bind: "0.0.0.0"  # all interfaces (LAN access)
  api_port: 3333

# Object detection
detection:
  enabled: true
  port: 8080
  model: "yolov8n.pt"  # Options: yolov8n, yolov8s, yolov8m, yolov8l
  confidence: 0.4
  resolution:
    width: 960
    height: 540
```

### Advanced Configuration

**Detection Filtering:**
```yaml
detection:
  filters:
    classes: ["person", "car", "dog"]  # Only detect these (empty = all)
    min_area: 1000  # Ignore tiny detections
    max_area: 500000  # Ignore huge detections
```

**Visual Appearance:**
```yaml
appearance:
  box:
    thickness: 2
    color: "yellow"  # green, red, blue, yellow, white, black, roboflow
  label:
    text_scale: 0.5
    position: "top_left"
```

**Recording Settings:**
```yaml
recording:
  enabled: true
  min_confidence: 0.5
  pre_buffer_seconds: 10  # Record before detection
  post_buffer_seconds: 10  # Record after detection
  max_storage_gb: 10.0
  recordings_dir: "~/video-feed-recordings"
  record_objects: ["person", "car", "dog"]  # Only record these
```

See the config file for complete documentation of all options.

### Connecting Your Cameras

When the system starts, it displays connection URLs:

**📱 For Mobile Cameras (Publishing):**
1. Install [Larix Broadcaster](https://softvelum.com/larix/) on your phone
2. Use the RTSPS URL shown in the terminal
3. Enter the publisher username and password
4. Start streaming!

**🖥️ For Viewing:**
- **Web Dashboard**: Open the URL shown (e.g., `http://192.168.x.x:8080`)
- **OBS/VLC**: Use the viewer RTSPS URL with credentials
- **Browser HLS**: Use the HLS URL for browser-based viewing

## Object Detection

SpectraX uses [YOLOv8 from Ultralytics](https://github.com/ultralytics/ultralytics) for real-time object detection on your video streams.

### Available Models

| Model | Size | Speed | Accuracy | Use Case |
|-------|------|-------|----------|----------|
| `yolov8n.pt` | ~6 MB | Fastest | Good | Multiple cameras, limited hardware |
| `yolov8s.pt` | ~22 MB | Fast | Better | Balanced performance |
| `yolov8m.pt` | ~52 MB | Medium | Very Good | Better accuracy needed |
| `yolov8l.pt` | ~88 MB | Slow | Excellent | Single camera, good hardware |
| `yolov8x.pt` | ~136 MB | Slowest | Best | Maximum accuracy |

Models are automatically loaded from `video-feed/models/` or downloaded on first use.

### Detection Features

**Smart Filtering:**
- Detect only specific objects (person, car, dog, cat, etc.)
- Filter by detection size (ignore tiny or huge detections)
- Adjust confidence threshold to reduce false positives

**Visual Customization:**
- Choose bounding box colors and thickness
- Customize label appearance and position
- Real-time overlay on video streams

**Performance Tuning:**
- Adjust processing resolution for speed vs. quality
- Configure frame buffer size
- Set reconnection intervals

### Detectable Objects

YOLO can detect 80+ object classes including:
- **People**: person
- **Vehicles**: car, truck, bus, motorcycle, bicycle
- **Animals**: dog, cat, bird, horse, cow, sheep
- **Common items**: backpack, umbrella, handbag, suitcase, bottle, cup, chair, couch, bed, dining table, laptop, cell phone

See [COCO dataset classes](https://github.com/ultralytics/ultralytics/blob/main/ultralytics/cfg/datasets/coco.yaml) for the complete list.

## Event-Based Recording

Automatically record video clips when objects are detected.

### How It Works

1. **Continuous Buffering**: System maintains a rolling buffer of recent frames
2. **Detection Trigger**: When an object is detected, recording starts
3. **Pre-Buffer**: Includes 10 seconds *before* the detection
4. **Post-Buffer**: Continues 10 seconds *after* the last detection
5. **Metadata Storage**: All recordings saved to SQLite database with searchable metadata

### Recording Configuration

```yaml
recording:
  enabled: true
  min_confidence: 0.5  # Only record high-confidence detections
  pre_buffer_seconds: 10
  post_buffer_seconds: 10
  max_storage_gb: 10.0
  recordings_dir: "~/video-feed-recordings"
  record_objects: ["person", "car", "dog"]  # Selective recording
```

### Storage Management

- **Automatic Cleanup**: Oldest recordings deleted when storage limit reached
- **Metadata Preserved**: Database tracks all recordings with timestamps, objects detected, and confidence scores
- **Efficient Format**: MP4 videos with H.264 encoding

### Accessing Recordings

- **Web Dashboard**: Browse and play recordings in your browser
- **REST API**: Query recordings programmatically
- **File System**: Direct access to MP4 files in recordings directory
- **Database**: SQLite database for custom queries

## Web Dashboard

Modern web interface for monitoring cameras and managing recordings.

### Features

- **Live Video**: Real-time MJPEG streams with AI detection overlays
- **Multi-Camera Grid**: View all cameras simultaneously
- **Recordings Browser**: Search, filter, and play recorded clips
- **Statistics**: FPS, detection counts, and system status
- **REST API**: Programmatic access to all features
- **Responsive**: Works on desktop and mobile browsers

### Accessing the Dashboard

**Option 1: Integrated Dashboard (Recommended)**

1. Start the system:
   ```bash
   ./scripts/surveillance.sh config
   ```

2. Open the URL shown in terminal (e.g., `http://192.168.x.x:8080`)

3. The dashboard shows:
   - Live video feeds with detection overlays
   - FPS and detection statistics
   - Recordings tab for browsing saved clips

**Option 2: Standalone HTML Dashboard**

For quick access without the full system:

```bash
# Open standalone dashboard
./scripts/surveillance.sh dashboard

# Or open directly in browser
open video-feed/ui/dashboard.html
```

**Note**: The standalone dashboard requires the surveillance system to be running to connect to video streams.

### API Endpoints

**Status and Streams:**
- `GET /status` - System status and statistics
- `GET /video/stream` - MJPEG video stream with detections
- `GET /paths` - Available camera paths

**Recordings:**
- `GET /api/recordings` - List all recordings
- `GET /api/recordings/{id}` - Get specific recording
- `GET /api/recordings/stats` - Recording statistics
- `GET /recordings/{filename}` - Download recording file

### Technology Stack

- **Backend**: FastAPI + Uvicorn
- **Streaming**: MJPEG for low-latency video
- **Database**: SQLite for recording metadata
- **Templates**: Jinja2 for HTML rendering
- **Detection**: Real-time YOLO inference

## Advanced Usage

### Command Line Options

**Start with custom settings:**
```bash
./scripts/surveillance.sh custom --path video/camera-1 --path video/camera-2
```

**Python module usage:**
```bash
# Start streaming server only (no detection)
python -m videofeed.surveillance run --path video/front-door

# Start detection only (existing stream)
python -m videofeed.surveillance detect --rtsp-url "rtsps://viewer:pass@host:8322/video/cam"

# Reset stored credentials
python -m videofeed.surveillance reset
```

### Development Mode

```bash
cd video-feed
pip install -e .  # Editable install

# Run tests
pytest

# Run directly
python -m videofeed.surveillance config
```

### Systemd Service (Linux)

For running as a system service:

```bash
# Copy service file
sudo cp scripts/surveillance.service /etc/systemd/system/

# Edit paths in service file
sudo nano /etc/systemd/system/surveillance.service

# Enable and start
sudo systemctl enable surveillance
sudo systemctl start surveillance

# Check status
sudo systemctl status surveillance
```

### Custom TLS Certificates

Replace self-signed certificates with your own:

```yaml
security:
  use_tls: true
  tls_key: "/path/to/your/private.key"
  tls_cert: "/path/to/your/certificate.crt"
```

## Troubleshooting

### Common Issues

**MediaMTX fails to start:**
- Check if MediaMTX is installed: `which mediamtx`
- Verify ports 8322, 8554, 8888 are not in use
- Check terminal output for specific error messages

**Connection refused errors:**
- Ensure MediaMTX is running (check terminal output)
- Verify network bind address in config (127.0.0.1 vs 0.0.0.0)
- Check firewall settings

**No video in dashboard:**
- Verify camera is publishing to the correct URL
- Check credentials match those shown in terminal
- Ensure detector is running (look for "Loading model" message)

**Recording not working:**
- Check `recording.enabled: true` in config
- Verify recordings directory exists and is writable
- Check `record_objects` list matches detected objects
- Ensure sufficient disk space

**Model downloads to wrong location:**
- Models should auto-load from `video-feed/models/`
- If not, manually download to that directory
- Check file permissions

### Configuration Issues

**Script not executable:**
```bash
chmod +x scripts/surveillance.sh
```

**Config file not found:**
- Verify file exists at `video-feed/config/surveillance.yml`
- Check file permissions (should be readable)

**Module import errors:**
```bash
# Install in development mode
cd video-feed
pip install -e .
```

### Network Setup

**Find your IP address:**
```bash
# macOS/Linux
ifconfig | grep "inet " | grep -v 127.0.0.1

# Windows
ipconfig
```

**Port Configuration:**
- RTSP: 8554 (unencrypted)
- RTSPS: 8322 (encrypted)
- HLS: 8888 (browser streaming)
- Detection: 8080 (web dashboard)
- API: 3333 (paths discovery)

### Performance Optimization

**Slow detection:**
- Use smaller model (yolov8n.pt instead of yolov8l.pt)
- Reduce resolution in config
- Decrease frame buffer size
- Limit number of cameras

**High CPU usage:**
- Lower detection resolution
- Increase confidence threshold (fewer detections)
- Use hardware acceleration if available

**Recording lag:**
- Reduce pre/post buffer seconds
- Lower video resolution
- Check disk I/O performance

### Getting Help

1. **Check logs**: Terminal output shows detailed error messages
2. **Reset credentials**: `python -m videofeed.surveillance reset`
3. **Test components separately**:
   - Test MediaMTX: `mediamtx --help`
   - Test Python: `python -m videofeed.surveillance --help`
4. **Review documentation**: See `docs/` folder for detailed guides

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

## License

See [LICENSE](LICENSE) file for details.

## Acknowledgments

- [MediaMTX](https://github.com/bluenviron/mediamtx) - Excellent RTSP/HLS server
- [Ultralytics YOLOv8](https://github.com/ultralytics/ultralytics) - State-of-the-art object detection
- [Supervision](https://github.com/roboflow/supervision) - Computer vision utilities
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
