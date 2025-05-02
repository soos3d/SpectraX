# QuickCast—Video Stream Manager

A lightweight CLI tool for quickly setting up a secure RTSP/HLS video streaming server. Turn your phone or webcam into a network camera with proper authentication and easy-to-use streaming URLs.

## Overview

This tool wraps [MediaMTX](https://github.com/bluenviron/mediamtx) (a powerful RTSP/HLS server) with:

- **Simple CLI**: Start a secure streaming server with one command
- **Auto-Credentials**: Generates and manages secure publisher/viewer passwords
- **Multiple Outputs**: Stream via RTSP (low-latency) or HLS (browser-friendly)
- **Mobile Ready**: Works great with [Larix Broadcaster](https://softvelum.com/larix/) to stream from phones

Ideal for developers who need to quickly get a video feed from a camera into their machine, whether for testing or development.

> ⚠️ **Note** that at this stage, the RTSP feed is not encrypted, and the credentials are stored in the keychain.

## Prerequisites

### Required Software

(Tested on macOS Sequoia 15.4.1 during development)

1. **MediaMTX**: RTSP/HLS streaming server
   ```bash
   # macOS
   brew install mediamtx
   
   # Other platforms
   # See https://github.com/bluenviron/mediamtx/releases
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

1. Clone this repository:
   ```bash
   git clone https://github.com/soos3d/quickcast-cli.git
   ```

2. Create a virtual environment and activate it:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Unix or MacOS
   # Or
   .\venv\Scripts\activate  # On Windows
   ```

3. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Stat the RTSP/HLS Server

The `feed_cli.py` tool provides a simple way to manage your MediaMTX server:

```bash
python3 video-feed/feed_cli.py run --bind 0.0.0.0
```

This command will start the RTSP/HLS server and display connection information. Here is an example:

```bash
⏳ Starting MediaMTX ...
2025/05/01 21:14:53 INF MediaMTX v1.12.0
2025/05/01 21:14:53 INF configuration loaded from PATH_TO_CONFIG/mediamtx.yml
2025/05/01 21:14:53 INF [RTSP] listener opened on 0.0.0.0:8554 (TCP), :8000 (UDP/RTP), :8001 (UDP/RTCP)
2025/05/01 21:14:53 INF [RTMP] listener opened on :1935
2025/05/01 21:14:53 INF [HLS] listener opened on :8888
2025/05/01 21:14:53 INF [WebRTC] listener opened on :8889 (HTTP), :8189 (ICE/UDP)
2025/05/01 21:14:53 INF [SRT] listener opened on :8890 (UDP)

🎥 RTSP Connection Settings:
   URL: rtsp://YOUR_IP:8554/YOUR_PATH
   Username: publisher
   Password: YOUR_PUBLISHER_PASSWORD

👀 Viewer URL (embedded credentials):
   rtsp://viewer:YOUR_VIEWER_PASSWORD@YOUR_IP:8554/YOUR_PATH

Press Ctrl+C to quit.
```

> ⚠️ Use the --bind 0.0.0.0 option to display the clear connection information for your local network. The camera device must be on the same wifi network as the server.

Now simply use the RTSP connection settings to set up your phone or camera to stream to the server. Use the viewer URL to view the stream in any RTSP player like OBS or VLC.

Here is a video on how to set up Larix Broadcaster to stream to the server: [https://www.youtube.com/watch?v=Dhj0_QbtfTw](https://www.youtube.com/watch?v=Dhj0_QbtfTw)

### Managing Credentials

Credentials are securely stored in your system's keychain:

```bash
# Reset stored publisher/viewer credentials
python3 video-feed/feed_cli.py reset-creds
```

## Server CLI Usage

Use the `--help` flag to list available commands and options:

```bash
python3 video-feed/feed_cli.py --help
```

### Starting the RTSP/HLS Server

The `feed_cli.py` tool provides a simple way to manage your MediaMTX server:

```bash
# Basic usage (localhost only)
python3 video-feed/feed_cli.py run

# Expose on local network (for phone cameras)
python3 video-feed/feed_cli.py run --bind 0.0.0.0

# Change the RTSP path (default: video/iphone-1)
python3 video-feed/feed_cli.py run --path video/camera1

# Show full configuration details (includes credentials be careful)
python3 video-feed/feed_cli.py run --verbose

# Use a custom config file
python3 video-feed/feed_cli.py run --config ./my-config.yml
```

### Managing Credentials

Credentials are securely stored in your system's keychain:

```bash
# Reset stored publisher/viewer credentials
python3 video-feed/feed_cli.py reset-creds
```

## Manual Configuration

If you prefer to run MediaMTX directly, create a `mediamtx.yml` with:

```yaml
# Server configuration
paths:
  video/iphone-1:
    source: publisher

# Network settings
rtspAddress: 0.0.0.0:8554
rtsp: true
hls: true

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

Then start the server:
```bash
mediamtx ./mediamtx/mediamtx.yml
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
