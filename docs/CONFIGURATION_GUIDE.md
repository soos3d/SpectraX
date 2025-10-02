# SentriX Configuration Guide

**Last Updated:** 2025-10-02  
**Version:** 2.0 - Unified Configuration

---

## Overview

**`surveillance.yml` is now the ONLY file you need to configure your entire surveillance system.**

All settings—from camera paths to visual appearance—are managed through this single, well-documented YAML file.

---

## Quick Start

1. **Edit `surveillance.yml`** in the project root
2. **Run the system:** `./surveillance.sh config`
3. **That's it!** All changes take effect immediately

---

## Configuration Sections

### **1. Camera Streams** 📹

```yaml
cameras:
  - video/front-door
  - video/backyard
  - video/garage
```

**What it does:** Defines the RTSP paths for your camera streams.

**Tips:**
- Use descriptive names (e.g., `video/front-door` not `video/cam1`)
- Each path becomes a unique stream endpoint
- Add/remove cameras by editing this list

---

### **2. Network Settings** 🌐

```yaml
network:
  bind: "127.0.0.1"  # or "0.0.0.0" for LAN access
  api_port: 3333
```

**What it does:** Controls network access and ports.

**Options:**
- `bind: "127.0.0.1"` - **Secure**: Localhost only (recommended)
- `bind: "0.0.0.0"` - **Less secure**: Accessible from LAN

**Ports:**
- `api_port: 3333` - Camera path discovery API
- Detection dashboard runs on port 8080 (set in detection section)

---

### **3. Object Detection** 🎯

#### **Basic Settings**

```yaml
detection:
  enabled: true
  port: 8080
  model: "yolov8n.pt"
  confidence: 0.4
```

**Model Options:**
- `yolov8n.pt` - **Fastest** (nano, ~6MB, recommended for most)
- `yolov8s.pt` - Small (~22MB, more accurate)
- `yolov8m.pt` - Medium (~52MB, even more accurate)
- `yolov8l.pt` - Large (~88MB, most accurate but slowest)

**Confidence Threshold:**
- `0.3` - More detections, more false positives
- `0.4` - **Recommended** balance
- `0.5+` - Fewer detections, higher accuracy

#### **Resolution**

```yaml
resolution:
  width: 960
  height: 540
```

**Common Resolutions:**
- `640x480` - Fastest, lowest quality
- `960x540` - **Recommended** balance
- `1280x720` - HD, slower processing
- `1920x1080` - Full HD, slowest

**Rule of thumb:** Lower resolution = faster processing, less detail

#### **Stream Processing** (NEW!)

```yaml
stream:
  buffer_size: 10          # Frame buffer (1-30)
  reconnect_interval: 5    # Seconds between reconnects
```

**Buffer Size:**
- `5` - Lower latency, may drop frames
- `10` - **Recommended** balance
- `20+` - Smoother playback, higher latency

#### **Detection Filters** (NEW!)

```yaml
filters:
  classes: ["person", "car"]  # Only detect these
  min_area: 1000              # Ignore tiny detections
  max_area: 500000            # Ignore huge detections
```

**Common Object Classes:**
- **People:** `person`
- **Vehicles:** `car`, `truck`, `bus`, `motorcycle`, `bicycle`
- **Animals:** `dog`, `cat`, `bird`, `horse`, `cow`, `sheep`
- **Objects:** `backpack`, `umbrella`, `handbag`, `suitcase`

**Area Filtering:**
- `min_area: 1000` - Ignore detections smaller than 1000 pixels
- `max_area: 500000` - Ignore detections larger than 500k pixels
- Use `null` for no limit

**Examples:**

```yaml
# Person-only detection
filters:
  classes: ["person"]
  min_area: 2000  # Ignore small/distant people

# Vehicle monitoring
filters:
  classes: ["car", "truck", "bus", "motorcycle"]
  min_area: 5000  # Ignore far-away vehicles

# Pet monitoring
filters:
  classes: ["dog", "cat"]
  min_area: 1000

# Detect everything (default)
filters:
  classes: []
  min_area: null
  max_area: null
```

---

### **4. Visual Appearance** 🎨 (NEW!)

Customize how detections are displayed on video.

#### **Bounding Boxes**

