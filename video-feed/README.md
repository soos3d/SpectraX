# VideoFeed Package

The core Python package for SentriX surveillance system.

## Package Structure

```
video-feed/
├── videofeed/              # Main Python package
│   ├── surveillance.py     # Main CLI entry point
│   ├── config.py           # Configuration management
│   ├── detector.py         # YOLO object detection
│   ├── recorder.py         # Event-based recording
│   ├── visualizer.py       # Web dashboard & API
│   ├── credentials.py      # Secure credential storage
│   ├── api.py              # Recordings database API
│   ├── utils.py            # Utility functions
│   ├── constants.py        # Shared constants
│   ├── routes/             # FastAPI route modules
│   └── templates/          # Jinja2 web templates
├── tests/                  # Test suite
├── config/                 # Configuration files
│   └── surveillance.yml    # Main configuration
├── models/                 # YOLO model files
│   ├── yolov8n.pt         # Nano model (fastest)
│   └── yolov8l.pt         # Large model (most accurate)
├── ui/                     # Web dashboards
│   └── dashboard.html      # Standalone HTML dashboard
├── setup.py                # Package setup
├── requirements.txt        # Python dependencies
├── pytest.ini              # Test configuration
├── server.crt              # TLS certificate
└── server.key              # TLS private key
```

## Installation

### Development Mode

```bash
cd video-feed
pip install -e .
```

### Production Mode

```bash
cd video-feed
pip install -r requirements.txt
```

## Usage

### As a Python Module

```bash
# Start with configuration file
python -m videofeed.surveillance config

# Quick start with defaults
python -m videofeed.surveillance quick

# Custom options
python -m videofeed.surveillance start --path video/camera-1 --detector

# Object detection only
python -m videofeed.surveillance detect --path video/camera-1

# Reset credentials
python -m videofeed.surveillance reset
```

### As Installed Command

After installing with `pip install -e .`:

```bash
surveillance config
surveillance quick
surveillance start --path video/camera-1
```

## Configuration

Edit `config/surveillance.yml` to customize:

- Camera stream paths
- Network settings (bind address, ports)
- Object detection settings (model, confidence, resolution)
- Recording settings (buffers, storage limits)
- Visual appearance (box colors, labels)
- Security settings (TLS certificates)

See the main project README for detailed configuration options.

## Development

### Running Tests

```bash
cd video-feed
pytest
```

### Code Structure

- **surveillance.py**: Main entry point with Typer CLI commands
- **config.py**: YAML configuration parsing and management
- **detector.py**: Multi-camera YOLO detection with threading
- **recorder.py**: Event-based video recording with SQLite metadata
- **visualizer.py**: FastAPI web server with MJPEG streaming
- **credentials.py**: OS keyring integration for secure storage
- **api.py**: REST API for recordings and statistics

## Dependencies

Core dependencies:
- **typer**: CLI framework
- **fastapi/uvicorn**: Web server
- **opencv-python-headless**: Video processing
- **ultralytics**: YOLO object detection
- **torch/torchvision**: Deep learning backend
- **keyring**: Secure credential storage
- **PyYAML**: Configuration management

See `requirements.txt` for complete list with versions.

## Entry Points

The package provides two console scripts:
- `videofeed`: Main command
- `surveillance`: Alias for convenience

Both point to `videofeed.surveillance:app`.
