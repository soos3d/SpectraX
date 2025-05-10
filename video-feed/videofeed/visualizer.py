"""Visualization server for video-feed with object detection."""

import asyncio
import io
import logging
import os
from typing import Dict, List, Optional, Set
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.responses import StreamingResponse, HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from videofeed.detector import DetectorManager

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('video-visualizer')

# Create FastAPI app
app = FastAPI(title="Video Feed Visualizer")

# Configure CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins - replace with specific origins in production
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Create templates directory and simple viewer
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
os.makedirs(TEMPLATES_DIR, exist_ok=True)

# Initialize templates
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Global detector manager instance
detector_manager = None

# Create HTML template for video viewing with multiple feeds
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Video Feed with Object Detection</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f4f4f4;
            color: #333;
        }
        .container {
            width: 95%;
            max-width: 1400px;
            margin: 20px auto;
            padding: 20px;
            background-color: white;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
            border-radius: 5px;
        }
        h1, h2 {
            color: #2c3e50;
        }
        .grid-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        .feed-card {
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            overflow: hidden;
            transition: transform 0.3s, box-shadow 0.3s;
        }
        .feed-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 16px rgba(0,0,0,0.2);
        }
        .feed-card.active {
            border: 3px solid #4CAF50;
        }
        .feed-header {
            padding: 15px;
            background-color: #f8f9fa;
            border-bottom: 1px solid #eee;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .feed-title {
            margin: 0;
            font-size: 18px;
            font-weight: bold;
        }
        .feed-badge {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
        }
        .feed-badge.secure {
            background-color: #4CAF50;
            color: white;
        }
        .feed-badge.standard {
            background-color: #FF9800;
            color: white;
        }
        .video-container {
            width: 100%;
            margin: 0;
            text-align: center;
        }
        .video-feed {
            width: 100%;
            max-width: 100%;
            border-radius: 0 0 8px 8px;
        }
        .current-video-container {
            width: 100%;
            margin: 20px 0;
            text-align: center;
        }
        .current-video-feed {
            max-width: 100%;
            border: 1px solid #ddd;
            box-shadow: 0 0 5px rgba(0,0,0,0.2);
            border-radius: 5px;
            max-height: 70vh;
        }
        .info-panel {
            margin-top: 20px;
            padding: 15px;
            background-color: #f9f9f9;
            border-radius: 5px;
            border-left: 4px solid #3498db;
        }
        .status {
            margin-top: 20px;
            padding: 15px;
            background-color: #e8f5e9;
            border-radius: 5px;
        }
        pre {
            background-color: #f8f8f8;
            padding: 10px;
            border-radius: 4px;
            overflow-x: auto;
            max-height: 300px;
            overflow-y: auto;
        }
        .tabs {
            display: flex;
            margin-bottom: 20px;
            border-bottom: 1px solid #ddd;
        }
        .tab {
            padding: 10px 20px;
            cursor: pointer;
            border: 1px solid transparent;
            border-radius: 4px 4px 0 0;
            margin-right: 5px;
        }
        .tab.active {
            background-color: white;
            border-color: #ddd;
            border-bottom-color: white;
            margin-bottom: -1px;
            font-weight: bold;
        }
        .tab-content {
            display: none;
            padding: 20px;
            background-color: white;
        }
        .tab-content.active {
            display: block;
        }
        .btn {
            display: inline-block;
            padding: 8px 16px;
            background-color: #3498db;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            text-decoration: none;
            transition: background-color 0.3s;
        }
        .btn:hover {
            background-color: #2980b9;
        }
        .btn-danger {
            background-color: #e74c3c;
        }
        .btn-danger:hover {
            background-color: #c0392b;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Video Feed with YOLO Object Detection</h1>
        
        <!-- Tabs Navigation -->
        <div class="tabs">
            <div class="tab active" data-tab="current">Current Feed</div>
            <div class="tab" data-tab="all">All Feeds</div>
            <div class="tab" data-tab="status">Status</div>
        </div>
        
        <!-- Current Feed Tab -->
        <div class="tab-content active" id="current">
            <div class="info-panel">
                <h3 id="current-feed-title">{{ active_feed_name }}</h3>
                <p><strong>Source:</strong> <span id="current-feed-source">{{ active_feed_source }}</span></p>
                <p><strong>Model:</strong> <span id="current-feed-model">{{ model }}</span></p>
                <p><strong>Connection:</strong> <span id="current-feed-connection">{% if active_feed_source and active_feed_source.startswith('rtsps://') %}Encrypted RTSPS 🔒{% else %}Standard RTSP{% endif %}</span></p>
            </div>
            
            <div class="current-video-container">
                <img src="/video/stream" class="current-video-feed" alt="Video Feed with Object Detection">
            </div>
        </div>
        
        <!-- All Feeds Tab -->
        <div class="tab-content" id="all">
            <h2>Available Feeds</h2>
            <div class="grid-container" id="feeds-grid">
                {% for id, feed in feeds.items() %}
                <div class="feed-card {{ 'active' if id == active_feed_id else '' }}" data-feed-id="{{ id }}">
                    <div class="feed-header">
                        <h3 class="feed-title">{{ feed.name }}</h3>
                        {% if feed.source.startswith('rtsps://') %}
                        <span class="feed-badge secure">Secure</span>
                        {% else %}
                        <span class="feed-badge standard">Standard</span>
                        {% endif %}
                    </div>
                    <div class="video-container">
                        <img src="/video/thumbnail/{{ id }}" class="video-feed" alt="{{ feed.name }}">
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
        
        <!-- Status Tab -->
        <div class="tab-content" id="status">
            <h2>Status Information</h2>
            <div id="statusInfo">Loading...</div>
        </div>
    </div>
    
    <script>
        // Tab switching
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                
                tab.classList.add('active');
                document.getElementById(tab.getAttribute('data-tab')).classList.add('active');
            });
        });
        
        // Feed selection
        document.querySelectorAll('.feed-card').forEach(card => {
            card.addEventListener('click', () => {
                const feedId = card.getAttribute('data-feed-id');
                window.location.href = `/?feed=${feedId}`;
            });
        });
        
        // Fetch status info every 2 seconds
        setInterval(async function() {
            try {
                const response = await fetch('/status');
                const data = await response.json();
                document.getElementById('statusInfo').innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
                
                // Update current feed info if we have active feed
                const currentFeedId = new URLSearchParams(window.location.search).get('feed');
                if (currentFeedId && data[currentFeedId]) {
                    const feed = data[currentFeedId];
                    document.getElementById('current-feed-title').textContent = feed.name || 'Unknown';
                    document.getElementById('current-feed-source').textContent = feed.source || 'Unknown';
                    document.getElementById('current-feed-model').textContent = feed.model || 'Unknown';
                    document.getElementById('current-feed-connection').textContent = 
                        feed.source && feed.source.startsWith('rtsps://') ? 'Encrypted RTSPS 🔒' : 'Standard RTSP';
                }
            } catch (error) {
                console.error('Error fetching status:', error);
            }
        }, 2000);
    </script>