```yaml
appearance:
  box:
    thickness: 2     # Line thickness (1-5)
    color: "green"   # Box color
```

**Available Colors:**
- `green` - Default, easy to see
- `red` - High alert
- `blue` - Cool tone
- `yellow` - High visibility
- `white` - Clean look
- `roboflow` - Roboflow brand color

#### **Labels**

```yaml
  label:
    text_scale: 0.5        # Text size (0.3-1.0)
    text_thickness: 1      # Text thickness (1-3)
    text_padding: 10       # Padding around text
    position: "top_left"   # Label position
    border_radius: 0       # Rounded corners (0 = square)
```

**Label Positions:**
- `top_left` - Default
- `top_center` - Centered above box
- `top_right` - Right side above box
- `center_left` - Left side of box
- `center` - Center of box
- `bottom_left` - Below box (left)

**Style Examples:**

```yaml
# High visibility (for outdoor/bright scenes)
appearance:
  box:
    thickness: 3
    color: "yellow"
  label:
    text_scale: 0.6
    text_thickness: 2

# Minimal/clean (for indoor/dark scenes)
appearance:
  box:
    thickness: 1
    color: "white"
  label:
    text_scale: 0.4
    text_thickness: 1

# Alert mode (for security)
appearance:
  box:
    thickness: 3
    color: "red"
  label:
    text_scale: 0.7
    text_thickness: 2
    border_radius: 5  # Rounded labels
```

---

### **5. Recording** 📹

```yaml
recording:
  enabled: false
  min_confidence: 0.5
  pre_buffer_seconds: 10
  post_buffer_seconds: 10
  max_storage_gb: 10.0
  recordings_dir: "~/video-feed-recordings"
  record_objects: ["person", "car", "dog", "cat"]
```

**How it works:**
1. Detection occurs with confidence ≥ `min_confidence`
2. System records `pre_buffer_seconds` BEFORE detection
3. Continues recording until `post_buffer_seconds` after last detection
4. Saves to `recordings_dir` with metadata

**Storage Management:**
- `max_storage_gb: 10.0` - Auto-cleanup when limit reached
- Oldest recordings deleted first

**Selective Recording:**
- `record_objects: ["person"]` - Only record when people detected
- `record_objects: []` - Record all detections

**Examples:**

```yaml
# Security mode (person detection only)
recording:
  enabled: true
  min_confidence: 0.6  # Higher confidence
  pre_buffer_seconds: 15  # More context before
  post_buffer_seconds: 20  # More context after
  record_objects: ["person"]

# Pet monitoring
recording:
  enabled: true
  min_confidence: 0.5
  pre_buffer_seconds: 5
  post_buffer_seconds: 10
  record_objects: ["dog", "cat"]

# Traffic monitoring
recording:
  enabled: true
  min_confidence: 0.5
  record_objects: ["car", "truck", "bus", "motorcycle"]
```

---

### **6. Security** 🔐

```yaml
security:
  use_tls: true
  tls_key: ""    # Custom key path (optional)
  tls_cert: ""   # Custom cert path (optional)
```

**TLS Encryption:**
- `use_tls: true` - **Recommended**: Enables RTSPS (encrypted RTSP)
- `use_tls: false` - Unencrypted RTSP (faster but less secure)

**Custom Certificates:**
- Leave empty to use auto-generated self-signed certs
- Provide paths for custom CA-signed certificates

---

### **7. Advanced Settings** ⚙️ (Optional)

```yaml
# Uncomment to enable
advanced:
  debug: false
  
  mediamtx:
    rtsp_port: 8554
    rtsps_port: 8322
    hls_port: 8888
  
  performance:
    max_detectors: 10
    thread_pool_size: 3
```

**Debug Mode:**
- `debug: true` - Verbose logging for troubleshooting

**Custom Ports:**
- Change if default ports conflict with other services

**Performance Tuning:**
- `max_detectors: 10` - Maximum concurrent camera streams
- `thread_pool_size: 3` - Processing thread pool size

---

## Complete Configuration Examples

### **Example 1: Home Security (Person Detection)**

