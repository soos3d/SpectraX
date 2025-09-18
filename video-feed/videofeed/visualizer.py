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

from fastapi import FastAPI, HTTPException, Request, Query, Body, File, UploadFile
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn
import os

from videofeed.detector import DetectorManager
from videofeed.credentials import get_credentials, APP_NAME
from videofeed.recorder import RecordingManager
from videofeed.api import RecordingsAPI

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

# Configure templates
templates_path = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_path)

# Authentication schema for simple credential verification
class UserCredentials(BaseModel):
    username: str
    password: str

# Global instances
detector_manager = None
recordings_api = None

# Directory for recordings is configured at runtime
recordings_directory = None


def set_detector_manager(manager):
    """Set the global detector manager instance.
    
    This function is called by the surveillance system to set the detector manager.
    """
    global detector_manager
    detector_manager = manager
    logger.info(f"Detector manager set with {len(manager.get_all_detectors())} detectors")
    return detector_manager


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

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Render the main viewer page."""
    return templates.TemplateResponse("viewer.html", {"request": request})

@app.get("/recordings.html", response_class=HTMLResponse)
async def recordings_page(request: Request):
    """Render the recordings page."""
    return templates.TemplateResponse("recordings.html", {"request": request})

@app.get("/recordings/{file_path:path}")
async def serve_recording_file(file_path: str):
    """Serve a recording file (video or thumbnail)."""
    global recordings_directory
    
    if not recordings_directory:
        raise HTTPException(status_code=404, detail="Recording directory not configured")
    
    file_full_path = os.path.join(recordings_directory, file_path)
    
    if not os.path.exists(file_full_path):
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
    
    return FileResponse(file_full_path)

@app.get("/status")
async def get_status(feed: Optional[str] = None):
    """Get the detector status for one or all feeds."""
    global detector_manager
    if detector_manager is None:
        raise HTTPException(status_code=503, detail="Detector manager not initialized")
    
    return detector_manager.get_detector_status(feed)

@app.get("/api/recordings")
async def get_recordings(
    stream_id: Optional[str] = None,
    limit: int = Query(100, gt=0, le=1000),
    offset: int = Query(0, ge=0),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    object_type: Optional[str] = None,
    min_confidence: Optional[float] = None,
    sort_by: str = Query("timestamp", regex=r"^(timestamp|confidence|duration)$"),
    sort_order: str = Query("desc", regex=r"^(asc|desc)$")
):
    """Get list of recordings from the database with filtering and sorting options."""
    global recordings_api, recordings_directory
    
    if recordings_api is None:
        raise HTTPException(status_code=503, detail="Recording API not initialized")
    
    try:
        # Get recordings
        recordings = recordings_api.get_recordings(
            stream_id=stream_id,
            limit=limit,
            offset=offset,
            start_date=start_date,
            end_date=end_date,
            object_type=object_type,
            min_confidence=min_confidence,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        # Get total count for pagination
        total = recordings_api.get_recordings_count(
            stream_id=stream_id,
            start_date=start_date,
            end_date=end_date,
            object_type=object_type,
            min_confidence=min_confidence
        )
        
        # Transform file paths to URLs
        for rec in recordings:
            if rec.get('file_path'):
                rel_path = os.path.relpath(rec['file_path'], recordings_directory)
                rec['file_url'] = f"/recordings/{rel_path}"
            
            if rec.get('thumbnail_path'):
                rel_path = os.path.relpath(rec['thumbnail_path'], recordings_directory)
                rec['thumbnail_url'] = f"/recordings/{rel_path}"
        
        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "recordings": recordings
        }
    except Exception as e:
        logger.error(f"Error retrieving recordings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/recordings/{recording_id}")
async def delete_recording(recording_id: int):
    """Delete a recording by ID."""
    global recordings_api
    
    if recordings_api is None:
        raise HTTPException(status_code=503, detail="Recording API not initialized")
    
    try:
        success = recordings_api.delete_recording(recording_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Recording {recording_id} not found")
        
        return {"success": True, "message": f"Recording {recording_id} deleted"}
    except Exception as e:
        logger.error(f"Error deleting recording {recording_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/recordings/{recording_id}")
async def get_recording_detail(recording_id: int):
    """Get detailed information about a specific recording."""
    global recordings_api, recordings_directory
    
    if recordings_api is None:
        raise HTTPException(status_code=503, detail="Recording API not initialized")
    
    try:
        recording = recordings_api.get_recording_by_id(recording_id)
        if not recording:
            raise HTTPException(status_code=404, detail=f"Recording {recording_id} not found")
        
        # Transform file paths to URLs
        if recording.get('file_path'):
            rel_path = os.path.relpath(recording['file_path'], recordings_directory)
            recording['file_url'] = f"/recordings/{rel_path}"
        
        if recording.get('thumbnail_path'):
            rel_path = os.path.relpath(recording['thumbnail_path'], recordings_directory)
            recording['thumbnail_url'] = f"/recordings/{rel_path}"
        
        return recording
    except Exception as e:
        logger.error(f"Error retrieving recording {recording_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/alerts")
async def get_alerts(
    limit: int = Query(100, gt=0, le=1000),
    offset: int = Query(0, ge=0),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    object_type: Optional[str] = None,
    min_confidence: float = Query(0.5, ge=0, le=1.0)
):
    """Get detection alerts from recordings, for event monitoring."""
    global recordings_api, recordings_directory
    
    if recordings_api is None:
        raise HTTPException(status_code=503, detail="Recording API not initialized")
    
    try:
        # Get alerts
        alerts = recordings_api.get_alerts(
            limit=limit,
            offset=offset,
            start_date=start_date,
            end_date=end_date,
            object_type=object_type,
            min_confidence=min_confidence
        )
        
        # Get total count for pagination
        total = recordings_api.get_alerts_count(
            start_date=start_date,
            end_date=end_date,
            object_type=object_type,
            min_confidence=min_confidence
        )
        
        # Transform file paths to URLs
        for alert in alerts:
            if alert.get('thumbnail_path'):
                rel_path = os.path.relpath(alert['thumbnail_path'], recordings_directory)
                alert['thumbnail_url'] = f"/recordings/{rel_path}"
        
        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "alerts": alerts
        }
    except Exception as e:
        logger.error(f"Error retrieving alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats/objects")
async def get_object_stats(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    stream_id: Optional[str] = None
):
    """Get statistics about detected objects over time."""
    global recordings_api
    
    if recordings_api is None:
        raise HTTPException(status_code=503, detail="Recording API not initialized")
    
    try:
        stats = recordings_api.get_object_stats(
            start_date=start_date,
            end_date=end_date,
            stream_id=stream_id
        )
        return {"stats": stats}
    except Exception as e:
        logger.error(f"Error retrieving object statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats/times")
async def get_time_stats(
    object_type: Optional[str] = None,
    days: int = Query(7, gt=0, le=90),
    stream_id: Optional[str] = None
):
    """Get detection statistics by time of day."""
    global recordings_api
    
    if recordings_api is None:
        raise HTTPException(status_code=503, detail="Recording API not initialized")
    
    try:
        stats = recordings_api.get_time_stats(
            object_type=object_type,
            days=days,
            stream_id=stream_id
        )
        return {"stats": stats}
    except Exception as e:
        logger.error(f"Error retrieving time statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/streams")
async def get_streams():
    """Get list of all video streams with recording statistics."""
    global detector_manager, recordings_api
    
    if detector_manager is None:
        raise HTTPException(status_code=503, detail="Detector manager not initialized")
        
    # If recording API isn't available, we can't get stats
    if recordings_api is None:
        streams = detector_manager.get_detector_status()
        for stream in streams.values():
            stream['recording_stats'] = None
        return {"streams": list(streams.values())}
    
    try:
        streams = detector_manager.get_detector_status()
        for stream_id, stream in streams.items():
            # Get stats for this stream
            stats = recordings_api.get_stream_stats(stream_id)
            stream['recording_stats'] = stats
            
        return {"streams": list(streams.values())}
    except Exception as e:
        logger.error(f"Error retrieving streams: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
        logger.info("Stopping all detectors...")
        detector_manager.stop_all()
        logger.info("All detectors stopped successfully")
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
    resolution: tuple = (960, 540),
    enable_recording: bool = False,
    recordings_dir: Optional[str] = None,
    min_confidence: float = 0.5,
    pre_detection_buffer: int = 5,
    post_detection_buffer: int = 5
):
    """Start the API server with object detection for multiple streams.
    
    Args:
        rtsp_urls: List of RTSP source URLs with credentials
        host: Host to bind the FastAPI server
        port: Port to bind the FastAPI server
        model_path: Path to YOLO model or model name
        confidence: Detection confidence threshold
        resolution: Output resolution (width, height)
        enable_recording: Whether to enable recording of detected objects
        recordings_dir: Directory to store recordings
    """
    global detector_manager, recordings_api
    
    # Initialize the recording manager if enabled
    recording_manager = None
    if enable_recording:
        logger.info("Initializing recording manager")
        recording_manager = RecordingManager(
            recordings_dir=recordings_dir,
            min_confidence=min_confidence,
            pre_detection_buffer=pre_detection_buffer,
            post_detection_buffer=post_detection_buffer
        )
        recording_manager.start()
        
        # Store the recordings directory for serving files
        global recordings_directory
        recordings_directory = recording_manager.recordings_dir
        
        # Initialize the recordings API with shared database connection
        logger.info("Initializing recordings API with shared connection")
        recordings_api = RecordingsAPI(db_connection=recording_manager.get_database_connection())
    
    # Initialize the detector manager
    detector_manager = DetectorManager(recording_manager=recording_manager)
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
        
        # Close the API connection
        if recordings_api:
            logger.info("Closing recordings API connection...")
            recordings_api.close()
            recordings_api = None
            
        logger.info("All API server resources released")