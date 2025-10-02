# Basic UI - Standalone Dashboard

This directory contains a standalone HTML dashboard for quick access to your surveillance feeds.

## Usage

### Option 1: Quick Launch (Recommended)
```bash
# From project root
./scripts/surveillance.sh dashboard
```

### Option 2: Direct Access
Open `dashboard.html` directly in your browser:
```bash
# From project root
open video-feed/ui/dashboard.html

# Or on Linux
xdg-open video-feed/ui/dashboard.html
```

## Features

- **Standalone**: No server required, works directly in browser
- **Multi-camera grid view**: View all cameras simultaneously
- **Auto-discovery**: Automatically detects available camera paths via API
- **Manual configuration**: Fallback to manual path entry if API unavailable

## Configuration

The dashboard connects to:
- **Paths API**: `http://localhost:3333/paths` (auto-discovery)
- **Video streams**: `http://localhost:8080/video/stream?feed={id}`

Make sure your surveillance system is running before opening the dashboard:
```bash
./scripts/surveillance.sh config
```

## Note

This is a simplified standalone version. For the full-featured web interface with recordings browser and advanced features, use the integrated dashboard at `http://localhost:8080` when running the surveillance system.
