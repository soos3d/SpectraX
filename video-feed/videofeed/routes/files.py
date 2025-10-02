"""File serving routes with security checks."""

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(prefix="/recordings", tags=["files"])

logger = logging.getLogger(__name__)

# Global recordings directory reference (set by visualizer)
recordings_directory = None


def set_recordings_directory(directory: str):
    """Set the recordings directory path."""
    global recordings_directory
    recordings_directory = directory


@router.get("/{file_path:path}")
async def serve_recording_file(file_path: str):
    """Serve a recording file (video or thumbnail) with security checks."""
    global recordings_directory
    
    if not recordings_directory:
        raise HTTPException(status_code=404, detail="Recording directory not configured")
    
    try:
        # Convert to Path objects and resolve to absolute paths
        recordings_path = Path(recordings_directory).resolve()
        requested_path = (recordings_path / file_path).resolve()
        
        # ✅ CRITICAL: Ensure requested path is within recordings directory
        # This prevents path traversal attacks like "../../../etc/passwd"
        if not requested_path.is_relative_to(recordings_path):
            logger.warning(f"Path traversal attempt blocked: {file_path}")
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Check if file exists
        if not requested_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
        
        # Check if it's a file (not a directory)
        if not requested_path.is_file():
            raise HTTPException(status_code=403, detail="Not a file")
        
        # ✅ Validate file extension (only allow expected types)
        allowed_extensions = {'.mp4', '.jpg', '.jpeg', '.png', '.webm', '.enc'}
        if requested_path.suffix.lower() not in allowed_extensions:
            logger.warning(f"Unauthorized file type access attempt: {requested_path.suffix}")
            raise HTTPException(status_code=403, detail="File type not allowed")
        
        # Log access for audit
        logger.info(f"File access: {file_path}")
        
        return FileResponse(requested_path)
        
    except ValueError as e:
        # is_relative_to can raise ValueError
        logger.error(f"Path validation error: {e}")
        raise HTTPException(status_code=403, detail="Invalid path")
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error serving file {file_path}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