```yaml
cameras:
  - video/front-door
  - video/backyard

network:
  bind: "127.0.0.1"
  api_port: 3333

detection:
  enabled: true
  port: 8080
  model: "yolov8n.pt"
  confidence: 0.5
  resolution:
    width: 1280
    height: 720
  stream:
    buffer_size: 10
    reconnect_interval: 5
  filters:
    classes: ["person"]
    min_area: 2000

appearance:
  box:
    thickness: 3
    color: "red"
  label:
    text_scale: 0.6
    text_thickness: 2
    position: "top_left"

recording:
  enabled: true
  min_confidence: 0.6
  pre_buffer_seconds: 15
  post_buffer_seconds: 20
  max_storage_gb: 50.0
  recordings_dir: "~/security-recordings"
  record_objects: ["person"]

security:
  use_tls: true
```

---

### **Example 2: Pet Monitoring**

```yaml
cameras:
  - video/living-room
  - video/backyard

detection:
  enabled: true
  model: "yolov8s.pt"  # More accurate for pets
  confidence: 0.4
  resolution:
    width: 960
    height: 540
  filters:
    classes: ["dog", "cat", "bird"]
    min_area: 1000

appearance:
  box:
    thickness: 2
    color: "green"
  label:
    text_scale: 0.5

recording:
  enabled: true
  min_confidence: 0.5
  pre_buffer_seconds: 10
  post_buffer_seconds: 15
  record_objects: ["dog", "cat"]
```

---

### **Example 3: Traffic Monitoring**

```yaml
cameras:
  - video/street-view

detection:
  enabled: true
  model: "yolov8m.pt"  # Better for vehicles
  confidence: 0.5
  resolution:
    width: 1920
    height: 1080
  filters:
    classes: ["car", "truck", "bus", "motorcycle", "bicycle"]
    min_area: 5000  # Ignore distant vehicles

appearance:
  box:
    thickness: 2
    color: "blue"

recording:
  enabled: true
  record_objects: ["car", "truck", "bus"]
```

---

## Configuration Best Practices

### **Performance Optimization**

1. **Start with `yolov8n.pt`** - Fastest model, good for most use cases
2. **Use lower resolution** (960x540) for faster processing
3. **Filter by class** - Only detect what you need
4. **Set min_area** - Ignore tiny/distant objects

### **Accuracy Optimization**

1. **Use larger model** (`yolov8s.pt` or `yolov8m.pt`)
2. **Higher resolution** (1280x720 or 1920x1080)
3. **Higher confidence** (0.5-0.6) to reduce false positives
4. **Set max_area** - Ignore unrealistic detections

### **Storage Optimization**

1. **Selective recording** - Only record specific objects
2. **Higher min_confidence** for recording
3. **Shorter buffers** (5-10 seconds)
4. **Lower max_storage_gb** with auto-cleanup

---

## Troubleshooting

### **No detections appearing**

- Lower `confidence` threshold (try 0.3)
- Check `filters.classes` - make sure it includes objects in view
- Verify `min_area` isn't too high

### **Too many false positives**

- Raise `confidence` threshold (try 0.5-0.6)
- Add `filters.classes` to only detect specific objects
- Set `min_area` to ignore tiny detections

### **Slow performance**

- Use smaller model (`yolov8n.pt`)
- Lower resolution (640x480 or 960x540)
- Reduce `buffer_size` to 5
- Enable class filtering

### **Colors not working**

- Check spelling: `"green"`, `"red"`, `"blue"`, etc.
- Must be lowercase string in quotes
- See available colors in Visual Appearance section

---

## Migration from Old Config

If you have old code using individual parameters:

**Old way:**
```python
detector_manager.add_detector(
    source_url=url,
    model_path="yolov8n.pt",
    confidence=0.5,
    resolution=(960, 540)
)
```

**New way:**
Just edit `surveillance.yml` and run:
```bash
./surveillance.sh config
```

All settings are automatically loaded from the YAML file!

---

## Summary

✅ **One file to rule them all:** `surveillance.yml`  
✅ **No code changes needed:** Edit YAML, restart system  
✅ **Fully documented:** Every setting explained with examples  
✅ **Type-safe:** Validated on load with helpful error messages  
✅ **Extensible:** Easy to add new settings in future  

**Next time you want to change anything, just edit `surveillance.yml`!** 🎉
