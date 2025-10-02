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

All recordings are stored in the user's home directory by default:

```
~/video-feed-recordings/
├── recordings.db                    # SQLite database with metadata
├── camera-1_2024-01-15_14-30-25.mp4    # Video recording
├── camera-1_2024-01-15_14-30-25_thumb.jpg  # Thumbnail
├── camera-2_2024-01-15_15-45-10.mp4
└── camera-2_2024-01-15_15-45-10_thumb.jpg
```

**Important**: The system automatically expands `~` to your home directory. All data is stored on the machine's hard drive, not in the project directory.

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

## API Endpoints Overview

The system provides comprehensive REST API endpoints for recordings:

- `GET /api/recordings` - List recordings with filtering and pagination
- `GET /api/recordings/{id}` - Get specific recording details
- `DELETE /api/recordings/{id}` - Delete a recording
- `GET /api/alerts` - Get detection alerts
- `GET /api/stats/objects` - Object detection statistics
- `GET /api/stats/times` - Time-based detection statistics
- `GET /api/streams` - Get all streams with recording stats
- `GET /recordings/{file_path}` - Serve recording files (videos and thumbnails)

See the **API Specifications** section below for detailed documentation.

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

---

# API Specifications

## Base URL

```
http://localhost:8080
```

Replace `localhost` with your server's IP address when accessing from other devices.

## Authentication

Currently, the API uses the same authentication as the web interface. Future versions may include API key authentication.

---

## Endpoints

### 1. List Recordings

Retrieve a paginated list of recordings with optional filtering.

**Endpoint:** `GET /api/recordings`

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `limit` | integer | No | 100 | Maximum number of recordings to return (1-1000) |
| `offset` | integer | No | 0 | Number of recordings to skip (for pagination) |
| `stream_id` | string | No | - | Filter by stream ID |
| `start_date` | string | No | - | Filter by start date (ISO format: `YYYY-MM-DDTHH:MM:SS`) |
| `end_date` | string | No | - | Filter by end date (ISO format: `YYYY-MM-DDTHH:MM:SS`) |
| `object_type` | string | No | - | Filter by detected object type (e.g., "person", "car") |
| `min_confidence` | float | No | - | Minimum confidence threshold (0.0-1.0) |
| `sort_by` | string | No | timestamp | Sort field: `timestamp`, `confidence`, or `duration` |
| `sort_order` | string | No | desc | Sort order: `asc` or `desc` |

**Example Request:**
```bash
curl "http://localhost:8080/api/recordings?limit=10&object_type=person&min_confidence=0.7&sort_by=timestamp&sort_order=desc"
```

**Response:**
```json
{
  "total": 42,
  "offset": 0,
  "limit": 10,
  "recordings": [
    {
      "id": 1,
      "timestamp": "2025-10-01T18:59:19.546",
      "stream_id": "6a0e10d5-b890-4483-8e39-f2916a0f6c09",
      "stream_name": "Front Door",
      "file_path": "/Users/davide/video-feed-recordings/Front_Door_2025-10-01_18-59-19.mp4",
      "file_url": "/recordings/Front_Door_2025-10-01_18-59-19.mp4",
      "duration": 141.12,
      "objects_detected": [
        {
          "class": "person",
          "confidence": 0.85,
          "bbox": [100, 150, 300, 450]
        }
      ],
      "thumbnail_path": "/Users/davide/video-feed-recordings/Front_Door_2025-10-01_18-59-19_thumb.jpg",
      "thumbnail_url": "/recordings/Front_Door_2025-10-01_18-59-19_thumb.jpg",
      "confidence": 0.85,
      "retained": 1
    }
  ]
}
```

**Client Example (JavaScript):**
```javascript
async function fetchRecordings(options = {}) {
  const params = new URLSearchParams({
    limit: options.limit || 20,
    offset: options.offset || 0,
    ...(options.stream_id && { stream_id: options.stream_id }),
    ...(options.object_type && { object_type: options.object_type }),
    ...(options.min_confidence && { min_confidence: options.min_confidence }),
    sort_by: options.sort_by || 'timestamp',
    sort_order: options.sort_order || 'desc'
  });

  const response = await fetch(`http://localhost:8080/api/recordings?${params}`);
  const data = await response.json();
  return data;
}

