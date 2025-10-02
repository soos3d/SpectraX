"""Recording management routes."""

import logging
import os
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api/recordings", tags=["recordings"])

logger = logging.getLogger(__name__)

# Global references (set by visualizer)
recordings_api = None
recordings_directory = None


def set_recordings_api(api):
    """Set the recordings API instance."""
    global recordings_api
    recordings_api = api


def set_recordings_directory(directory: str):
    """Set the recordings directory path."""
    global recordings_directory
    recordings_directory = directory


def initialize_recordings_api():
    """Initialize the recordings API if not already initialized.
    
    Returns:
        bool: True if initialization was successful, False otherwise
    """
    global recordings_api, recordings_directory
    
    if recordings_api is not None:
        return True
    
    try:
        from videofeed.api import RecordingsAPI
        
        # First check if recordings_directory is set
        if recordings_directory:
            # Ensure path is expanded properly
            expanded_dir = os.path.expanduser(recordings_directory)
            db_path = os.path.join(expanded_dir, "recordings.db")
            logger.info(f"Looking for database at: {db_path}")
            
            if os.path.exists(db_path):
                logger.info(f"Initializing recordings API with database: {db_path}")
                recordings_api = RecordingsAPI(db_path=db_path)
                logger.info("Successfully initialized recordings API")
                return True
        
        # If not found, try the default location in user's home directory
        home_db_path = os.path.expanduser("~/video-feed-recordings/recordings.db")
        logger.info(f"Looking for database at home path: {home_db_path}")
        
        if os.path.exists(home_db_path):
            logger.info(f"Initializing recordings API with database from home directory: {home_db_path}")
            recordings_api = RecordingsAPI(db_path=home_db_path)
            
            # Also set the recordings_directory if it wasn't set before
            if not recordings_directory:
                recordings_directory = os.path.dirname(home_db_path)
                logger.info(f"Setting recordings directory to: {recordings_directory}")
                
            logger.info("Successfully initialized recordings API from home directory")
            return True
        
        # If we get here, we couldn't find the database
        logger.error(f"Database file not found in configured directory or home directory")
        return False
    except Exception as e:
        logger.error(f"Failed to initialize recordings API: {e}")
        return False


@router.get("")
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
    
    # Try to initialize recordings API if needed
    if not initialize_recordings_api():
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
                try:
                    # Ensure both paths are absolute before computing relative path
                    abs_file_path = os.path.abspath(os.path.expanduser(rec['file_path']))
                    abs_recordings_dir = os.path.abspath(os.path.expanduser(recordings_directory))
                    rel_path = os.path.relpath(abs_file_path, abs_recordings_dir)
                    rec['file_url'] = f"/recordings/{rel_path}"
                except Exception as e:
                    logger.error(f"Error creating file URL: {e}")
                    rec['file_url'] = None
            
            if rec.get('thumbnail_path'):
                try:
                    # Ensure both paths are absolute before computing relative path
                    abs_thumb_path = os.path.abspath(os.path.expanduser(rec['thumbnail_path']))
                    abs_recordings_dir = os.path.abspath(os.path.expanduser(recordings_directory))
                    rel_path = os.path.relpath(abs_thumb_path, abs_recordings_dir)
                    rec['thumbnail_url'] = f"/recordings/{rel_path}"
                except Exception as e:
                    logger.error(f"Error creating thumbnail URL: {e}")
                    rec['thumbnail_url'] = None
        
        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "recordings": recordings
        }
    except Exception as e:
        logger.error(f"Error retrieving recordings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{recording_id}")
async def delete_recording(recording_id: int):
    """Delete a recording by ID."""
    global recordings_api
    
    # Try to initialize recordings API if needed
    if not initialize_recordings_api():
        raise HTTPException(status_code=503, detail="Recording API not initialized")
    
    try:
        success = recordings_api.delete_recording(recording_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Recording {recording_id} not found")
        
        return {"success": True, "message": f"Recording {recording_id} deleted"}
    except Exception as e:
        logger.error(f"Error deleting recording {recording_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{recording_id}")
async def get_recording_detail(recording_id: int):
    """Get detailed information about a specific recording."""
    global recordings_api, recordings_directory
    
    # Try to initialize recordings API if needed
    if not initialize_recordings_api():
        raise HTTPException(status_code=503, detail="Recording API not initialized")
    
    try:
        recording = recordings_api.get_recording_by_id(recording_id)
        if not recording:
            raise HTTPException(status_code=404, detail=f"Recording {recording_id} not found")
        
        # Transform file paths to URLs
        if recording.get('file_path'):
            try:
                # Ensure both paths are absolute before computing relative path
                abs_file_path = os.path.abspath(os.path.expanduser(recording['file_path']))
                abs_recordings_dir = os.path.abspath(os.path.expanduser(recordings_directory))
                rel_path = os.path.relpath(abs_file_path, abs_recordings_dir)
                recording['file_url'] = f"/recordings/{rel_path}"
                logger.info(f"Created file URL: {recording['file_url']} from {recording['file_path']}")
            except Exception as e:
                logger.error(f"Error creating file URL: {e}")
                recording['file_url'] = None
        
        if recording.get('thumbnail_path'):
            try:
                # Ensure both paths are absolute before computing relative path
                abs_thumb_path = os.path.abspath(os.path.expanduser(recording['thumbnail_path']))
                abs_recordings_dir = os.path.abspath(os.path.expanduser(recordings_directory))
                rel_path = os.path.relpath(abs_thumb_path, abs_recordings_dir)
                recording['thumbnail_url'] = f"/recordings/{rel_path}"
                logger.info(f"Created thumbnail URL: {recording['thumbnail_url']} from {recording['thumbnail_path']}")
            except Exception as e:
                logger.error(f"Error creating thumbnail URL: {e}")
                recording['thumbnail_url'] = None
        
        return recording
    except Exception as e:
        logger.error(f"Error retrieving recording {recording_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