</body>
</html>
"""

# Save the HTML template
with open(os.path.join(TEMPLATES_DIR, "viewer.html"), "w") as f:
    f.write(HTML_TEMPLATE)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, feed: Optional[str] = None):
    """Render the video viewer page."""
    global detector_manager
    if detector_manager is None or len(detector_manager.get_all_detectors()) == 0:
        return HTMLResponse("<h1>No active detectors. Start the server with valid RTSP URLs.</h1>")
    
    # Get all detectors status for feed selection
    all_detectors_status = detector_manager.get_detector_status()
    
    # Get active feed information
    active_feed_id = feed or detector_manager.default_detector_id
    active_detector = detector_manager.get_detector(active_feed_id)
    
    if active_detector is None:
        # Redirect to the default feed if the requested one doesn't exist
        return RedirectResponse(url="/")
    
    active_feed_status = detector_manager.get_detector_status(active_feed_id)
    
    return templates.TemplateResponse(
        "viewer.html", 
        {
            "request": request, 
            "active_feed_id": active_feed_id,
            "active_feed_name": active_detector.get_name(),
            "active_feed_source": active_feed_status.get("source", ""),
            "model": active_detector.model_path,
            "feeds": all_detectors_status
        }
    )

@app.get("/video/stream")
async def video_feed(feed: Optional[str] = None):
    """Stream MJPEG video feed with object detection overlay."""
    global detector_manager
    if detector_manager is None:
        raise HTTPException(status_code=503, detail="Detector manager not initialized")
    
    return StreamingResponse(
        generate_frames(feed),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@app.get("/video/thumbnail/{detector_id}")
async def video_thumbnail(detector_id: str):
    """Get a single frame thumbnail from a specific detector."""
    global detector_manager
    if detector_manager is None:
        raise HTTPException(status_code=503, detail="Detector manager not initialized")
    
    # Get a single frame as JPEG
    frame_bytes = detector_manager.get_frame_jpeg(detector_id)
    return StreamingResponse(content=io.BytesIO(frame_bytes), media_type="image/jpeg")

@app.get("/status")
async def get_status(feed: Optional[str] = None):
    """Get the detector status for one or all feeds."""
    global detector_manager
    if detector_manager is None:
        raise HTTPException(status_code=503, detail="Detector manager not initialized")
    
    return detector_manager.get_detector_status(feed)

@app.get("/feeds")
async def get_feeds():
    """Get information about all available feeds."""
    global detector_manager
    if detector_manager is None:
        raise HTTPException(status_code=503, detail="Detector manager not initialized")
    
    feeds = {}
    for detector_id, detector in detector_manager.get_all_detectors().items():
        feeds[detector_id] = {
            "id": detector_id,
            "name": detector.get_name(),
            "source": detector._mask_credentials(detector.source_url)
        }
    
    return {"feeds": feeds, "default": detector_manager.default_detector_id}

async def generate_frames(detector_id: Optional[str] = None):
    """Generate video frames for streaming."""
    global detector_manager
    
    if detector_manager is None:
        return
    
    while True:
        # Get the latest processed frame as JPEG
        frame_bytes = detector_manager.get_frame_jpeg(detector_id)
        
        # Yield the frame in MJPEG format
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
        # Control the frame rate of the stream
        await asyncio.sleep(0.03)  # ~30 FPS

# Imports for shutdown management
import signal
import sys
import threading
import time

# Create a shutdown event to coordinate graceful shutdown
shutdown_requested = threading.Event()

@app.on_event("shutdown")
async def shutdown_detector():
    """Shutdown the detector when FastAPI is shutting down."""
    global detector
    logger.info("Server is shutting down, stopping detector...")
    if detector:
        detector.stop()
        detector = None
    logger.info("Detector stopped successfully")

def force_exit():
    """Force exit after a timeout."""
    time.sleep(3)  # Give a few seconds for graceful shutdown
    logger.warning("Forcing exit after timeout")
    os._exit(0)  # Hard exit

def start_visualizer(
    rtsp_urls: List[str],
    host: str = "0.0.0.0",
    port: int = 8000,
    model_path: str = "yolov8n.pt",
    confidence: float = 0.4,
    resolution: tuple = (960, 540)
):
    """Start the visualization server with object detection for multiple streams.
    
    Args:
        rtsp_urls: List of RTSP source URLs with credentials
        host: Host to bind the FastAPI server
        port: Port to bind the FastAPI server
        model_path: Path to YOLO model or model name
        confidence: Detection confidence threshold
        resolution: Output resolution (width, height)
    """
    global detector_manager
    
    # Initialize the detector manager
    detector_manager = DetectorManager()
    logger.info(f"Initializing detection for {len(rtsp_urls)} streams")
    
    # Define our own signal handler for graceful shutdown
    def handle_exit(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown")
        shutdown_requested.set()
        
        # Stop all detectors BEFORE shutting down uvicorn
        if detector_manager:
            logger.info("Stopping all detectors...")
            detector_manager.stop_all()
            logger.info("All detectors stopped successfully")
        
        # Start a watchdog thread to force exit if graceful shutdown takes too long
        exit_thread = threading.Thread(target=force_exit, daemon=True)
        exit_thread.start()
        
        # We don't call sys.exit() here, instead we'll let uvicorn handle the shutdown
        # This is important because we want uvicorn to clean up properly
    
    # Register our custom signal handlers
    original_sigint = signal.getsignal(signal.SIGINT)
    original_sigterm = signal.getsignal(signal.SIGTERM)
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)
    
    try:
        # Load model once and add all detectors
        logger.info(f"Loading YOLO model: {model_path}")
        for url in rtsp_urls:
            # Add detector to manager
            logger.info(f"Starting detector for stream: {url.split('@')[-1] if '@' in url else url}")
            detector_manager.add_detector(
                source_url=url,
                model_path=model_path,
                confidence=confidence,
                resolution=resolution
            )
        
        # Config for Uvicorn with shutdown timeout
        config = uvicorn.Config(
            app=app,
            host=host,
            port=port,
            log_level="info",
            timeout_keep_alive=2,    # Shorter keep-alive timeout 
            timeout_graceful_shutdown=3  # Shorter graceful shutdown timeout
        )
        
        # Start Uvicorn server
        server = uvicorn.Server(config)
        logger.info(f"Starting visualization server with {len(rtsp_urls)} streams at http://{host}:{port}")
        logger.info("Press Ctrl+C once to exit cleanly.")
        server.run()
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received directly in start_visualizer")
    except Exception as e:
        logger.error(f"Error in visualization server: {e}")
    finally:
        # Restore original signal handlers
        signal.signal(signal.SIGINT, original_sigint)
        signal.signal(signal.SIGTERM, original_sigterm)
        
        # Make sure all detectors are stopped
        if detector_manager:
            logger.info("Final cleanup of all detectors...")
            detector_manager.stop_all()
            detector_manager = None
            logger.info("All visualization resources released")
