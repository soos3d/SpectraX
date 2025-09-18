#!/usr/bin/env python3
"""Start the surveillance system with configuration file."""

import yaml
import sys
import os
from pathlib import Path
import subprocess

# Set up Python path to include the video-feed directory
project_root = os.path.dirname(os.path.abspath(__file__))
video_feed_dir = os.path.join(project_root, 'video-feed')
if video_feed_dir not in sys.path:
    sys.path.insert(0, video_feed_dir)

def load_config(config_path="surveillance.yml"):
    """Load surveillance configuration."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def main():
    # Load configuration
    config = load_config()
    
    # Build command
    cmd = [
        "python3", "-m", "videofeed.surveillance", "start"
    ]
    
    # Add camera paths
    for camera in config['cameras']:
        cmd.extend(["--path", camera])
    
    # Add network settings
    cmd.extend(["--bind", config['network']['bind']])
    cmd.extend(["--api-port", str(config['network']['api_port'])])
    
    # Add detection settings if enabled
    if config['detection']['enabled']:
        cmd.extend(["--detector"])
        cmd.extend(["--detector-port", str(config['detection']['port'])])
        cmd.extend(["--model", config['detection']['model']])
        cmd.extend(["--confidence", str(config['detection']['confidence'])])
        cmd.extend(["--width", str(config['detection']['resolution']['width'])])
        cmd.extend(["--height", str(config['detection']['resolution']['height'])])
    else:
        cmd.extend(["--no-detector"])
    
    # Add TLS settings if configured
    if config['security']['use_tls']:
        if config['security'].get('tls_key'):
            cmd.extend(["--tls-key", config['security']['tls_key']])
        if config['security'].get('tls_cert'):
            cmd.extend(["--tls-cert", config['security']['tls_cert']])
    
    # Set environment variable for Python path
    env = os.environ.copy()
    env['PYTHONPATH'] = f"{video_feed_dir}:{env.get('PYTHONPATH', '')}"
    
    # Run the command
    print(f"Starting surveillance system...")
    print(f"Command: {' '.join(cmd)}\n")
    
    try:
        subprocess.run(cmd, env=env)
    except KeyboardInterrupt:
        print("\nSurveillance system stopped.")
        sys.exit(0)

if __name__ == "__main__":
    main()
