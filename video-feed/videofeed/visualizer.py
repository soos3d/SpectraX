"""API server for video-feed with object detection."""

import asyncio
import io
import logging
import os
import signal
import sys
import threading
import time
from typing import Dict, List, Optional, Set

from fastapi import FastAPI, HTTPException, Request, Query, Body
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from videofeed.detector import DetectorManager
from videofeed.credentials import get_credentials, APP_NAME

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('video-api-server')

# Create FastAPI app
app = FastAPI(title="Video Feed API")

# Configure CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins - replace with specific origins in production
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Authentication schema for simple credential verification
class UserCredentials(BaseModel):
    username: str
    password: str

# Global detector manager instance
detector_manager = None



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

@app.get("/video/jpeg/{detector_id}")
async def video_frame(detector_id: str):
    """Get a single frame as JPEG from a specific detector."""
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

# Create a shutdown event to coordinate graceful shutdown
shutdown_requested = threading.Event()

@app.on_event("shutdown")
async def shutdown_detector():
    """Shutdown the detector when FastAPI is shutting down."""
    global detector_manager
    logger.info("Server is shutting down, stopping detector...")
    if detector_manager:
        detector_manager.stop_all()
        detector_manager = None
    logger.info("Detector stopped successfully")


# Simple credential verification endpoint
@app.post("/auth/verify")
async def verify_credentials(user_creds: UserCredentials):
    """Verify if credentials match those in the system keychain."""
    creds = get_credentials()
    
    # Check publisher credentials
    if user_creds.username == creds["publish_user"] and user_creds.password == creds["publish_pass"]:
        return {
            "authenticated": True,
            "user_type": "publisher",
            "username": creds["publish_user"]
        }
    
    # Check viewer credentials
    if user_creds.username == creds["read_user"] and user_creds.password == creds["read_pass"]:
        return {
            "authenticated": True,
            "user_type": "viewer",
            "username": creds["read_user"]
        }
    
    # Invalid credentials
    raise HTTPException(
        status_code=401,
        detail="Invalid credentials"
    )

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
    """Start the API server with object detection for multiple streams.
    
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
        logger.info(f"Starting API server with {len(rtsp_urls)} streams at http://{host}:{port}")
        logger.info("Press Ctrl+C once to exit cleanly.")
        server.run()
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received directly in start_api_server")
    except Exception as e:
        logger.error(f"Error in API server: {e}")
    finally:
        # Restore original signal handlers
        signal.signal(signal.SIGINT, original_sigint)
        signal.signal(signal.SIGTERM, original_sigterm)
        
        # Make sure all detectors are stopped
        if detector_manager:
            logger.info("Final cleanup of all detectors...")
            detector_manager.stop_all()
            detector_manager = None
            logger.info("All API server resources released")