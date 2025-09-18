"""Unified surveillance system launcher."""

import asyncio
import signal
import subprocess
import threading
import time
import sys
import os
import json
from pathlib import Path
from typing import List, Optional, Dict
import typer
import yaml
from http.server import HTTPServer, BaseHTTPRequestHandler

# Add the parent directory to sys.path to make videofeed importable
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Now import from videofeed
from videofeed.credentials import get_credentials, load_config_credentials
from videofeed.config import write_cfg, load_config_paths
from videofeed.network import detect_host_ip, check_mediamtx_installed
from videofeed.server import launch_mediamtx
from videofeed.visualizer import start_visualizer

app = typer.Typer(add_completion=False)

class PathsAPIHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler for paths API."""
    
    def __init__(self, *args, paths=None, **kwargs):
        self.paths = paths
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests."""
        if self.path == "/paths":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            
            data = {"count": len(self.paths), "paths": self.paths}
            self.wfile.write(json.dumps(data).encode())
        else:
            self.send_response(404)
            self.end_headers()


class SurveillanceSystem:
    """Unified surveillance system manager."""
    
    def __init__(self):
        self.mediamtx_process = None
        self.detector_thread = None
        self.api_server = None
        self.api_thread = None
        self.running = False
        self.config = {}
        
    def start_streaming_server(
        self,
        paths: List[str],
        bind: str,
        config_path: Optional[Path],
        tls_key: Optional[Path],
        tls_cert: Optional[Path],
        api_port: Optional[int]
    ) -> Dict:
        """Start the MediaMTX streaming server."""
        check_mediamtx_installed("mediamtx")
        
        # Use default TLS paths if not provided
        default_tls_key = Path(__file__).parent.parent / "server.key"
        default_tls_cert = Path(__file__).parent.parent / "server.crt"
        
        if not tls_key and default_tls_key.exists():
            tls_key = default_tls_key
        if not tls_cert and default_tls_cert.exists():
            tls_cert = default_tls_cert
            
        # Create configuration
        if config_path and config_path.exists():
            creds = load_config_credentials(config_path)
            config_paths = load_config_paths(config_path)
        else:
            import tempfile
            self.temp_dir = tempfile.mkdtemp(prefix="surveillance-")
            config_path = Path(self.temp_dir) / "mediamtx.yml"
            creds = get_credentials()
            write_cfg(
                config_path, 
                bind, 
                paths, 
                creds,
                tls_key=str(tls_key) if tls_key else None,
                tls_cert=str(tls_cert) if tls_cert else None
            )
            config_paths = paths
            
        # Launch MediaMTX
        self.mediamtx_process = launch_mediamtx(config_path)
        typer.echo("⏳ Starting MediaMTX streaming server...")
        
        # Wait for server to start
        try:
            self.mediamtx_process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            pass  # Expected: server is running
            
        # Store configuration
        self.config = {
            "creds": creds,
            "paths": config_paths,
            "host_ip": detect_host_ip(),
            "api_port": api_port,
            "use_rtsps": tls_key is not None and tls_cert is not None
        }
        
        # Start API server if port is specified
        if api_port:
            self.start_api_server(api_port)
        
        return self.config
        
    def start_api_server(self, port: int):
        """Start the API server for path discovery."""
        # Create a handler class with access to paths
        paths = self.config["paths"]
        
        def handler_factory(*args, **kwargs):
            return PathsAPIHandler(*args, paths=paths, **kwargs)
        
        # Start the server in a separate thread
        self.api_server = HTTPServer(("0.0.0.0", port), handler_factory)
        self.api_thread = threading.Thread(target=self.api_server.serve_forever, daemon=True)
        self.api_thread.start()
        
        typer.echo(f"🔍 API server started on port {port}")
        typer.echo(f"  • Local: http://127.0.0.1:{port}/paths")
        typer.echo(f"  • Network: http://{self.config['host_ip']}:{port}/paths")
        
    def start_detector(
        self,
        host: str,
        port: int,
        model: str,
        confidence: float,
        resolution: tuple
    ):
        """Start the object detection service in a separate thread."""
        def run_detector():
            # Build RTSP URLs from paths
            rtsp_urls = []
            for path in self.config["paths"]:
                if self.config["use_rtsps"]:
                    url = f"rtsps://{self.config['creds']['read_user']}:{self.config['creds']['read_pass']}@{self.config['host_ip']}:8322/{path}"
                else:
                    url = f"rtsp://{self.config['creds']['read_user']}:{self.config['creds']['read_pass']}@{self.config['host_ip']}:8554/{path}"
                rtsp_urls.append(url)
                
            typer.echo(f"🎯 Starting object detection for {len(rtsp_urls)} streams...")
            
            # Import here to avoid circular imports
            from videofeed.detector import DetectorManager
            from videofeed.visualizer import app, set_detector_manager
            import uvicorn
            
            try:
                # Initialize detector manager
                detector_manager = DetectorManager()
                
                # Add detectors for each URL
                for url in rtsp_urls:
                    detector_manager.add_detector(
                        source_url=url,
                        model_path=model,
                        confidence=confidence,
                        resolution=resolution
                    )
                
                # Set the detector manager in the visualizer module
                set_detector_manager(detector_manager)
                
                # Start FastAPI server without signal handlers
                config = uvicorn.Config(
                    app=app,
                    host=host,
                    port=port,
                    log_level="info"
                )
                
                server = uvicorn.Server(config)
                server.run()
            except Exception as e:
                typer.echo(f"Error in detector: {e}")
            
        self.detector_thread = threading.Thread(target=run_detector, daemon=True)
        self.detector_thread.start()
        
    def print_status(self):
        """Print system status and connection information."""
        typer.echo("\n" + "="*60)
        typer.secho("🎥 SURVEILLANCE SYSTEM ACTIVE", fg=typer.colors.GREEN, bold=True)
        typer.echo("="*60 + "\n")
        
        # Print stream paths
        typer.secho("📹 Active Streams:", fg=typer.colors.YELLOW, bold=True)
        for path in self.config["paths"]:
            typer.echo(f"  • {path}")
            
        typer.echo()
        
        # Print publisher info (for cameras)
        typer.secho("📱 Camera Connection (Publisher):", fg=typer.colors.CYAN, bold=True)
        if self.config["use_rtsps"]:
            typer.echo(f"  RTSPS URL: rtsps://{self.config['host_ip']}:8322/[stream-path]")
        else:
            typer.echo(f"  RTSP URL: rtsp://{self.config['host_ip']}:8554/[stream-path]")
        typer.echo(f"  Username: {self.config['creds']['publish_user']}")
        typer.echo(f"  Password: {self.config['creds']['publish_pass']}")
        
        typer.echo()
        
        # Print viewer info
        typer.secho("🖥️  Web Interfaces:", fg=typer.colors.GREEN, bold=True)
        typer.echo(f"  Object Detection: http://{self.config['host_ip']}:8080")
        typer.echo(f"  HLS Streams: http://{self.config['host_ip']}:8888/[stream-path]/index.m3u8")
        if self.config.get("api_port"):
            typer.echo(f"  Paths API: http://{self.config['host_ip']}:{self.config['api_port']}/paths")
            
        typer.echo()
        
        # Print secure viewer URLs
        typer.secho("🔐 Secure Viewer URLs:", fg=typer.colors.MAGENTA, bold=True)
        for path in self.config["paths"]:
            if self.config["use_rtsps"]:
                url = f"rtsps://{self.config['creds']['read_user']}:{self.config['creds']['read_pass']}@{self.config['host_ip']}:8322/{path}"
            else:
                url = f"rtsp://{self.config['creds']['read_user']}:{self.config['creds']['read_pass']}@{self.config['host_ip']}:8554/{path}"
            typer.echo(f"  • {path}: {url}")
            
        typer.echo("\n" + "="*60)
        typer.secho("Press Ctrl+C to stop the surveillance system", fg=typer.colors.BRIGHT_BLACK)
        typer.echo("="*60 + "\n")
        
    def shutdown(self):
        """Shutdown all services."""
        typer.echo("\n🛑 Shutting down surveillance system...")
        
        if self.mediamtx_process:
            self.mediamtx_process.terminate()
            self.mediamtx_process.wait()
            typer.echo("  ✓ Streaming server stopped")
            
        # Detector thread will stop automatically as it's daemon
        # We don't need to join it since it's a daemon thread
        typer.echo("  ✓ Object detection stopped")
        
        # Shutdown API server if running
        if self.api_server:
            self.api_server.shutdown()
            typer.echo("  ✓ API server stopped")
        
        # Clean up temp directory if it exists
        if hasattr(self, 'temp_dir'):
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            
        typer.echo("👋 Surveillance system stopped\n")


