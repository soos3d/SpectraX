"""Utility functions for video-feed."""

import socket
import shutil
import subprocess
import typer
from pathlib import Path
from typing import Dict, List, Optional

from .constants import MEDIAMTX_BIN


def launch_mediamtx(cfg_path: Path) -> subprocess.Popen:
    """Launch the MediaMTX server with the given configuration.
    
    Args:
        cfg_path: Path to mediamtx.yml configuration file
        
    Returns:
        Process object for the running server
    """
    return subprocess.Popen(
        [MEDIAMTX_BIN, cfg_path],
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE
    )


def detect_host_ip(prefer_iface: Optional[str] = None) -> str:
    """Return best-guess LAN IP, fallback to localhost."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"


def check_mediamtx_installed(binary_name: str = MEDIAMTX_BIN) -> None:
    """Check if mediamtx binary is available and exit if not."""
    if shutil.which(binary_name) is None:
        typer.secho(f"Error: '{binary_name}' binary not found.", fg=typer.colors.RED, bold=True)
        typer.echo("Please install MediaMTX from: https://github.com/bluenviron/mediamtx/releases")
        raise typer.Exit(1)


def print_urls(host: str, paths: List[str], creds: Dict[str, str], rtsps: bool = False) -> None:
    """Print connection URLs for RTSP/HLS streams."""
    for i, path in enumerate(paths):
        if i > 0:
            typer.echo("\n" + "-" * 50 + "\n")
            
        typer.secho(f"\n📹 Stream Path: {path}", fg=typer.colors.YELLOW, bold=True)
        base_url = f"rtsp://{host}:8554/{path}"

        if rtsps:
            # For secure publishers like Larix
            publish_url = f"rtsps://{host}:8322/{path}"
            typer.secho("\n📲 Encrypted RTSPS Publishing:", fg=typer.colors.CYAN, bold=True)
            typer.secho("Use in phone apps (e.g. Larix Broadcaster) or other cameras - encrypted", fg=typer.colors.CYAN, bold=True)
            typer.echo(f"  URL: {publish_url}")
            typer.echo(f"  User: {creds['publish_user']}")
            typer.echo(f"  Pass: {creds['publish_pass']}") 
        else:
            # Standard RTSP publishing
            typer.secho("\n📲 RTSP Publishing:", fg=typer.colors.CYAN, bold=True)
            typer.secho("Use in phone apps (e.g. Larix Broadcaster) or other cameras - unencrypted", fg=typer.colors.CYAN, bold=True)
            typer.echo(f"  URL: {base_url}")
            typer.echo(f"  User: {creds['publish_user']}")
            typer.echo(f"  Pass: {creds['publish_pass']}")

        # Show viewing URLs - always the same regardless of rtsps/rtsp for publishing
        typer.secho("\n📺 Encrypted RTSPS Viewing:", fg=typer.colors.GREEN, bold=True)
        typer.secho("Use in OBS or other video platform- encrypted", fg=typer.colors.GREEN, bold=True)
        view_url = f"rtsps://{creds['read_user']}:{creds['read_pass']}@{host}:8322/{path}"
        typer.echo(f"  URL: {view_url}")
        typer.echo(f"  • VLC: File > Open Network > {view_url}")
        typer.echo(f"  • OBS: Souces > + > Media Source > Uncheck local File > add RTSP URL to input >\n {view_url}")

        typer.secho("\n🌐 HLS Viewing (browser):", fg=typer.colors.MAGENTA, bold=True)
        typer.secho("Use in OBS or other video platform- encrypted", fg=typer.colors.MAGENTA, bold=True)
        hls_url = f"http://{host}:8888/{path}/index.m3u8"
        hls_auth_url = f"http://{creds['read_user']}:{creds['read_pass']}@{host}:8888/{path}/index.m3u8"
        typer.echo(f"  URL: {hls_url}")
        typer.echo(f"  Auth: {creds['read_user']} / {creds['read_pass']}")
        typer.echo(f"  Direct URL: {hls_auth_url}")

        # Unencrypted RTSP Connection Settings
        typer.secho("\n🎥 Unencrypted RTSP Connection Settings:", fg=typer.colors.GREEN, bold=True)
        typer.secho("Use in phone apps (e.g. Larix Broadcaster) or other cameras - unencrypted", fg=typer.colors.GREEN, bold=True)
        typer.echo(f"   URL: {base_url}")
        typer.echo(f"   Username: {creds['publish_user']}")
        typer.echo(f"   Password: {creds['publish_pass']}")

        # Viewer URL (embedded credentials)
        typer.secho("\n👀 Viewer URL (embedded credentials):", fg=typer.colors.BLUE, bold=True)
        typer.secho("Use in OBS or other video platform- unencrypted", fg=typer.colors.BLUE, bold=True)
        typer.echo(f"   {view_url}")
