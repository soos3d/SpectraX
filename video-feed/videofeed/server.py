"""Server management for video-feed."""

import subprocess
from pathlib import Path


def launch_mediamtx(cfg_path: Path) -> subprocess.Popen:
    """Launch the MediaMTX server with the given configuration.
    
    Args:
        cfg_path: Path to mediamtx.yml configuration file
        
    Returns:
        Process object for the running server
    """
    return subprocess.Popen(
        ["mediamtx", cfg_path],
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE
    )
