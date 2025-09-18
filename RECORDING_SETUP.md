# Recording System Setup Guide

The QuickCast surveillance system now includes a robust recording feature that automatically saves video clips when objects are detected. Here's how to set it up and use it.

## How It Works

The recording system implements a **smart buffering approach**:

1. **Pre-Detection Buffer**: Continuously maintains a 10-second buffer of video frames
2. **Detection Trigger**: When an object is detected with sufficient confidence, recording starts
3. **Buffer Inclusion**: The recording includes the 10 seconds of footage *before* the detection
4. **Continuous Recording**: Keeps recording as long as objects are being detected
5. **Post-Detection Buffer**: Continues recording for 10 seconds after the last detection
6. **Automatic Finalization**: Saves the complete video clip with metadata to the database

## Configuration

### YAML Configuration (surveillance.yml)

```yaml
# Recording settings
recording:
  enabled: true
  min_confidence: 0.5  # Minimum confidence to trigger recording
  pre_buffer_seconds: 10  # Seconds to record before detection
  post_buffer_seconds: 10  # Seconds to record after last detection
  max_storage_gb: 10.0  # Maximum storage in GB before cleanup
  recordings_dir: "~/video-feed-recordings"  # Directory to store recordings
  # Only record when these objects are detected (empty list means record all objects)
  record_objects: ["person", "car", "dog", "cat"]
```

### Command Line Options

```bash
# Enable/disable recording
./surveillance.sh config --recording / --no-recording

# Customize recording parameters
python -m videofeed.surveillance start \
  --recording \
  --recording-confidence 0.6 \
  --pre-buffer 15 \
  --post-buffer 15 \
  --recordings-dir "/path/to/recordings" \
  --record-objects person car dog
```

## Features

### Object-Based Recording Filtering
- Selectively record only when specific objects are detected
- Configure a list of object classes to trigger recording (e.g., person, car, dog)
- Saves storage space by ignoring irrelevant detections
- Empty list means record all detected objects

### Automatic Frame Rate Detection
- The system automatically detects the actual frame rate of your video streams
- Adjusts buffer sizes dynamically to maintain exactly 10 seconds of footage
- Uses the correct frame rate when creating video files

### Smart Storage Management
- Automatically cleans up old recordings when storage limit is reached
- Configurable maximum storage limit (default: 10GB)
- Keeps newest recordings and removes oldest ones first

### Database Integration
- Stores recording metadata in SQLite database
- Tracks detected objects, confidence scores, timestamps
- Enables searching and filtering through the web interface

### Thumbnail Generation
- Creates thumbnail images for each recording
- Shows the frame where detection occurred
- Useful for quick preview in the web interface

## File Structure

```
~/video-feed-recordings/
├── recordings.db                    # SQLite database with metadata
├── camera-1_2024-01-15_14-30-25.mp4    # Video recording
├── camera-1_2024-01-15_14-30-25_thumb.jpg  # Thumbnail
├── camera-2_2024-01-15_15-45-10.mp4
└── camera-2_2024-01-15_15-45-10_thumb.jpg
```

## Testing the Recording System

Use the provided test script to verify recording functionality:

```bash
cd /Users/davide/Documents/coding/perimeter-ai
# Test without object filtering (record all objects)
python test_recording.py

# Test with object filtering (only record person and car)
python test_recording.py --filter

# Test both modes
python test_recording.py --all
```

This script will:
1. Create a test recording manager
2. Simulate video frames and object detections
3. Verify that recordings are created correctly
4. Test object filtering if specified
5. Show you where the test files are saved

## Web Interface

Access recordings through the web dashboard:
- Navigate to `http://your-ip:8080`
- Click on the "Recordings" tab
- Browse, filter, and manage your recordings
- View thumbnails and download video files

## API Endpoints

The system provides REST API endpoints for recordings:

- `GET /api/recordings` - List recordings with filtering options
- `GET /api/recordings/{id}` - Get specific recording details
- `DELETE /api/recordings/{id}` - Delete a recording
- `GET /api/alerts` - Get detection alerts
- `GET /api/stats/objects` - Object detection statistics
- `GET /recordings/{file_path}` - Serve recording files

## Troubleshooting

### No Recordings Created
1. Check that recording is enabled in configuration
2. Verify detection confidence is set appropriately
3. Ensure objects are being detected (check web interface)
4. If using object filtering, verify that the objects you want to record are in the `record_objects` list
5. Check logs for any error messages like "Skipping recording for objects..."
6. Try temporarily setting `record_objects: []` to record all objects for testing

### Storage Issues
1. Verify the recordings directory is writable
2. Check available disk space
3. Adjust `max_storage_gb` setting if needed

### Performance Issues
1. Lower the video resolution if needed
2. Reduce the buffer duration for less memory usage
3. Use a faster storage device (SSD) for better performance

### Video Playback Issues
1. Ensure you have proper video codecs installed
2. Try different video players (VLC is recommended)
3. Check that the video files aren't corrupted

## Advanced Configuration

### Custom Recording Directory
```bash
# Use a specific directory
python -m videofeed.surveillance config --recordings-dir "/mnt/storage/recordings"
```

### Object Filtering
```bash
# Only record when specific objects are detected
python -m videofeed.surveillance config --record-objects person car dog

# Record all objects (default)
python -m videofeed.surveillance config --record-objects
```