// Usage
const recordings = await fetchRecordings({
  limit: 10,
  object_type: 'person',
  min_confidence: 0.7
});
```

**Client Example (Python):**
```python
import requests

def fetch_recordings(limit=20, offset=0, **filters):
    params = {
        'limit': limit,
        'offset': offset,
        **filters
    }
    response = requests.get('http://localhost:8080/api/recordings', params=params)
    return response.json()

# Usage
recordings = fetch_recordings(
    limit=10,
    object_type='person',
    min_confidence=0.7,
    sort_by='confidence',
    sort_order='desc'
)
```

---

### 2. Get Recording Details

Retrieve detailed information about a specific recording.

**Endpoint:** `GET /api/recordings/{id}`

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | integer | Yes | Recording ID |

**Example Request:**
```bash
curl "http://localhost:8080/api/recordings/1"
```

**Response:**
```json
{
  "id": 1,
  "timestamp": "2025-10-01T18:59:19.546",
  "stream_id": "6a0e10d5-b890-4483-8e39-f2916a0f6c09",
  "stream_name": "Front Door",
  "file_path": "/Users/davide/video-feed-recordings/Front_Door_2025-10-01_18-59-19.mp4",
  "file_url": "/recordings/Front_Door_2025-10-01_18-59-19.mp4",
  "duration": 141.12,
  "objects_detected": [
    {
      "class": "person",
      "confidence": 0.85,
      "bbox": [100, 150, 300, 450]
    }
  ],
  "thumbnail_path": "/Users/davide/video-feed-recordings/Front_Door_2025-10-01_18-59-19_thumb.jpg",
  "thumbnail_url": "/recordings/Front_Door_2025-10-01_18-59-19_thumb.jpg",
  "confidence": 0.85,
  "retained": 1
}
```

**Client Example (JavaScript):**
```javascript
async function getRecording(recordingId) {
  const response = await fetch(`http://localhost:8080/api/recordings/${recordingId}`);
  if (!response.ok) {
    throw new Error(`Recording ${recordingId} not found`);
  }
  return await response.json();
}
```

---

### 3. Delete Recording

Delete a recording and its associated files.

**Endpoint:** `DELETE /api/recordings/{id}`

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | integer | Yes | Recording ID |

**Example Request:**
```bash
curl -X DELETE "http://localhost:8080/api/recordings/1"
```

**Response:**
```json
{
  "success": true,
  "message": "Recording 1 deleted"
}
```

**Client Example (JavaScript):**
```javascript
async function deleteRecording(recordingId) {
  const response = await fetch(`http://localhost:8080/api/recordings/${recordingId}`, {
    method: 'DELETE'
  });
  
  if (!response.ok) {
    throw new Error(`Failed to delete recording ${recordingId}`);
  }
  
  return await response.json();
}
```

---

### 4. Get Detection Alerts

Retrieve recent detection alerts for monitoring.

**Endpoint:** `GET /api/alerts`

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `limit` | integer | No | 100 | Maximum number of alerts to return (1-1000) |
| `offset` | integer | No | 0 | Number of alerts to skip |
| `start_date` | string | No | - | Filter by start date (ISO format) |
| `end_date` | string | No | - | Filter by end date (ISO format) |
| `object_type` | string | No | - | Filter by object type |
| `min_confidence` | float | No | 0.5 | Minimum confidence threshold |

**Example Request:**
```bash
curl "http://localhost:8080/api/alerts?limit=5&min_confidence=0.8"
```

**Response:**
```json
{
  "total": 156,
  "offset": 0,
  "limit": 5,
  "alerts": [
    {
      "id": 42,
      "timestamp": "2025-10-01T19:30:15.123",
      "stream_id": "6a0e10d5-b890-4483-8e39-f2916a0f6c09",
      "stream_name": "Front Door",
      "confidence": 0.92,
      "objects_detected": [
        {
          "class": "person",
          "confidence": 0.92,
          "bbox": [120, 180, 340, 520]
        }
      ],
      "object_counts": {
        "person": 1
      },
      "thumbnail_path": "/Users/davide/video-feed-recordings/Front_Door_2025-10-01_19-30-15_thumb.jpg",
      "thumbnail_url": "/recordings/Front_Door_2025-10-01_19-30-15_thumb.jpg"
    }
  ]
}
```

**Client Example (JavaScript):**
```javascript
async function fetchAlerts(options = {}) {
  const params = new URLSearchParams({
    limit: options.limit || 20,
    offset: options.offset || 0,
    min_confidence: options.min_confidence || 0.5,
    ...(options.object_type && { object_type: options.object_type })
  });

  const response = await fetch(`http://localhost:8080/api/alerts?${params}`);
  return await response.json();
}
```

---

### 5. Get Object Statistics

Retrieve statistics about detected objects over time.

**Endpoint:** `GET /api/stats/objects`

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `start_date` | string | No | Filter by start date (ISO format) |
| `end_date` | string | No | Filter by end date (ISO format) |
| `stream_id` | string | No | Filter by stream ID |

**Example Request:**
```bash
curl "http://localhost:8080/api/stats/objects"
```

**Response:**
```json
{
  "stats": {
    "total_recordings": 156,
    "object_counts": {
      "person": 89,
      "car": 45,
      "dog": 12,
      "cat": 10
    },
    "object_percentages": {
      "person": 57.05,
      "car": 28.85,
      "dog": 7.69,
      "cat": 6.41
    }
  }
}
```

**Client Example (JavaScript):**
```javascript
async function getObjectStats(streamId = null) {
  const params = streamId ? `?stream_id=${streamId}` : '';
  const response = await fetch(`http://localhost:8080/api/stats/objects${params}`);
  return await response.json();
}
```

---

### 6. Get Time-Based Statistics

Retrieve detection statistics by time of day and day of week.

**Endpoint:** `GET /api/stats/times`

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `object_type` | string | No | - | Filter by object type |
| `days` | integer | No | 7 | Number of days to analyze (1-90) |
| `stream_id` | string | No | - | Filter by stream ID |

**Example Request:**
```bash
curl "http://localhost:8080/api/stats/times?object_type=person&days=7"
```

**Response:**
```json
{
  "stats": {
    "hours": [
      { "hour": 0, "detections": 2 },
      { "hour": 1, "detections": 0 },
      { "hour": 2, "detections": 1 },
      ...
      { "hour": 23, "detections": 5 }
    ],
    "days": [
      { "day": "Monday", "detections": 15 },
      { "day": "Tuesday", "detections": 22 },
      { "day": "Wednesday", "detections": 18 },
      { "day": "Thursday", "detections": 20 },
      { "day": "Friday", "detections": 25 },
      { "day": "Saturday", "detections": 30 },
      { "day": "Sunday", "detections": 28 }
    ]
  }
}
```

**Client Example (JavaScript):**
```javascript
async function getTimeStats(objectType = null, days = 7) {
  const params = new URLSearchParams({ days });
  if (objectType) params.append('object_type', objectType);
  
  const response = await fetch(`http://localhost:8080/api/stats/times?${params}`);
  return await response.json();
}
```

---

### 7. Get Streams Information

Retrieve information about all video streams with recording statistics.

**Endpoint:** `GET /api/streams`

**Example Request:**
```bash
curl "http://localhost:8080/api/streams"
```

**Response:**
```json
{
  "streams": [
    {
      "id": "6a0e10d5-b890-4483-8e39-f2916a0f6c09",
      "name": "Front Door",
      "source": "rtsp://***:***@192.168.1.100:8554/video/camera-1",
      "status": "active",
      "fps": 29.8,
      "resolution": [960, 540],
      "recording_stats": {
        "recording_count": 42,
        "total_duration": 3600.5,
        "latest_recording": "2025-10-01T19:30:15.123"
      }
    }
  ]
}
```

---

### 8. Serve Recording Files

Serve video files and thumbnails.

**Endpoint:** `GET /recordings/{file_path}`

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file_path` | string | Yes | Relative path to the file (from recordings directory) |

