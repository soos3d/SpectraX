# Bug Fix: Detection Filtering Issue

**Date:** 2025-10-02  
**Issue:** System only detecting persons instead of all objects  
**Status:** ✅ Fixed

---

## Problem

After implementing the unified configuration system, the detector was only detecting objects listed in `record_objects` (person, car, dog, cat) instead of detecting all objects.

### Root Cause

In `detector_config.py`, the logic was:
```python
filter_classes = filter_config.get('classes', [])
# If no filter classes specified, use record_objects as fallback
if not filter_classes:
    filter_classes = recording_config.get('record_objects', [])
```

This meant that even with `detection.filters.classes: []` (which should mean "detect all"), the system would fall back to using `record_objects`, limiting detection.

---

## Solution

**Fixed in:** `video-feed/videofeed/detector_config.py`

**Changed:**
```python
# Get filter settings
filter_config = detection_config.get('filters', {})
filter_classes = filter_config.get('classes', [])
# NOTE: Empty list means detect ALL objects
# Only use record_objects if explicitly set in filters.classes
# Do NOT use record_objects as fallback - that would limit detection
```

**Key insight:** Empty list `[]` should mean "no filtering" (detect everything), not "use fallback".

---

## Configuration Clarification

Updated `surveillance.yml` to make the distinction clear:

### **Detection Filtering** (what to detect)
```yaml
detection:
  filters:
    classes: []  # Empty = detect ALL objects
```

### **Recording Filtering** (what to record)
```yaml
recording:
  record_objects: ["person", "car"]  # Only record these
```

### **Two Separate Concepts:**

1. **`detection.filters.classes`** - Controls what the AI detects/displays
   - `[]` = Detect everything (default)
   - `["person"]` = Only detect people
   - `["person", "car"]` = Only detect people and cars

2. **`recording.record_objects`** - Controls what triggers recording
   - `[]` = Record all detections
   - `["person"]` = Only record when people detected
   - Independent of what's being detected

---

## Use Cases

### **Detect Everything, Record Specific Objects**
```yaml
detection:
  filters:
    classes: []  # Detect all objects

recording:
  record_objects: ["person"]  # But only record people
```
**Result:** See all objects on screen, only save recordings when people appear.

---

### **Detect and Record Specific Objects**
```yaml
detection:
  filters:
    classes: ["person", "car"]  # Only detect these

recording:
  record_objects: ["person"]  # Only record people
```
**Result:** Only see people and cars, only save recordings when people appear.

---

### **Detect and Record Everything**
```yaml
detection:
  filters:
    classes: []  # Detect all

recording:
  record_objects: []  # Record all
```
**Result:** See everything, record everything.

---

## Testing

After fix, system should:
- ✅ Detect all object types (person, car, dog, cat, bird, etc.)
- ✅ Display all detections with bounding boxes
- ✅ Only record when `record_objects` match (if recording enabled)

**Test command:**
```bash
./surveillance.sh config
```

Point camera at various objects and verify all are detected.

---

## Files Modified

- ✅ `video-feed/videofeed/detector_config.py` - Removed fallback logic
- ✅ `surveillance.yml` - Added clarifying comments
- ✅ `docs/BUGFIX_DETECTION_FILTERING.md` - This document

---

## Lesson Learned

**Empty list semantics matter:**
- In filtering contexts, `[]` typically means "no filter" (allow all)
- Don't use fallbacks that change this semantic meaning
- Always document the difference between "detect" and "record"
