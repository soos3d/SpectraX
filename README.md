# QuickCast — Video Stream Manager

QuickCast is a lightweight CLI tool for turning any phone or webcam into a secure RTSP/HLS streaming source in seconds. It’s built for developers who need a simple, no-fuss way to stream video from a camera to a local machine for processing, testing, or development.

There was no easy tool for this—so I built one.

> ⚠️ Early stage: QuickCast is under active development and may contain bugs. It currently uses a self-signed certificate for RTSPS, which can trigger security warnings in some clients. For production use, replace it with a certificate from a trusted CA.

## What It Does

QuickCast wraps [MediaMTX](https://github.com/bluenviron/mediamtx), a powerful RTSP/HLS server, with:

- One-line CLI startup — instantly launch a secure video stream
- Automatic credentials — randomly generated publisher/viewer passwords
- Configuration file support - use a custom config file to manage credentials and paths if you want
- Multiple streaming outputs — RTSP (low latency), RTSPS (encrypted), and HLS (browser-compatible)
- Mobile-ready — plug-and-play with Larix Broadcaster or other RTSP clients for phone-based streaming

### Usage Options

- **Python Package**: For integrating streaming into your own Python projects
→ Found in `video-feed/videofeed/`
- **CLI-Only Tool**: Standalone script for quick use
→ Found in `cli-only/`
- **Streamlit UI**: Web-based interface for easy stream management
→ Found in `basic-ui/streamlit_ui.py`

All instructions in this `README` use the Python package version, it works the same way as the CLI-only script.

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

## Quickstart

Follow these steps to get started with QuickCast:

1. Clone the Repository

```bash
git clone https://github.com/soos3d/quickcast-cli.git
```

2. Set Up a Virtual Environment

Create and activate a Python virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# or
.\venv\Scripts\activate   # Windows
```

3. Install Dependencies

```bash
pip install -r requirements.txt
```

### Enabling Secure RTSPS Streaming

By default, QuickCast provides both RTSP and RTSPS endpoints. To enable secure RTSPS streaming:

Generate a Self-Signed Certificate

```bash
cd video-feed
openssl genrsa -out server.key 2048
openssl req -new -x509 -sha256 -key server.key -out server.crt -days 3650
```

Move both `server.key` and `server.crt` into the same directory as `feed_cli.py` (should already be there if following the commands above).

> ⚠️ Note: Self-signed certificates may trigger warnings in some clients. For production environments, use a certificate issued by a trusted Certificate Authority.

4. Start the RTSP/HLS Server

The `feed_cli.py` tool provides a simple way to manage your MediaMTX server:

```bash
python3 video-feed/feed_cli.py run
```

This command will start the RTSP/HLS server and display connection information. Here is an example:

```txt
⏳ Starting MediaMTX ...

📹 Stream Path: video/iphone-1

📲 Encrypted RTSPS Publishing:
Use in phone apps (e.g. Larix Broadcaster) or other cameras - encrypted
  URL: rtsps://<host>:8322/video/iphone-1
  User: publisher
  Pass: <password>

📺 Encrypted RTSPS Viewing:
Use in OBS or other video platform- encrypted
  URL: rtsps://viewer:<password>@<host>:8322/video/iphone-1
  • VLC: File > Open Network > rtsps://viewer:<password>@<host>:8322/video/iphone-1
  • OBS: Souces > + > Media Source > Uncheck local File > add RTSP URL to input >
 rtsps://viewer:<password>@<host>:8322/video/iphone-1

🌐 HLS Viewing (browser):
Use in OBS or other video platform- encrypted
  URL: http://<host>:8888/video/iphone-1/index.m3u8
  Auth: viewer / <password>
  Direct URL: http://viewer:<password>@<host>:8888/video/iphone-1/index.m3u8

🎥 Unencrypted RTSP Connection Settings:
Use in phone apps (e.g. Larix Broadcaster) or other cameras - unencrypted
   URL: rtsp://<host>:8554/video/iphone-1
   Username: publisher
   Password: <password>

🎥 Unencrypted RTSP viewing Settings:
Use in phone apps (e.g. Larix Broadcaster) or other cameras - unencrypted

👀 Viewer URL (embedded credentials):
Use in OBS or other video platform- unencrypted
   rtsp://viewer:<password>@<host>:8554/video/iphone-1

Press Ctrl+C to quit.
```


Now simply use the RTSP connection settings to set up your phone or camera to stream to the server. Use the viewer URL to view the stream in any RTSP player like OBS or VLC.

Here is a video on how to set up Larix Broadcaster to stream to the server: [https://www.youtube.com/watch?v=Dhj0_QbtfTw](https://www.youtube.com/watch?v=Dhj0_QbtfTw)

## Streamlit Web Interface

QuickCast includes a basic web-based interface built with Streamlit for easy testing. You can use this provider UI or use the privded view URL to view the stream in any RTSP player like OBS or VLC.

> ⚠️ This UI is meant to be used as a quick test tool and is not recommended for production use. There are many features missing and it is not secure. (for example credentials are stored in the browser's local storage and are not encrypted, uses http instead of https, etc.)

### Running the UI

1. Start the Streamlit interface:
   ```bash
   cd basic-ui
   streamlit run streamlit_ui.py
   ```

2. Open your browser to the displayed URL (typically http://localhost:8501)

3. Enter your stream URL and viewer credentials in the sidebar (it now defaults to the standard `http://localhost:8888/video/iphone-1/index.m3u8`)
  - Use the same credential provided by the CLI or your custom config file

4. Use the Advanced Settings to configure buffer length and reconnection behavior for optimal playback

### Managing Credentials

Credentials are securely stored in your system's keychain:

```bash
# Reset stored publisher/viewer credentials
python3 video-feed/feed_cli.py reset-creds
```

## Server CLI Usage

Use the `--help` flag to list available commands and options:

```bash
python3 video-feed/feed_cli.py run --help
```

### Available commands

The `feed_cli.py` tool provides a simple way to manage your MediaMTX server:

Those are the available commands (assumes you are in the `video-feed` directory):

By default, the server binds to all interfaces (LAN + localhost). Pass `--bind 127.0.0.1` to restrict access to this machine only.

```bash
# Default: bind to all interfaces (LAN + localhost)
python3 video-feed/feed_cli.py run

# Restrict to local-only (loopback)
python3 video-feed/feed_cli.py run --bind 127.0.0.1

# Change the RTSP path (default: video/iphone-1)
python3 video-feed/feed_cli.py run  --path video/camera1

# Use multiple paths (specify --path multiple times)
python3 video-feed/feed_cli.py run  --path video/camera1 --path video/camera2

# Show full configuration details (includes credentials be careful)
python3 video-feed/feed_cli.py run --verbose

# Use a custom config file
python3 video-feed/feed_cli.py run --config ./my-config.yml

# Expose JSON path API (use to to fetch available paths)
python3 video-feed/feed_cli.py run --api-port 3333
```

### Using as a Python Package

You can also use video-feed as a Python package in your own projects:

```python
# Import specific modules
from videofeed.credentials import get_credentials
from videofeed.config import create_config
from videofeed.network import detect_host_ip
from videofeed.server import launch_mediamtx

# Example: Get streaming credentials
creds = get_credentials()
print(f"Publisher: {creds['publish_user']}:{creds['publish_pass']}")
print(f"Viewer: {creds['read_user']}:{creds['read_pass']}")

# Example: Create streaming config
host_ip = detect_host_ip()
paths = ["video/camera1"]
config = create_config(host_ip, paths, creds)

# Use other functionality as needed
```

The modular package structure makes it easy to integrate streaming capabilities into your Python applications without having to run the CLI directly.

## Manual Configuration

If you prefer to run the server with your own configuration file, create a `mediamtx.yml`. 

Here is an example (you manage the credentials here):

```yaml
# Server configuration
paths:
  video/iphone-1:
    source: publisher

# Network & protocol settings
rtspAddress: 0.0.0.0:8554
rtsp: true
hls: true

rtspEncryption: optional
rtspServerKey: server.key # Path to your TLS key
rtspServerCert: server.crt # Path to your TLS certificate

# Authentication configuration
authInternalUsers:
  - user: publisher
    pass: YOUR_PUBLISHER_PASSWORD
    permissions:
      - action: publish
        path: video/iphone-1
  - user: viewer
    pass: YOUR_VIEWER_PASSWORD
    permissions:
      - action: read
        path: video/iphone-1
```

You can also configure multiple paths in the same config file:

```yml
# MediaMTX configuration with multiple stream paths

# Network & protocol settings
rtspAddress: 0.0.0.0:8554
rtsp: true
hls: true

rtspEncryption: optional
rtspServerKey: server.key # Path to your TLS key
rtspServerCert: server.crt # Path to your TLS certificate

# Multiple stream paths
paths:
  front-gate:
    source: publisher
  back-yard:
    source: publisher

# Authentication users
authInternalUsers:
  - user: publisher
    pass: test_publisher_pass
    permissions:
      - action: publish
        path: front-gate
      - action: publish
        path: back-yard

  - user: viewer
    pass: test_viewer_pass
    permissions:
      - action: read
        path: front-gate
      - action: playback
        path: front-gate
      - action: read
        path: back-yard
      - action: playback
        path: back-yard
```

## Streaming Setup

### Publishing Video

1. When the server starts, it displays connection information:
   ```
   🎥 RTSP Connection Settings:
      URL: rtsp://192.168.x.x:8554/video/iphone-1
      Username: publisher
      Password: abc123xyz789
   ```

2. In Larix Broadcaster or any other RTSP client:
   - Open app settings → Connections → Add New → RTSP
   - Enter the URL, username, and password shown in the terminal
   - Start streaming from the camera interface

### Viewing the Stream

1. Use the viewer URL provided when starting the server:
   ```
   👀 Viewer URL (embedded credentials):
      rtsp://viewer:xyz789abc123@192.168.x.x:8554/video/iphone-1
   ```

2. Open this URL in OBS or any RTSP-compatible player:
   - OBS: click + in the Sources panel → select Media Source → name it (e.g. “RTSP Camera”) → click OK, then uncheck “Local File” → paste the URL.
   - FFPLAY: `ffplay rtsp://viewer:xyz789abc123@192.168.x.x:8554/video/iphone-1`


## Troubleshooting

### Common Issues

- **Authentication errors**: Ensure you're using the correct credentials shown in the terminal
- **No connection**: Make sure your device and streaming server are on the same network
- **Port issues**: Default RTSP port is 8554, HLS on 8888
- **"No stream available"**: The publisher hasn't connected or started streaming yet

### Network Setup

- Find your computer's IP address:
  ```bash
  ifconfig | grep "inet " | grep -v 127.0.0.1
  ```
- Ensure your firewall allows traffic on ports 8554 (RTSP) and 8888 (HLS)
