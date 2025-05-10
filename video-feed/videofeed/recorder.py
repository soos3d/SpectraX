"""Video recording and database management for video-feed."""

import os
import time
import json
import logging
import sqlite3
import threading
import queue
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('video-recorder')

class RecordingManager:
    """Manage video recordings and database operations."""
    
    def __init__(
        self,
        db_path: Optional[str] = None,
        recordings_dir: Optional[str] = None,
        pre_detection_buffer: int = 5,      # Seconds to keep before detection
        post_detection_buffer: int = 5,     # Seconds to keep after last detection
        min_confidence: float = 0.5,        # Minimum confidence to trigger recording
        fps: int = 40,                      # Target FPS for recordings
        codec: str = 'mp4v',                # Video codec (mp4v is widely compatible)
        max_storage_gb: float = 10.0        # Max storage in GB before cleanup
    ):
        """Initialize the recording manager.
        
        Args:
            db_path: Path to SQLite database file
            recordings_dir: Directory to store recordings
            clip_duration: Seconds to include before/after detection
            min_confidence: Minimum confidence to trigger recording
            fps: Target FPS for recordings
            codec: Video codec to use
            max_storage_gb: Maximum storage space in gigabytes
        """
        # Set up paths
        self.recordings_dir = Path(recordings_dir or os.path.expanduser("~/video-feed-recordings"))
        self.recordings_dir.mkdir(exist_ok=True, parents=True)
        
        self.db_path = db_path or str(self.recordings_dir / "recordings.db")
        
        # Recording settings
        self.pre_detection_buffer = pre_detection_buffer
        self.post_detection_buffer = post_detection_buffer
        self.min_confidence = min_confidence
        self.fps = fps
        self.fourcc = cv2.VideoWriter_fourcc(*codec)
        self.max_storage_bytes = max_storage_gb * 1024 * 1024 * 1024  # Convert GB to bytes
        
        # Runtime state
        self.frame_buffers = {}  # Dict of stream_id -> deque of (timestamp, frame) tuples
        self.active_recordings = {}  # Dict of recording_id -> recording_info
        self.db_conn = None
        self._lock = threading.RLock()
        self.running = False
        self.cleanup_thread = None
        
        # Initialize database
        self._init_database()
        
    def _init_database(self):
        """Initialize the SQLite database."""
        try:
            self.db_conn = sqlite3.connect(self.db_path, check_same_thread=False)
            cursor = self.db_conn.cursor()
            
            # Create recordings table if it doesn't exist
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS recordings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                stream_id TEXT NOT NULL,
                stream_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                duration REAL NOT NULL,
                objects_detected TEXT NOT NULL,
                thumbnail_path TEXT,
                confidence REAL NOT NULL,
                retained BOOLEAN DEFAULT 1
            )
            ''')
            
            # Create indexes for faster queries
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_recordings_timestamp ON recordings(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_recordings_stream_id ON recordings(stream_id)')
            
            self.db_conn.commit()
            logger.info(f"Database initialized: {self.db_path}")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
            
    def start(self):
        """Start the recording manager threads."""
        if self.running:
            return
            
        self.running = True
        self.cleanup_thread = threading.Thread(target=self._storage_cleanup_loop, daemon=True)
        self.cleanup_thread.start()
        logger.info("Recording manager started")
        
    def stop(self):
        """Stop all recording manager threads."""
        logger.info("Stopping recording manager...")
        self.running = False
        
        if self.cleanup_thread and self.cleanup_thread.is_alive():
            self.cleanup_thread.join(timeout=2.0)
            
        # Finalize any active recordings
        with self._lock:
            for recording_id, info in list(self.active_recordings.items()):
                self._finalize_recording(recording_id)
                
        # Close database connection
        if self.db_conn:
            self.db_conn.close()
            self.db_conn = None
            
        logger.info("Recording manager stopped")
            
    def register_stream(self, stream_id: str, stream_name: str):
        """Register a stream for recording.
        
        Args:
            stream_id: Unique identifier for the stream
            stream_name: Human-readable name for the stream
            buffer_seconds: Seconds of video to keep in buffer
        """
        from collections import deque
        
        with self._lock:
            # Calculate buffer size based on FPS and pre-detection buffer duration
            buffer_size = self.pre_detection_buffer * self.fps
            self.frame_buffers[stream_id] = {
                'buffer': deque(maxlen=buffer_size),
                'name': stream_name,
                'last_recording': 0,
                'recording_in_progress': False,
                'last_detection_time': 0,
                'cooldown_timer': None,
                'timer_lock': threading.Lock()
            }
        logger.info(f"Registered stream {stream_id} ({stream_name}) for recording")
            
    def unregister_stream(self, stream_id: str):
        """Unregister a stream from recording.
        
        Args:
            stream_id: Stream ID to unregister
        """
        with self._lock:
            if stream_id in self.frame_buffers:
                del self.frame_buffers[stream_id]
        logger.info(f"Unregistered stream {stream_id} from recording")
            
    def add_frame(self, stream_id: str, frame: np.ndarray, timestamp: Optional[float] = None):
        """Add a frame to the stream's buffer.
        
        Args:
            stream_id: Stream ID
            frame: Video frame (numpy array)
            timestamp: Frame timestamp (defaults to current time)
        """
        if timestamp is None:
            timestamp = time.time()
            
        with self._lock:
            if stream_id in self.frame_buffers:
                # Make a copy of the frame to avoid reference issues
                self.frame_buffers[stream_id]['buffer'].append((timestamp, frame.copy()))
                
                # If we're currently recording for this stream, add the frame to the recording
                if self.frame_buffers[stream_id]['recording_in_progress']:
                    for recording_id, recording in list(self.active_recordings.items()):
                        if recording['stream_id'] == stream_id:
                            try:
                                recording['writer'].write(frame.copy())
                                recording['frame_count'] += 1
                                
                                # Update last frame time
                                recording['last_frame_time'] = timestamp
                            except Exception as e:
                                logger.error(f"Error writing frame to recording {recording_id}: {e}")
                
    def handle_detection(self, stream_id: str, objects: List[Dict], confidence: float, frame: np.ndarray):
        """Handle an object detection event and possibly start or continue recording.
        
        This method is called whenever objects are detected in a frame. It will:
        1. Start a new recording if one isn't already in progress
        2. Update the last detection time if recording is already in progress
        3. Include buffer frames from before the detection
        4. Continue recording until no detections occur for post_detection_buffer seconds
        
        Args:
            stream_id: Stream ID where detection occurred
            objects: List of detected objects with class, confidence, etc.
            confidence: Highest confidence score
            frame: Current video frame
        """
        """Handle an object detection event and possibly start recording.
        
        Args:
            stream_id: Stream ID where detection occurred
            objects: List of detected objects with class, confidence, etc.
            confidence: Highest confidence score
            frame: Current video frame
        """
        # Skip if confidence is too low
        if confidence < self.min_confidence:
            return
            
        current_time = time.time()
            
        with self._lock:
            # Check if stream is registered
            if stream_id not in self.frame_buffers:
                return
                
            stream_info = self.frame_buffers[stream_id]
            
            # Update the last detection time
            stream_info['last_detection_time'] = current_time
            
            # If we're already recording, just update the detection time and cancel any cooldown timer
            if stream_info['recording_in_progress']:
                # Find the active recording for this stream
                for recording_id, recording in list(self.active_recordings.items()):
                    if recording['stream_id'] == stream_id:
                        # Update the detection time in the recording
                        recording['last_detection_time'] = current_time
                        
                        # Cancel any cooldown timer
                        if stream_info['cooldown_timer'] is not None:
                            stream_info['cooldown_timer'].cancel()
                            stream_info['cooldown_timer'] = None
                            #logger.info(f"Canceled cooldown timer for stream {stream_id} due to new detection")
                            
                        # Start a new cooldown timer
                        self._start_cooldown_timer(stream_id, recording_id)
                       # logger.info(f"Reset cooldown timer for ongoing recording due to new detection")
                        break
                        
                return
            
            # Avoid starting too many recordings (minimum 5 seconds between recordings)
            if current_time - stream_info['last_recording'] < 5:
                return
                
            # Create a unique identifier for this recording
            recording_id = f"{stream_id}_{int(current_time * 1000)}"
            
            # Start a new recording
            detection_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            video_filename = f"{stream_info['name']}_{detection_timestamp}.mp4"
            video_path = str(self.recordings_dir / video_filename)
            
            # Save thumbnail
            thumbnail_filename = f"{stream_info['name']}_{detection_timestamp}_thumb.jpg"
            thumbnail_path = str(self.recordings_dir / thumbnail_filename)
            self._save_thumbnail(frame, thumbnail_path)
            
            # Get frame dimensions
            height, width = frame.shape[:2]
            
            # Create a video writer
            writer = cv2.VideoWriter(
                video_path, 
                self.fourcc, 
                self.fps, 
                (width, height)
            )
            
            # Write buffered frames (pre-detection footage)
            for ts, buffered_frame in list(stream_info['buffer']):
                if buffered_frame is not None:
                    writer.write(buffered_frame)
            
            # Update stream info
            stream_info['recording_in_progress'] = True
            stream_info['last_recording'] = current_time
            
            # Add current detection frame
            writer.write(frame)
            
            # Store recording information
            self.active_recordings[recording_id] = {
                'stream_id': stream_id,
                'stream_name': stream_info['name'],
                'start_time': current_time,
                'last_detection_time': current_time,
                'last_frame_time': current_time,
                'writer': writer,
                'file_path': video_path,
                'thumbnail_path': thumbnail_path,
                'frame_count': len(stream_info['buffer']),
                'objects': objects,
                'confidence': confidence
            }
            
            # We don't set a timer to finalize immediately - recording will continue
            # until no more detections occur for post_detection_buffer seconds
            
            # Log the event
            class_names = [obj['class'] for obj in objects]
            logger.info(f"Started recording {recording_id} due to detection: {class_names}")
            
            # Start a cooldown timer that will finalize the recording if no more detections occur
            self._start_cooldown_timer(stream_id, recording_id)
            
    def _check_recording_status(self, stream_id: str, recording_id: str):
        """Check if recording should continue or be finalized based on detection timing.
        
        Args:
            stream_id: Stream ID to check
            recording_id: Recording ID to check
        """
        logger.info(f"Checking recording status for {recording_id} after cooldown period")
        with self._lock:
            if stream_id not in self.frame_buffers or recording_id not in self.active_recordings:
                logger.info(f"Stream or recording no longer exists: {stream_id}/{recording_id}")
                return
                
            stream_info = self.frame_buffers[stream_id]
            recording = self.active_recordings[recording_id]
            
            current_time = time.time()
            time_since_last_detection = current_time - recording['last_detection_time']
            
            logger.info(f"Time since last detection: {time_since_last_detection:.2f}s (buffer: {self.post_detection_buffer}s)")
            
            # If it's been long enough since the last detection, finalize the recording
            if time_since_last_detection >= self.post_detection_buffer:
                logger.info(f"Finalizing recording {recording_id} after cooldown period")
                # Clear the cooldown timer reference to prevent memory leaks
                stream_info['cooldown_timer'] = None
                # Finalize the recording
                self._finalize_recording(recording_id)
            else:
                # We still have recent detections, so reset the timer
                logger.info(f"Recent detection found, resetting cooldown timer for {recording_id}")
                self._start_cooldown_timer(stream_id, recording_id)
                
    def _start_cooldown_timer(self, stream_id: str, recording_id: str):
        """Start a cooldown timer to finalize recording if no more detections occur.
        
        Args:
            stream_id: Stream ID
            recording_id: Recording ID
        """
        with self._lock:
            if stream_id not in self.frame_buffers:
                return
                
            # Cancel any existing timer
            stream_info = self.frame_buffers[stream_id]
            if stream_info['cooldown_timer'] is not None:
                stream_info['cooldown_timer'].cancel()
            
            # Create a new timer
            timer = threading.Timer(
                self.post_detection_buffer,
                self._check_recording_status,
                args=[stream_id, recording_id]
            )
            timer.daemon = True
            timer.start()
            
            # Store the timer
            stream_info['cooldown_timer'] = timer
            #logger.info(f"Started cooldown timer for recording {recording_id} ({self.post_detection_buffer}s)")
            
    def _finalize_recording(self, recording_id: str):
        """Finalize a recording and save to database.
        
        Args:
            recording_id: ID of the recording to finalize
        """
        logger.info(f"Finalizing recording {recording_id}")
        with self._lock:
            if recording_id not in self.active_recordings:
                return
                
            recording = self.active_recordings[recording_id]
            stream_id = recording['stream_id']
            
            # Release the video writer
            writer = recording['writer']
            writer.release()
            
            # Calculate duration
            end_time = time.time()
            duration = end_time - recording['start_time']
            
            # Reset stream recording flag
            if stream_id in self.frame_buffers:
                self.frame_buffers[stream_id]['recording_in_progress'] = False
                # Clear any cooldown timer
                if self.frame_buffers[stream_id]['cooldown_timer'] is not None:
                    self.frame_buffers[stream_id]['cooldown_timer'].cancel()
                    self.frame_buffers[stream_id]['cooldown_timer'] = None
            
            # Save recording to database
            try:
                cursor = self.db_conn.cursor()
                cursor.execute('''
                INSERT INTO recordings 
                (timestamp, stream_id, stream_name, file_path, duration, 
                objects_detected, thumbnail_path, confidence, retained)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
                ''', (
                    datetime.fromtimestamp(recording['start_time']).isoformat(),
                    stream_id,
                    recording['stream_name'],
                    recording['file_path'],
                    duration,
                    json.dumps(recording['objects']),
                    recording['thumbnail_path'],
                    recording['confidence']
                ))
                self.db_conn.commit()
                
                # Remove from active recordings
                del self.active_recordings[recording_id]
                
                logger.info(f"Finalized recording {recording_id} (duration: {duration:.2f}s, frames: {recording['frame_count']})")
            except Exception as e:
                logger.error(f"Failed to save recording {recording_id} to database: {e}")
        
    # This method is no longer needed
    # def _continue_recording(self, recording_id: str):
        """Finalize a recording and save to database.
        
        Args:
            recording_id: ID of the recording to finalize
        """
        with self._lock:
            if recording_id not in self.active_recordings:
                return
                
            recording = self.active_recordings[recording_id]
            stream_id = recording['stream_id']
            
            # Release the video writer
            writer = recording['writer']
            writer.release()
            
            # Calculate duration
            end_time = time.time()
            duration = end_time - recording['start_time']
            
            # Reset stream recording flag
            if stream_id in self.frame_buffers:
                self.frame_buffers[stream_id]['recording_in_progress'] = False
            
            # Save recording to database
            try:
                cursor = self.db_conn.cursor()
                cursor.execute('''
                INSERT INTO recordings 
                (timestamp, stream_id, stream_name, file_path, duration, 
                objects_detected, thumbnail_path, confidence, retained)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
                ''', (
                    datetime.fromtimestamp(recording['start_time']).isoformat(),
                    stream_id,
                    recording['stream_name'],
                    recording['file_path'],
                    duration,
                    json.dumps(recording['objects']),
                    recording['thumbnail_path'],
                    recording['confidence']
                ))
                self.db_conn.commit()
                
                # Remove from active recordings
                del self.active_recordings[recording_id]
                
                logger.info(f"Finalized recording {recording_id} (duration: {duration:.2f}s, frames: {recording['frame_count']})")
            except Exception as e:
                logger.error(f"Failed to save recording {recording_id} to database: {e}")
                
    def _save_thumbnail(self, frame: np.ndarray, path: str):
        """Save a thumbnail image from a frame.
        
        Args:
            frame: Frame to save as thumbnail
            path: Path to save thumbnail to
        """
        try:
            cv2.imwrite(path, frame)
        except Exception as e:
            logger.error(f"Error saving thumbnail: {e}")
                
    def _storage_cleanup_loop(self):
        """Background thread to periodically check storage usage and cleanup if needed."""
        while self.running:
            try:
                # Run cleanup check every hour
                time.sleep(3600)
                
                if not self.running:
                    break
                    
                total_size = sum(f.stat().st_size for f in self.recordings_dir.glob('**/*') if f.is_file())
                
                # If we're using too much space, delete oldest recordings
                if total_size > self.max_storage_bytes:
                    logger.info(f"Storage usage ({total_size/1e9:.2f}GB) exceeds limit ({self.max_storage_bytes/1e9:.2f}GB), cleaning up...")
                    self._cleanup_old_recordings()
            except Exception as e:
                logger.error(f"Error in storage cleanup loop: {e}")
                
    def _cleanup_old_recordings(self):
        """Delete oldest recordings to free up space."""
        try:
            cursor = self.db_conn.cursor()
            
            # Get oldest recordings first
            cursor.execute('''
            SELECT id, file_path, thumbnail_path FROM recordings
            WHERE retained = 1
            ORDER BY timestamp ASC
            LIMIT 20
            ''')
            
            for row in cursor.fetchall():
                rec_id, file_path, thumbnail_path = row
                
                # Delete the files
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    if thumbnail_path and os.path.exists(thumbnail_path):
                        os.remove(thumbnail_path)
                        
                    # Update database
                    cursor.execute('UPDATE recordings SET retained = 0 WHERE id = ?', (rec_id,))
                    self.db_conn.commit()
                    logger.info(f"Deleted old recording: {file_path}")
                except Exception as e:
                    logger.error(f"Error deleting recording {rec_id}: {e}")
                    
                # Check if we've freed up enough space
                total_size = sum(f.stat().st_size for f in self.recordings_dir.glob('**/*') if f.is_file())
                if total_size < self.max_storage_bytes * 0.8:  # Stop when we're below 80% of max
                    break
        except Exception as e:
            logger.error(f"Error during recordings cleanup: {e}")
            
    def get_recordings(self, 
                       stream_id: Optional[str] = None, 
                       limit: int = 100, 
                       offset: int = 0,
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None) -> List[Dict]:
        """Get recordings from the database.
        
        Args:
            stream_id: Filter by stream ID (optional)
            limit: Maximum number of recordings to return
            offset: Offset for pagination
            start_date: Start date filter (ISO format)
            end_date: End date filter (ISO format)
            
        Returns:
            List of recording information dictionaries
        """
        query = 'SELECT * FROM recordings WHERE retained = 1'
        params = []
        
        if stream_id:
            query += ' AND stream_id = ?'
            params.append(stream_id)
            
        if start_date:
            query += ' AND timestamp >= ?'
            params.append(start_date)
            
        if end_date:
            query += ' AND timestamp <= ?'
            params.append(end_date)
            
        query += ' ORDER BY timestamp DESC LIMIT ? OFFSET ?'
        params.extend([limit, offset])
        
        try:
            cursor = self.db_conn.cursor()
            cursor.execute(query, params)
            
            columns = [col[0] for col in cursor.description]
            recordings = []
            
            for row in cursor.fetchall():
                recording = dict(zip(columns, row))
                
                # Parse JSON fields
                recording['objects_detected'] = json.loads(recording['objects_detected'])
                
                recordings.append(recording)
                
            return recordings
        except Exception as e:
            logger.error(f"Error retrieving recordings: {e}")
            return []
            
    def delete_recording(self, recording_id: int) -> bool:
        """Delete a recording and its files.
        
        Args:
            recording_id: ID of the recording to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            cursor = self.db_conn.cursor()
            cursor.execute('SELECT file_path, thumbnail_path FROM recordings WHERE id = ?', (recording_id,))
            result = cursor.fetchone()
            
            if not result:
                return False
                
            file_path, thumbnail_path = result
            
            # Delete the files
            if os.path.exists(file_path):
                os.remove(file_path)
            if thumbnail_path and os.path.exists(thumbnail_path):
                os.remove(thumbnail_path)
                
            # Delete from database
            cursor.execute('DELETE FROM recordings WHERE id = ?', (recording_id,))
            self.db_conn.commit()
            
            logger.info(f"Deleted recording {recording_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting recording {recording_id}: {e}")
            return False
