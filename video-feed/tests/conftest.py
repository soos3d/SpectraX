"""Pytest configuration and shared fixtures for tests."""

import os
import sys
import tempfile
import pytest
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_db_path(temp_dir):
    """Provide a temporary database path for testing."""
    return str(temp_dir / "test_recordings.db")


@pytest.fixture
def test_recordings_dir(temp_dir):
    """Provide a temporary recordings directory for testing."""
    recordings_dir = temp_dir / "recordings"
    recordings_dir.mkdir(exist_ok=True)
    return str(recordings_dir)


@pytest.fixture
def sample_config():
    """Provide sample configuration for testing."""
    return {
        'cameras': ['video/test-camera'],
        'network': {
            'bind': '127.0.0.1',
            'api_port': 3333
        },
        'detection': {
            'enabled': True,
            'port': 8080,
            'model': 'yolov8n.pt',
            'confidence': 0.4,
            'resolution': {
                'width': 960,
                'height': 540
            }
        },
        'recording': {
            'enabled': True,
            'min_confidence': 0.5,
            'pre_buffer_seconds': 5,
            'post_buffer_seconds': 5,
            'max_storage_gb': 1.0,
            'recordings_dir': '~/test-recordings',
            'record_objects': []
        },
        'security': {
            'use_tls': False,
            'tls_key': '',
            'tls_cert': ''
        }
    }
