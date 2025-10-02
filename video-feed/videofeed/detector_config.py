"""Configuration dataclasses for detector module."""

from dataclasses import dataclass, field
from typing import Tuple, List, Optional, Dict, Any
import supervision as sv


# Color mapping for string-based color configuration
COLOR_MAP = {
    "green": sv.Color.GREEN,
    "red": sv.Color.RED,
    "blue": sv.Color.BLUE,
    "yellow": sv.Color.YELLOW,
    "white": sv.Color.WHITE,
    "black": sv.Color.BLACK,
    "roboflow": sv.Color.ROBOFLOW,
}

# Position mapping for string-based position configuration
POSITION_MAP = {
    "top_left": sv.Position.TOP_LEFT,
    "top_center": sv.Position.TOP_CENTER,
    "top_right": sv.Position.TOP_RIGHT,
    "center_left": sv.Position.CENTER_LEFT,
    "center": sv.Position.CENTER,
    "center_right": sv.Position.CENTER_RIGHT,
    "bottom_left": sv.Position.BOTTOM_LEFT,
    "bottom_center": sv.Position.BOTTOM_CENTER,
    "bottom_right": sv.Position.BOTTOM_RIGHT,
}


@dataclass
class AnnotatorConfig:
    """Configuration for Supervision annotators."""
    
    # Box annotator settings
    box_thickness: int = 2
    box_color: sv.Color = sv.Color.GREEN
    
    # Label annotator settings
    label_text_scale: float = 0.5
    label_text_thickness: int = 1
    label_text_padding: int = 10
    label_text_position: sv.Position = sv.Position.TOP_LEFT
    
    # Border settings (optional)
    label_border_radius: int = 0
    
    @classmethod
    def from_appearance_config(cls, appearance_config: Dict[str, Any]) -> 'AnnotatorConfig':
        """Create AnnotatorConfig from appearance section of surveillance.yml.
        
        Args:
            appearance_config: Dictionary from surveillance.yml appearance section
            
        Returns:
            AnnotatorConfig instance
        """
        box_config = appearance_config.get('box', {})
        label_config = appearance_config.get('label', {})
        
        # Parse box color from string
        box_color_str = box_config.get('color', 'green').lower()
        box_color = COLOR_MAP.get(box_color_str, sv.Color.GREEN)
        
        # Parse label position from string
        position_str = label_config.get('position', 'top_left').lower()
        label_position = POSITION_MAP.get(position_str, sv.Position.TOP_LEFT)
        
        return cls(
            box_thickness=box_config.get('thickness', 2),
            box_color=box_color,
            label_text_scale=label_config.get('text_scale', 0.5),
            label_text_thickness=label_config.get('text_thickness', 1),
            label_text_padding=label_config.get('text_padding', 10),
            label_text_position=label_position,
            label_border_radius=label_config.get('border_radius', 0)
        )


@dataclass
class DetectorConfig:
    """Configuration for RTSP object detector."""
    
    # Model settings
    model_path: str = "yolov8n.pt"
    confidence: float = 0.5
    
    # Stream settings
    resolution: Tuple[int, int] = (960, 540)
    buffer_size: int = 10
    reconnect_interval: int = 5
    
    # Filtering settings
    min_detection_area: Optional[int] = None  # Minimum area in pixels
    max_detection_area: Optional[int] = None  # Maximum area in pixels
    filter_classes: List[str] = field(default_factory=list)  # Only detect these classes (empty = all)
    
    # Annotator configuration
    annotator: AnnotatorConfig = field(default_factory=AnnotatorConfig)
    
    @classmethod
    def from_surveillance_config(cls, surveillance_config) -> 'DetectorConfig':
        """Create DetectorConfig from SurveillanceConfig.
        
        Args:
            surveillance_config: SurveillanceConfig instance
            
        Returns:
            DetectorConfig instance
        """
        detection_config = surveillance_config.get_detection_config()
        recording_config = surveillance_config.get_recording_config()
        
        # Get stream settings
        stream_config = detection_config.get('stream', {})
        
        # Get filter settings
        filter_config = detection_config.get('filters', {})
        filter_classes = filter_config.get('classes', [])
        # NOTE: Empty list means detect ALL objects
        # Only use record_objects if explicitly set in filters.classes
        # Do NOT use record_objects as fallback - that would limit detection
        
        # Get appearance settings
        appearance_config = surveillance_config.config_data.get('appearance', {})
        annotator_config = AnnotatorConfig.from_appearance_config(appearance_config)
        
        return cls(
            model_path=detection_config.get('model', 'yolov8n.pt'),
            confidence=detection_config.get('confidence', 0.4),
            resolution=tuple(detection_config.get('resolution', {}).values()) or (960, 540),
            buffer_size=stream_config.get('buffer_size', 10),
            reconnect_interval=stream_config.get('reconnect_interval', 5),
            filter_classes=filter_classes,
            min_detection_area=filter_config.get('min_area'),
            max_detection_area=filter_config.get('max_area'),
            annotator=annotator_config
        )
    
    def create_box_annotator(self) -> sv.BoxAnnotator:
        """Create configured BoxAnnotator instance."""
        return sv.BoxAnnotator(
            thickness=self.annotator.box_thickness,
            color=self.annotator.box_color
        )
    
    def create_label_annotator(self) -> sv.LabelAnnotator:
        """Create configured LabelAnnotator instance."""
        return sv.LabelAnnotator(
            text_position=self.annotator.label_text_position,
            text_thickness=self.annotator.label_text_thickness,
            text_scale=self.annotator.label_text_scale,
            text_padding=self.annotator.label_text_padding,
            border_radius=self.annotator.label_border_radius
        )
