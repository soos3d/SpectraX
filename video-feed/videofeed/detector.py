"""Object detection and video processing for video-feed."""

import cv2
import numpy as np
import time
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import threading
import queue
from ultralytics import YOLO
import logging

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
        resolution: Tuple[int, int] = (640, 480)
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
        logger.info("Detector started")
        
    def stop(self) -> None:
        """Stop all processing threads."""
        self.running = False
        
        if self.capture_thread:
            self.capture_thread.join(timeout=1.0)
            
        if self.processing_thread:
            self.processing_thread.join(timeout=1.0)
            
        if self.cap:
            self.cap.release()
            
        logger.info("Detector stopped")
        
    def _connect_to_stream(self) -> bool:
        """Connect to RTSP stream."""
        if self.cap is not None:
            self.cap.release()
            
        logger.info(f"Connecting to stream: {self.source_url}")
        # Use TCP as transport to avoid packet loss
        os_path = f"{self.source_url}"
        self.cap = cv2.VideoCapture(os_path, cv2.CAP_FFMPEG)
        
        # Check if connection was successful
        if not self.cap.isOpened():
            logger.error("Failed to connect to stream")
            return False
        
        logger.info("Connected to stream successfully")
        return True
        
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
                
    def _process_results(self, frame: np.ndarray, results) -> Tuple[np.ndarray, List[Dict]]:
        """Process YOLO results and draw on frame."""
        detections = []
        processed_frame = frame.copy()
        
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
            
            # Add to detections list
            detections.append({
                "class": name,
                "confidence": conf,
                "bbox": [x1, y1, x2, y2]
            })
            
            # Draw on frame
            cv2.rectangle(processed_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Draw label
            label = f"{name} {conf:.2f}"
            (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(processed_frame, (x1, y1 - 20), (x1 + w, y1), (0, 255, 0), -1)
            cv2.putText(processed_frame, label, (x1, y1 - 5), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        
        # Draw FPS
        fps_text = f"FPS: {self.fps}"
        cv2.putText(processed_frame, fps_text, (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
        
        return processed_frame, detections
        
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
            "source": self.source_url,
            "model": self.model_path,
            "resolution": self.resolution,
            "detections": len(self.detections),
            "buffer_usage": self.frame_buffer.qsize() / self.buffer_size
        }
