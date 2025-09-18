#!/bin/bash

# QuickCast Surveillance System Launcher
# Simple script to start your surveillance system

echo "🎥 QuickCast Surveillance System"
echo "================================"
echo ""

# Set the project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if MediaMTX is installed
if ! command -v mediamtx &> /dev/null; then
    echo "❌ MediaMTX is not installed!"
    echo "Please install it first: brew install mediamtx"
    exit 1
fi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Set Python path to include the video-feed directory
export PYTHONPATH="$PROJECT_ROOT/video-feed:$PYTHONPATH"

# Parse command line arguments
case "$1" in
    quick)
        echo "🚀 Quick start mode (1 camera, with detection)"
        cd "$PROJECT_ROOT"
        python3 -m videofeed.surveillance quick
        ;;
    config)
        echo "📋 Starting with configuration file..."
        cd "$PROJECT_ROOT"
        python3 start_surveillance.py
        ;;
    custom)
        echo "⚙️  Custom mode - specify your options:"
        shift
        cd "$PROJECT_ROOT"
        python3 -m videofeed.surveillance start "$@"
        ;;
    dashboard)
        echo "🌐 Opening surveillance dashboard..."
        open "$PROJECT_ROOT/dashboard.html"
        ;;
    *)
        echo "Usage: ./surveillance.sh [quick|config|custom|dashboard]"
        echo ""
        echo "  quick     - Quick start with 1 camera and object detection"
        echo "  config    - Start using surveillance.yml configuration"
        echo "  custom    - Start with custom command line options"
        echo "  dashboard - Open the web dashboard"
        echo ""
        echo "Default: Starting with configuration file..."
        cd "$PROJECT_ROOT"
        python3 start_surveillance.py
        ;;
esac