@app.command()
def start(
    paths: List[str] = typer.Option(
        ["video/front-door", "video/backyard", "video/garage"],
        "--path", "-p",
        help="Camera stream paths"
    ),
    bind: str = typer.Option("0.0.0.0", help="Bind IP address"),
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="Custom config file"),
    detector: bool = typer.Option(True, "--detector/--no-detector", help="Enable object detection"),
    detector_port: int = typer.Option(8080, "--detector-port", help="Object detection web port"),
    model: str = typer.Option("yolov8n.pt", "--model", "-m", help="YOLO model"),
    confidence: float = typer.Option(0.4, "--confidence", help="Detection confidence"),
    width: int = typer.Option(960, "--width", help="Video width"),
    height: int = typer.Option(540, "--height", help="Video height"),
    api_port: Optional[int] = typer.Option(3333, "--api-port", help="API port for paths"),
    tls_key: Optional[Path] = typer.Option(None, help="TLS key path"),
    tls_cert: Optional[Path] = typer.Option(None, help="TLS certificate path"),
):
    """Start the unified surveillance system with streaming and object detection."""
    
    system = SurveillanceSystem()
    
    try:
        # Start streaming server
        system.start_streaming_server(
            paths=paths,
            bind=bind,
            config_path=config,
            tls_key=tls_key,
            tls_cert=tls_cert,
            api_port=api_port
        )
        
        # Start detector if enabled
        if detector:
            time.sleep(1)  # Give server a moment to stabilize
            system.start_detector(
                host="0.0.0.0",
                port=detector_port,
                model=model,
                confidence=confidence,
                resolution=(width, height)
            )
            time.sleep(2)  # Give detector time to initialize
            
        # Print status
        system.print_status()
        
        # Wait for interrupt
        signal.pause()
        
    except KeyboardInterrupt:
        pass
    finally:
        system.shutdown()


@app.command()
def quick(
    cameras: int = typer.Option(1, "--cameras", "-n", help="Number of cameras"),
    detector: bool = typer.Option(True, "--detector/--no-detector", help="Enable object detection"),
):
    """Quick start with default settings for N cameras."""
    
    # Generate camera paths
    paths = [f"video/camera-{i+1}" for i in range(cameras)]
    
    typer.secho(f"🚀 Quick starting surveillance with {cameras} camera(s)...", fg=typer.colors.GREEN, bold=True)
    
    # Call start with defaults
    start(
        paths=paths,
        bind="0.0.0.0",
        detector=detector,
        detector_port=8080,
        api_port=3333
    )


if __name__ == "__main__":
    app()
