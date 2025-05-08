"""Visualization server for video-feed with object detection."""

import asyncio
import logging
import os
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

from videofeed.detector import RTSPObjectDetector

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('video-visualizer')

# Create FastAPI app
app = FastAPI(title="Video Feed Visualizer")

# Create templates directory and simple viewer
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
os.makedirs(TEMPLATES_DIR, exist_ok=True)

# Initialize templates
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Global detector instance
detector = None

# Create HTML template for video viewing
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
            width: 90%;
            max-width: 1200px;
            margin: 20px auto;
            padding: 20px;
            background-color: white;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
            border-radius: 5px;
        }
        h1 {
            color: #2c3e50;
        }
        .video-container {
            width: 100%;
            margin: 20px 0;
            text-align: center;
        }
        .video-feed {
            max-width: 100%;
            border: 1px solid #ddd;
            box-shadow: 0 0 5px rgba(0,0,0,0.2);
        }
        .info-panel {
            margin-top: 20px;
            padding: 10px;
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
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Video Feed with YOLO Object Detection</h1>
        
        <div class="info-panel">
            <p><strong>Source:</strong> {{ source }}</p>
            <p><strong>Model:</strong> {{ model }}</p>
        </div>
        
        <div class="video-container">
            <img src="/video/stream" class="video-feed" alt="Video Feed with Object Detection">
        </div>
        
        <div class="status">
            <h3>Status Information</h3>
            <div id="statusInfo">Loading...</div>
        </div>
    </div>
    
    <script>
        // Fetch status info every 2 seconds
        setInterval(async function() {
            try {
                const response = await fetch('/status');
                const data = await response.json();
                document.getElementById('statusInfo').innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
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
async def index(request: Request):
    """Render the video viewer page."""
    global detector
    if detector is None:
        return HTMLResponse("<h1>Detector not initialized. Start the server with a valid RTSP URL.</h1>")
    
    return templates.TemplateResponse(
        "viewer.html", 
        {
            "request": request, 
            "source": detector.source_url,
            "model": detector.model_path
        }
    )

@app.get("/video/stream")
async def video_feed():
    """Stream MJPEG video feed with object detection overlay."""
    global detector
    if detector is None:
        raise HTTPException(status_code=503, detail="Detector not initialized")
    
    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@app.get("/status")
async def get_status():
    """Get the current detector status."""
    global detector
    if detector is None:
        raise HTTPException(status_code=503, detail="Detector not initialized")
    
    return detector.get_status()

async def generate_frames():
    """Generate video frames for streaming."""
    global detector
    
    if detector is None:
        return
    
    while True:
        # Get the latest processed frame as JPEG
        frame_bytes = detector.get_frame_jpeg()
        
        # Yield the frame in MJPEG format
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
        # Control the frame rate of the stream
        await asyncio.sleep(0.03)  # ~30 FPS

def start_visualizer(
    rtsp_url: str,
    host: str = "0.0.0.0",
    port: int = 8000,
    model_path: str = "yolov8n.pt",
    confidence: float = 0.4,
    resolution: tuple = (960, 540)
):
    """Start the visualization server with object detection.
    
    Args:
        rtsp_url: RTSP source URL with credentials
        host: Host to bind the FastAPI server
        port: Port to bind the FastAPI server
        model_path: Path to YOLO model or model name
        confidence: Detection confidence threshold
        resolution: Output resolution (width, height)
    """
    global detector
    
    # Initialize the detector
    detector = RTSPObjectDetector(
        source_url=rtsp_url,
        model_path=model_path,
        confidence=confidence,
        resolution=resolution
    )
    
    # Start the detector
    detector.load_model()
    detector.start()
    
    # Config for Uvicorn
    config = uvicorn.Config(
        app=app,
        host=host,
        port=port,
        log_level="info"
    )
    
    # Start Uvicorn server
    server = uvicorn.Server(config)
    try:
        logger.info(f"Starting visualization server at http://{host}:{port}")
        server.run()
    finally:
        # Cleanup
        if detector:
            detector.stop()
