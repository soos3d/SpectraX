# QuickCast—Video Stream Manager

A lightweight CLI tool for quickly setting up a secure RTSP/HLS video streaming server. Turn your phone or webcam into a network camera with proper authentication and easy-to-use streaming URLs.

Basically this is ideal when you want to easily stream from your phone or camera to your computer and then process the video feed. I didn't find any simple tool so I just made one.

> ⚠️ This tool is under active development and may have some bugs. In the current set up it uses a self-signed certificate for RTSPS streaming, which may trigger warnings in some clients. For production environments, use a certificate issued by a trusted Certificate Authority.

## Overview

This tool wraps [MediaMTX](https://github.com/bluenviron/mediamtx) (a powerful RTSP/HLS server) with:

- **Simple CLI**: Start a secure streaming server with one command
- **Auto-Credentials**: Generates and manages secure publisher/viewer passwords
- **Multiple Outputs**: Stream via RTSP (low-latency) or RTSPS (encrypted) or HLS (browser-friendly)
- **Mobile Ready**: Works great with [Larix Broadcaster](https://softvelum.com/larix/) to stream from phones

Ideal for developers who need to quickly get a video feed from a camera into their machine, whether for testing or development.

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
python3 video-feed/feed_cli.py run --bind 0.0.0.0
```

This command will start the RTSP/HLS server and display connection information. Here is an example:

```bash
📲 Encrypted RTSPS Publishing:
Use in phone apps (e.g. Larix Broadcaster) or other cameras - encrypted & secure
   URL: rtsps://YOUR_IP:8322/YOUR_PATH
   Username: publisher
   Password: YOUR_PUBLISHER_PASSWORD

🔐 Encrypted RTSPS Viewer URL (TLS-encrypted):
Use in OBS or other video platform- encrypted & secure
   rtsps://viewer:YOUR_VIEWER_PASSWORD@YOUR_IP:8322/YOUR_PATH

🎥 Unencrypted RTSP Connection Settings:
Use in phone apps (e.g. Larix Broadcaster) or other cameras - unencrypted
   URL: rtsp://YOUR_IP:8554/YOUR_PATH
   Username: publisher
   Password: YOUR_PUBLISHER_PASSWORD

👀 Viewer URL (embedded credentials):
Use in OBS or other video platform- unencrypted
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

### Available commands

The `feed_cli.py` tool provides a simple way to manage your MediaMTX server:

Those are the available commands (assumes you are in the `video-feed` directory):

```bash
# Basic usage (localhost only)
python3 video-feed/feed_cli.py run

# Expose on local network (for phone or IP cameras)
python3 video-feed/feed_cli.py run --bind 0.0.0.0

# Change the RTSP path (default: video/iphone-1)
python3 video-feed/feed_cli.py run --bind 0.0.0.0 --path video/camera1

# Use multiple paths (specify --path multiple times)
python3 video-feed/feed_cli.py run --bind 0.0.0.0 --path video/camera1 --path video/camera2

# Show full configuration details (includes credentials be careful)
python3 video-feed/feed_cli.py run --bind 0.0.0.0 --verbose

# Use a custom config file
python3 video-feed/feed_cli.py run --bind 0.0.0.0 --config ./my-config.yml
```

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