### Multiple Cameras
Each camera stream gets its own recording files, automatically named based on the stream path.

### Integration with External Systems
Use the REST API to integrate with home automation systems, security platforms, or custom applications.

## Performance Considerations

- **Memory Usage**: Each camera uses ~300MB RAM for 10-second buffer at 1080p
- **Storage**: Expect ~50-100MB per minute of recorded video (depends on resolution/quality)
- **CPU Usage**: Recording adds minimal CPU overhead beyond object detection
- **Network**: No additional network usage (recordings are local only)

## Security

- Recordings are stored locally on your system
- Database contains only metadata, not video content
- Web interface requires authentication to access recordings
- Files are created with appropriate permissions (600)

## Next Steps

1. Start your surveillance system: `./surveillance.sh config`
2. Connect your cameras using RTSP clients
3. Monitor the web interface for detections and recordings
4. Adjust confidence thresholds based on your needs
5. Set up storage cleanup policies for long-term operation

## Recording System API Specifications

Here are the API specifications for the recording system.

## Base URL
`http://localhost:8080` (or your server's address)

## Endpoints

### 1. List Recordings

**Endpoint:** `GET /api/recordings`

**Query Parameters:**
- `limit` (integer, optional): Maximum number of recordings to return (default: 20)
- `offset` (integer, optional): Number of recordings to skip (for pagination) (default: 0)
- `stream_id` (string, optional): Filter by stream ID
- `start_date` (string, optional): Filter by start date (ISO format: YYYY-MM-DDTHH:MM:SS)
- `end_date` (string, optional): Filter by end date (ISO format: YYYY-MM-DDTHH:MM:SS)

**Response:**
```json
{
  "recordings": [
    {
      "id": 1,
      "timestamp": "2025-09-18T18:59:19.546",
      "stream_id": "6a0e10d5-b890-4483-8e39-f2916a0f6c09",
      "stream_name": "Front Door",
      "file_path": "/Users/davide/video-feed-recordings/Front_Door_2025-09-18_18-59-19.mp4",
      "duration": 141.12,
      "objects_detected": [
        {
          "class": "person",
          "confidence": 0.85,
          "bbox": [100, 150, 300, 450]
        }
      ],
      "thumbnail_path": "/Users/davide/video-feed-recordings/Front_Door_2025-09-18_18-59-19_thumb.jpg",
      "confidence": 0.85,
      "retained": 1
    },
    // More recordings...
  ],
  "total": 42
}
```

### 2. Get Recording Details

**Endpoint:** `GET /api/recordings/{id}`

**Path Parameters:**
- `id` (integer, required): Recording ID

**Response:**
```json
{
  "id": 1,
  "timestamp": "2025-09-18T18:59:19.546",
  "stream_id": "6a0e10d5-b890-4483-8e39-f2916a0f6c09",
  "stream_name": "Front Door",
  "file_path": "/Users/davide/video-feed-recordings/Front_Door_2025-09-18_18-59-19.mp4",
  "duration": 141.12,
  "objects_detected": [
    {
      "class": "person",
      "confidence": 0.85,
      "bbox": [100, 150, 300, 450]
    }
  ],
  "thumbnail_path": "/Users/davide/video-feed-recordings/Front_Door_2025-09-18_18-59-19_thumb.jpg",
  "confidence": 0.85,
  "retained": 1
}
```

### 3. Serve Recording Files

**Endpoint:** `GET /recordings/{filename}`

**Path Parameters:**
- `filename` (string, required): Name of the recording file (without path)

**Response:**
- Binary file data (video/mp4 or image/jpeg)

### 4. Get Recording Statistics

**Endpoint:** `GET /api/stats/recordings`

**Response:**
```json
{
  "total_recordings": 42,
  "total_duration": 3600.5,
  "object_counts": {
    "person": 156,
    "car": 89,
    "dog": 12
  },
  "storage_used": 1024000000,
  "storage_limit": 10737418240
}
```

## Media File Access

To access video files and thumbnails:

1. Extract just the filename from the `file_path` or `thumbnail_path`:
   ```javascript
   const filename = path.split('/').pop();
   ```

2. Construct the URL:
   ```javascript
   const mediaUrl = `${apiBaseUrl}/recordings/${filename}`;
   ```

## Data Types

### Recording Object

```typescript
interface Recording {
  id: number;
  timestamp: string;         // ISO format date string
  stream_id: string;         // UUID of the stream
  stream_name: string;       // Human-readable name
  file_path: string;         // Full path to MP4 file
  duration: number;          // Duration in seconds
  objects_detected: {
    class: string;           // Object class (person, car, etc.)
    confidence: number;      // Confidence score (0.0-1.0)
    bbox?: number[];         // Bounding box [x1, y1, x2, y2]
  }[];
  thumbnail_path: string;    // Path to thumbnail image
  confidence: number;        // Highest confidence score
  retained: number;          // 1 if file exists, 0 if deleted
}
```

## CORS Support

The API supports CORS for cross-origin requests from your Next.js application. No additional headers are required for basic requests.

## Error Responses

All endpoints return standard HTTP status codes:
- `200 OK`: Request successful
- `400 Bad Request`: Invalid parameters
- `404 Not Found`: Recording or file not found
- `500 Internal Server Error`: Server-side error

Error response format:
```json
{
  "detail": "Error message"
}
```