**Example Request:**
```bash
curl "http://localhost:8080/recordings/Front_Door_2025-10-01_18-59-19.mp4" --output video.mp4
```

**Response:**
- Binary file data (video/mp4 or image/jpeg)
- Appropriate Content-Type header

**Client Example (JavaScript):**
```javascript
// Display thumbnail
function displayThumbnail(recording) {
  const img = document.createElement('img');
  img.src = `http://localhost:8080${recording.thumbnail_url}`;
  document.body.appendChild(img);
}

// Play video
function playVideo(recording) {
  const video = document.createElement('video');
  video.src = `http://localhost:8080${recording.file_url}`;
  video.controls = true;
  document.body.appendChild(video);
}
```

---

## Media File Access

The API provides two ways to access media files:

### Method 1: Using `file_url` and `thumbnail_url` (Recommended)

The API automatically generates relative URLs for you:

```javascript
const recording = await getRecording(1);

// Access video
const videoUrl = `http://localhost:8080${recording.file_url}`;

// Access thumbnail
const thumbnailUrl = `http://localhost:8080${recording.thumbnail_url}`;
```

### Method 2: Extracting from file paths

If you need to construct URLs manually:

```javascript
function getMediaUrl(filePath) {
  const filename = filePath.split('/').pop();
  return `http://localhost:8080/recordings/${filename}`;
}

