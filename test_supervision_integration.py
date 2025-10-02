#!/usr/bin/env python3
"""Test script to verify Supervision integration."""

import sys
import os

# Add video-feed to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'video-feed'))

def test_imports():
    """Test that all imports work correctly."""
    print("Testing imports...")
    try:
        import supervision as sv
        print("✅ Supervision imported successfully")
        print(f"   Version: {sv.__version__ if hasattr(sv, '__version__') else 'unknown'}")
        
        from videofeed.detector import RTSPObjectDetector, DetectorManager
        print("✅ Detector modules imported successfully")
        
        # Test that Supervision components are available
        _ = sv.Detections
        _ = sv.BoxAnnotator
        _ = sv.LabelAnnotator
        _ = sv.ByteTrack
        print("✅ Supervision components accessible")
        
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_annotator_initialization():
    """Test that annotators can be initialized."""
    print("\nTesting annotator initialization...")
    try:
        import supervision as sv
        
        box_annotator = sv.BoxAnnotator(thickness=2, color=sv.Color.GREEN)
        print("✅ BoxAnnotator initialized")
        
        label_annotator = sv.LabelAnnotator(
            text_position=sv.Position.TOP_LEFT,
            text_thickness=1,
            text_scale=0.5
        )
        print("✅ LabelAnnotator initialized")
        
        return True
    except Exception as e:
        print(f"❌ Annotator initialization failed: {e}")
        return False

def test_detector_class():
    """Test that RTSPObjectDetector class can be instantiated."""
    print("\nTesting RTSPObjectDetector class...")
    try:
        from videofeed.detector import RTSPObjectDetector
        
        # Create a detector instance (without starting it)
        detector = RTSPObjectDetector(
            source_url="rtsp://test:test@localhost/test",
            model_path="yolov8n.pt",
            confidence=0.5,
            resolution=(640, 480)
        )
        
        # Check that Supervision annotators are initialized
        assert hasattr(detector, 'box_annotator'), "Missing box_annotator"
        assert hasattr(detector, 'label_annotator'), "Missing label_annotator"
        
        print("✅ RTSPObjectDetector instantiated with Supervision annotators")
        return True
    except Exception as e:
        print(f"❌ Detector class test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("Supervision Integration Test Suite")
    print("=" * 60)
    
    results = []
    
    results.append(("Imports", test_imports()))
    results.append(("Annotator Initialization", test_annotator_initialization()))
    results.append(("Detector Class", test_detector_class()))
    
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(result[1] for result in results)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All tests passed! Supervision integration successful.")
        print("\nNext steps:")
        print("1. Install supervision: pip install supervision==0.24.0")
        print("2. Test with actual video stream")
        print("3. Proceed to Phase 2: Add ByteTrack tracking")
    else:
        print("⚠️  Some tests failed. Please review the errors above.")
    print("=" * 60)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
