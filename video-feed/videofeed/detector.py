"""Object detection and video processing for video-feed."""

import cv2
import numpy as np
import time
import os
from typing import Dict, List, Tuple, Optional, Union, Any
from pathlib import Path
import threading
import queue
from ultralytics import YOLO
import logging
from concurrent.futures import ThreadPoolExecutor
import uuid

from videofeed.recorder import RecordingManager

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('video-detector')

class RTSPObjectDetector:
    """Process RTSP stream with YOLO object detection."""
    
    def __init__(
        self,
        source_url: str,
        model_path: str = "yolov8n.pt",
        confidence: float = 0.5,
        buffer_size: int = 10,
        reconnect_interval: int = 5,
        resolution: Tuple[int, int] = (640, 480),
        recording_manager: Optional[RecordingManager] = None
    ):
        """Initialize the RTSP object detector.
        
        Args:
            source_url: RTSP source URL with credentials
            model_path: Path to YOLO model or model name
            confidence: Detection confidence threshold
            buffer_size: Frame buffer size
            reconnect_interval: Seconds between reconnection attempts
            resolution: Output resolution (width, height)
        """
        self.source_url = source_url
        self.model_path = model_path
        self.confidence = confidence
        self.buffer_size = buffer_size
        self.reconnect_interval = reconnect_interval
        self.resolution = resolution
        
        # Initialize components
        self.model = None
        self.cap = None
        self.frame_buffer = queue.Queue(maxsize=buffer_size)
        self.latest_frame = None
        self.running = False
        self.processing_thread = None
        self.capture_thread = None
        
        # Stats
        self.fps = 0
        self.frame_count = 0
        self.last_fps_update = 0
        self.detections = []
        
        # Recording
        self.recording_manager = recording_manager
        self.detector_id = str(uuid.uuid4())  # Unique ID for this detector instance
        
    def load_model(self) -> None:
        """Load YOLO model."""
        try:
            logger.info(f"Loading YOLO model: {self.model_path}")
            self.model = YOLO(self.model_path)
            logger.info("Model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
            
    def start(self) -> None:
        """Start capture and processing threads."""
        if self.running:
            return
            
        if self.model is None:
            self.load_model()
            
        self.running = True
        self.capture_thread = threading.Thread(target=self._capture_loop)
        self.processing_thread = threading.Thread(target=self._processing_loop)
        
        self.capture_thread.daemon = True
        self.processing_thread.daemon = True
        
        self.capture_thread.start()
        self.processing_thread.start()
        
        # Register with recording manager if available
        if self.recording_manager:
            stream_name = self.get_name()
            self.recording_manager.register_stream(self.detector_id, stream_name)
            
        logger.info("Detector started")
        
    def stop(self) -> None:
        """Stop all processing threads."""
        logger.info("Stopping detector thread operations...")
        
        # Signal threads to stop
        self.running = False
        
        # Unregister from recording manager if available
        if self.recording_manager:
            self.recording_manager.unregister_stream(self.detector_id)
        
        # Clear the buffer to unblock any waiting threads
        try:
            while not self.frame_buffer.empty():
                self.frame_buffer.get_nowait()
        except Exception:
            pass
            
        # Wait for threads to terminate
        if self.capture_thread and self.capture_thread.is_alive():
            logger.info("Waiting for capture thread to terminate...")
            self.capture_thread.join(timeout=2.0)
            if self.capture_thread.is_alive():
                logger.warning("Capture thread did not terminate gracefully")
            
        if self.processing_thread and self.processing_thread.is_alive():
            logger.info("Waiting for processing thread to terminate...")
            self.processing_thread.join(timeout=2.0)
            if self.processing_thread.is_alive():
                logger.warning("Processing thread did not terminate gracefully")
            
        # Release the capture device
        if self.cap:
            logger.info("Releasing capture device...")
            self.cap.release()
            self.cap = None
            
        # Reset state
        self.latest_frame = None
        self.detections = []
        self.fps = 0
        self.frame_count = 0
            
        logger.info("Detector stopped successfully")
        
    def _connect_to_stream(self) -> bool:
        """Connect to RTSP/RTSPS stream."""
        if self.cap is not None:
            self.cap.release()
            
        # Mask credentials in log message for security
        log_url = self._mask_credentials(self.source_url)
        logger.info(f"Connecting to stream: {log_url}")
        
        # Set transport protocol options for RTSP/RTSPS
        # Use TCP as transport to avoid packet loss
        os_path = f"{self.source_url}"
        
        # Configure OpenCV to use FFMPEG backend with specific settings for RTSPS
        self.cap = cv2.VideoCapture(os_path, cv2.CAP_FFMPEG)
        
        # Additional options for RTSP/RTSPS streams
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)  # Smaller buffer for lower latency
        
        # Check if connection was successful
        if not self.cap.isOpened():
            logger.error("Failed to connect to stream. Check URL and credentials.")
            return False
        
        logger.info("Connected to stream successfully")
        return True
        
    def _mask_credentials(self, url: str) -> str:
        """Mask credentials in URL for logging purposes."""
        import re
        # Check if the URL contains credentials (username:password@)
        if '@' in url:
            # Replace credentials with '***:***'
            masked_url = re.sub(r'://([^:]+):([^@]+)@', r'://***:***@', url)
            return masked_url
        return url
        
    def _capture_loop(self) -> None:
        """Main capture loop to read frames from RTSP."""
        while self.running:
            if self.cap is None or not self.cap.isOpened():
                if not self._connect_to_stream():
                    logger.info(f"Reconnecting in {self.reconnect_interval} seconds...")
                    time.sleep(self.reconnect_interval)
                    continue
            
            ret, frame = self.cap.read()
            if not ret:
                logger.warning("Failed to read frame, reconnecting...")
                time.sleep(1)
                self._connect_to_stream()
                continue
                
            # Resize frame if needed
            if self.resolution:
                frame = cv2.resize(frame, self.resolution)
                
            # Update FPS counter
            current_time = time.time()
            if current_time - self.last_fps_update >= 1.0:
                self.fps = self.frame_count
                self.frame_count = 0
                self.last_fps_update = current_time
            self.frame_count += 1
            
            # Send frame to recording manager buffer if available
            if self.recording_manager and frame is not None:
                self.recording_manager.add_frame(self.detector_id, frame.copy())
            
            # Add to buffer, drop frames if buffer is full
            try:
                self.frame_buffer.put(frame, block=False)
            except queue.Full:
                # Skip this frame if buffer is full
                pass
                
    def _processing_loop(self) -> None:
        """Process frames with object detection."""
        while self.running:
            try:
                # Get frame from buffer
                frame = self.frame_buffer.get(timeout=1.0)
                
                # Run YOLO detection
                results = self.model(frame, conf=self.confidence, verbose=False)
                
                # Process results
                processed_frame, detections = self._process_results(frame, results)
                
                # Store latest processed frame and detections
                self.latest_frame = processed_frame
                self.detections = detections
                
            except queue.Empty:
                # No frames in the buffer
                continue
            except Exception as e:
                logger.error(f"Error processing frame: {e}")
                time.sleep(0.1)
                
    def _process_results(self, frame: np.ndarray, results):
        """Process YOLO results and draw on frame."""
        detections = []
        max_conf = 0
        
        # Extract the first result (only one image processed at a time)
        result = results[0]
        
        # Draw boxes and extract detection data
        boxes = result.boxes
        for box in boxes:
            # Get box coordinates
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            
            # Get confidence and class
            conf = float(box.conf[0])
            cls = int(box.cls[0])
            name = result.names[cls]
            
            # Track highest confidence
            if conf > max_conf:
                max_conf = conf
            
            # Save detection info
            detection = {
                "class": name,
                "confidence": conf,
                "bbox": [x1, y1, x2, y2]
            }
            detections.append(detection)
            
            # Draw on frame
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Draw label
            label = f"{name} {conf:.2f}"
            (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(frame, (x1, y1 - 20), (x1 + w, y1), (0, 255, 0), -1)
            cv2.putText(frame, label, (x1, y1 - 5), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        
        # Draw FPS
        fps_text = f"FPS: {self.fps}"
        cv2.putText(frame, fps_text, (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
        
        # Trigger recording if we have detections and a recording manager
        if detections and self.recording_manager and max_conf > 0:
            self.recording_manager.handle_detection(
                self.detector_id, 
                detections, 
                max_conf, 
                frame.copy()
            )
        
        return frame, detections
        
    def get_frame_jpeg(self) -> bytes:
        """Get the latest processed frame as JPEG bytes."""
        if self.latest_frame is None:
            # Return a blank frame
            blank = np.zeros((self.resolution[1], self.resolution[0], 3), dtype=np.uint8)
            _, buffer = cv2.imencode('.jpg', blank)
            return buffer.tobytes()
            
        _, buffer = cv2.imencode('.jpg', self.latest_frame)
        return buffer.tobytes()
        
    def get_status(self) -> Dict:
        """Get detector status information."""
        return {
            "running": self.running,
            "fps": self.fps,
            "source": self._mask_credentials(self.source_url),
            "model": self.model_path,
            "resolution": self.resolution,
            "detections": len(self.detections),
            "buffer_usage": self.frame_buffer.qsize() / self.buffer_size
        }
        
    def get_name(self) -> str:
        """Get a human-friendly name for this detector."""
        if '@' in self.source_url:
            # Extract path from URL (after credentials and host)
            path = self.source_url.split('@')[-1].split('/')[-1]
            return path
        return "camera"
        

class DetectorManager:
    """Manage multiple object detectors."""
    
    def __init__(self, recording_manager: Optional[RecordingManager] = None):
        """Initialize the detector manager."""
        self.detectors = {}
        self.default_detector_id = None
        self.model_cache = {}
        self.recording_manager = recording_manager
        # Use a thread pool for sharing across detectors
        self.executor = ThreadPoolExecutor(max_workers=3)
        self._lock = threading.RLock()
        
    def add_detector(self, 
                    source_url: str, 
                    model_path: str = "yolov8n.pt",
                    confidence: float = 0.5, 
                    resolution: Tuple[int, int] = (640, 480),
                    enable_recording: bool = True) -> str:
        """Add a new detector for a stream.
        
        Args:
            source_url: RTSP source URL with credentials
            model_path: Path to YOLO model or model name
            confidence: Detection confidence threshold
            resolution: Output resolution (width, height)
        
        Returns:
            Detector ID (UUID)
        """
        detector_id = str(uuid.uuid4())
        
        # Reuse model if already loaded
        if model_path not in self.model_cache:
            logger.info(f"Loading model {model_path} for the first time")
            model = YOLO(model_path)
            self.model_cache[model_path] = model
        
        with self._lock:
            detector = RTSPObjectDetector(
                source_url=source_url,
                model_path=model_path,
                confidence=confidence,
                resolution=resolution,
                recording_manager=self.recording_manager if enable_recording else None
            )
            
            # Set model directly if already loaded
            if model_path in self.model_cache:
                detector.model = self.model_cache[model_path]
            else:
                detector.load_model()
            
            detector.start()
            self.detectors[detector_id] = detector
            
            # Set as default if it's the first one
            if self.default_detector_id is None:
                self.default_detector_id = detector_id
                
        logger.info(f"Added detector {detector_id} for stream {detector.get_name()}")
        return detector_id
    
    def remove_detector(self, detector_id: str) -> bool:
        """Remove a detector by ID.
        
        Args:
            detector_id: ID of the detector to remove
        
        Returns:
            True if detector was removed, False if not found
        """
        with self._lock:
            if detector_id not in self.detectors:
                return False
                
            detector = self.detectors[detector_id]
            detector.stop()
            del self.detectors[detector_id]
            
            # Update default if needed
            if detector_id == self.default_detector_id:
                if self.detectors:
                    self.default_detector_id = next(iter(self.detectors.keys()))
                else:
                    self.default_detector_id = None
                    
        logger.info(f"Removed detector {detector_id}")
        return True
    
    def get_detector(self, detector_id: Optional[str] = None) -> Optional[RTSPObjectDetector]:
        """Get a detector by ID or the default detector.
        
        Args:
            detector_id: ID of the detector to get, or None for default
        
        Returns:
            The detector or None if not found
        """
        with self._lock:
            if detector_id is None:
                if self.default_detector_id is None:
                    return None
                return self.detectors.get(self.default_detector_id)
            return self.detectors.get(detector_id)
    
    def get_all_detectors(self) -> Dict[str, RTSPObjectDetector]:
        """Get all detectors.
        
        Returns:
            Dictionary of detector_id -> detector
        """
        with self._lock:
            return dict(self.detectors)
    
    def get_detector_status(self, detector_id: Optional[str] = None) -> Dict:
        """Get status information for a detector or all detectors."""
        if detector_id is not None:
            detector = self.get_detector(detector_id)
            if detector is None:
                return {"error": "Detector not found"}
            return detector.get_status()
        
        # Return status of all detectors
        result = {}
        for det_id, detector in self.get_all_detectors().items():
            result[det_id] = {
                "name": detector.get_name(),
                **detector.get_status()
            }
        return result
        
    def get_frame_jpeg(self, detector_id: Optional[str] = None) -> bytes:
        """Get the latest processed frame from a detector."""
        detector = self.get_detector(detector_id)
        if detector is None:
            # Return a blank frame with "No active detector"
            blank = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(blank, "No active detector", (100, 240),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            _, buffer = cv2.imencode('.jpg', blank)
            return buffer.tobytes()
        
        return detector.get_frame_jpeg()
    
    def stop_all(self):
        """Stop all detectors."""
        logger.info(f"Stopping {len(self.detectors)} detectors")
        with self._lock:
            for detector_id, detector in list(self.detectors.items()):
                logger.info(f"Stopping detector {detector_id}")
                try:
                    detector.stop()
                except Exception as e:
                    logger.error(f"Error stopping detector {detector_id}: {e}")
            self.detectors.clear()
            self.default_detector_id = None
        
        # Shutdown thread pool
        self.executor.shutdown(wait=True)
        
        # Stop recording manager if available
        if self.recording_manager:
            self.recording_manager.stop()
            
        logger.info("All detectors stopped")
    
    def __del__(self):
        """Clean up resources."""
        self.stop_all()