const videoUrl = getMediaUrl(recording.file_path);
const thumbnailUrl = getMediaUrl(recording.thumbnail_path);
```

---

## Data Types

### Recording Object

```typescript
interface Recording {
  id: number;                // Unique recording ID
  timestamp: string;         // ISO format date string (YYYY-MM-DDTHH:MM:SS)
  stream_id: string;         // UUID of the stream
  stream_name: string;       // Human-readable stream name
  file_path: string;         // Absolute path to MP4 file on server
  file_url: string;          // Relative URL to access the video file
  duration: number;          // Duration in seconds
  objects_detected: DetectedObject[];  // Array of detected objects
  thumbnail_path: string;    // Absolute path to thumbnail image on server
  thumbnail_url: string;     // Relative URL to access the thumbnail
  confidence: number;        // Highest confidence score (0.0-1.0)
  retained: number;          // 1 if file exists, 0 if deleted
}

interface DetectedObject {
  class: string;             // Object class (person, car, dog, cat, etc.)
  confidence: number;        // Confidence score (0.0-1.0)
  bbox?: number[];           // Bounding box [x1, y1, x2, y2] (optional)
}
```

### Alert Object

```typescript
interface Alert {
  id: number;                // Recording ID
  timestamp: string;         // ISO format date string
  stream_id: string;         // UUID of the stream
  stream_name: string;       // Human-readable stream name
  confidence: number;        // Highest confidence score
  objects_detected: DetectedObject[];  // Array of detected objects
  object_counts: Record<string, number>;  // Count of each object type
  thumbnail_path: string;    // Absolute path to thumbnail
  thumbnail_url: string;     // Relative URL to thumbnail
}
```

### Stream Object

```typescript
interface Stream {
  id: string;                // Stream UUID
  name: string;              // Human-readable name
  source: string;            // Masked RTSP URL
  status: string;            // Stream status (active, inactive)
  fps: number;               // Current frames per second
  resolution: [number, number];  // [width, height]
  recording_stats: {
    recording_count: number;     // Total number of recordings
    total_duration: number;      // Total duration in seconds
    latest_recording: string;    // ISO timestamp of latest recording
  };
}
```

---

## CORS Support

The API supports CORS (Cross-Origin Resource Sharing) for requests from web applications:

- **Allowed Origins**: `*` (all origins)
- **Allowed Methods**: All HTTP methods
- **Allowed Headers**: All headers
- **Credentials**: Supported

No additional configuration is required for basic requests from web clients.

---

## Error Responses

All endpoints return standard HTTP status codes:

| Status Code | Description |
|-------------|-------------|
| `200 OK` | Request successful |
| `400 Bad Request` | Invalid parameters or malformed request |
| `404 Not Found` | Recording or file not found |
| `500 Internal Server Error` | Server-side error |
| `503 Service Unavailable` | Recording API not initialized |

**Error Response Format:**
```json
{
  "detail": "Error message describing what went wrong"
}
```

**Example Error Response:**
```json
{
  "detail": "Recording 999 not found"
}
```

**Client Error Handling (JavaScript):**
```javascript
async function fetchRecordingSafely(recordingId) {
  try {
    const response = await fetch(`http://localhost:8080/api/recordings/${recordingId}`);
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || `HTTP ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Failed to fetch recording:', error.message);
    return null;
  }
}
```

---

## Complete Client Example

Here's a complete example of a client application using the Recording API:

### JavaScript/TypeScript Client

```javascript
class RecordingAPIClient {
  constructor(baseUrl = 'http://localhost:8080') {
    this.baseUrl = baseUrl;
  }

  async fetchRecordings(options = {}) {
    const params = new URLSearchParams({
      limit: options.limit || 20,
      offset: options.offset || 0,
      sort_by: options.sortBy || 'timestamp',
      sort_order: options.sortOrder || 'desc',
      ...(options.streamId && { stream_id: options.streamId }),
      ...(options.objectType && { object_type: options.objectType }),
      ...(options.minConfidence && { min_confidence: options.minConfidence }),
      ...(options.startDate && { start_date: options.startDate }),
      ...(options.endDate && { end_date: options.endDate })
    });

    const response = await fetch(`${this.baseUrl}/api/recordings?${params}`);
    if (!response.ok) throw new Error('Failed to fetch recordings');
    return await response.json();
  }

  async getRecording(id) {
    const response = await fetch(`${this.baseUrl}/api/recordings/${id}`);
    if (!response.ok) throw new Error(`Recording ${id} not found`);
    return await response.json();
  }

  async deleteRecording(id) {
    const response = await fetch(`${this.baseUrl}/api/recordings/${id}`, {
      method: 'DELETE'
    });
    if (!response.ok) throw new Error(`Failed to delete recording ${id}`);
    return await response.json();
  }

  async fetchAlerts(options = {}) {
    const params = new URLSearchParams({
      limit: options.limit || 20,
      offset: options.offset || 0,
      min_confidence: options.minConfidence || 0.5,
      ...(options.objectType && { object_type: options.objectType })
    });

    const response = await fetch(`${this.baseUrl}/api/alerts?${params}`);
    if (!response.ok) throw new Error('Failed to fetch alerts');
    return await response.json();
  }

  async getObjectStats(streamId = null) {
    const params = streamId ? `?stream_id=${streamId}` : '';
    const response = await fetch(`${this.baseUrl}/api/stats/objects${params}`);
    if (!response.ok) throw new Error('Failed to fetch object stats');
    return await response.json();
  }

  async getTimeStats(objectType = null, days = 7) {
    const params = new URLSearchParams({ days });
    if (objectType) params.append('object_type', objectType);
    
    const response = await fetch(`${this.baseUrl}/api/stats/times?${params}`);
    if (!response.ok) throw new Error('Failed to fetch time stats');
    return await response.json();
  }

  async getStreams() {
    const response = await fetch(`${this.baseUrl}/api/streams`);
    if (!response.ok) throw new Error('Failed to fetch streams');
    return await response.json();
  }

  getVideoUrl(recording) {
    return `${this.baseUrl}${recording.file_url}`;
  }

  getThumbnailUrl(recording) {
    return `${this.baseUrl}${recording.thumbnail_url}`;
  }
}

// Usage
const client = new RecordingAPIClient('http://192.168.1.100:8080');

// Fetch recent recordings
const { recordings, total } = await client.fetchRecordings({
  limit: 10,
  objectType: 'person',
  minConfidence: 0.7
});

// Get specific recording
const recording = await client.getRecording(1);

// Display video
const videoUrl = client.getVideoUrl(recording);
console.log('Video URL:', videoUrl);

// Get statistics
const stats = await client.getObjectStats();
console.log('Object counts:', stats.stats.object_counts);
```

### Python Client

```python
import requests
from typing import Optional, Dict, List

class RecordingAPIClient:
    def __init__(self, base_url: str = 'http://localhost:8080'):
        self.base_url = base_url
        self.session = requests.Session()
    
    def fetch_recordings(self, 
                        limit: int = 20,
                        offset: int = 0,
                        stream_id: Optional[str] = None,
                        object_type: Optional[str] = None,
                        min_confidence: Optional[float] = None,
                        sort_by: str = 'timestamp',
                        sort_order: str = 'desc') -> Dict:
        params = {
            'limit': limit,
            'offset': offset,
            'sort_by': sort_by,
            'sort_order': sort_order
        }
        if stream_id:
            params['stream_id'] = stream_id
        if object_type:
            params['object_type'] = object_type
        if min_confidence:
            params['min_confidence'] = min_confidence
        
        response = self.session.get(f'{self.base_url}/api/recordings', params=params)
        response.raise_for_status()
        return response.json()
    
    def get_recording(self, recording_id: int) -> Dict:
        response = self.session.get(f'{self.base_url}/api/recordings/{recording_id}')
        response.raise_for_status()
        return response.json()
    
    def delete_recording(self, recording_id: int) -> Dict:
        response = self.session.delete(f'{self.base_url}/api/recordings/{recording_id}')
        response.raise_for_status()
        return response.json()
    
    def fetch_alerts(self, 
                    limit: int = 20,
                    offset: int = 0,
                    min_confidence: float = 0.5,
                    object_type: Optional[str] = None) -> Dict:
        params = {
            'limit': limit,
            'offset': offset,
            'min_confidence': min_confidence
        }
        if object_type:
            params['object_type'] = object_type
        
        response = self.session.get(f'{self.base_url}/api/alerts', params=params)
        response.raise_for_status()
        return response.json()
    
    def get_object_stats(self, stream_id: Optional[str] = None) -> Dict:
        params = {'stream_id': stream_id} if stream_id else {}
        response = self.session.get(f'{self.base_url}/api/stats/objects', params=params)
        response.raise_for_status()
        return response.json()
    
    def get_time_stats(self, object_type: Optional[str] = None, days: int = 7) -> Dict:
        params = {'days': days}
        if object_type:
            params['object_type'] = object_type
        
        response = self.session.get(f'{self.base_url}/api/stats/times', params=params)
        response.raise_for_status()
        return response.json()
    
    def get_streams(self) -> Dict:
        response = self.session.get(f'{self.base_url}/api/streams')
        response.raise_for_status()
        return response.json()
    
    def get_video_url(self, recording: Dict) -> str:
        return f"{self.base_url}{recording['file_url']}"
    
    def get_thumbnail_url(self, recording: Dict) -> str:
        return f"{self.base_url}{recording['thumbnail_url']}"
    
    def download_video(self, recording: Dict, output_path: str):
        """Download a recording video to a local file."""
        url = self.get_video_url(recording)
        response = self.session.get(url, stream=True)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

# Usage
client = RecordingAPIClient('http://192.168.1.100:8080')

# Fetch recent recordings
data = client.fetch_recordings(limit=10, object_type='person', min_confidence=0.7)
recordings = data['recordings']
print(f"Found {data['total']} recordings")

# Get specific recording
recording = client.get_recording(1)
print(f"Recording duration: {recording['duration']} seconds")

# Download video
client.download_video(recording, 'recording.mp4')

# Get statistics
stats = client.get_object_stats()
print(f"Object counts: {stats['stats']['object_counts']}")
```

---

## Storage Location

**Important**: All recordings and the database are stored in the user's home directory:

```
~/video-feed-recordings/
```

The system automatically expands the `~` symbol to the user's home directory. This ensures:

- Data persists across application updates
- Data is stored on the machine's hard drive, not in the project directory
- Multiple users on the same machine have separate recording directories
- Recordings are easily accessible for backup or manual management

You can customize the storage location in `surveillance.yml`:

```yaml
recording:
  recordings_dir: "/path/to/custom/directory"
```

---

## Rate Limiting

Currently, there is no rate limiting on the API. For production use, consider implementing rate limiting at the reverse proxy level (e.g., nginx, Caddy).

---

## Webhooks (Future Feature)

Webhook support for real-time notifications is planned for a future release. This will allow you to receive HTTP callbacks when new recordings are created or specific objects are detected.
