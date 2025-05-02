"""CLI interface for video-feed."""

import os
import signal
import subprocess
import contextlib
import tempfile
from pathlib import Path
from typing import List, Optional

import typer

from videofeed.credentials import get_credentials, reset_creds, load_config_credentials
from videofeed.config import write_cfg, load_config_paths
from videofeed.network import detect_host_ip, print_urls, check_mediamtx_installed
from videofeed.server import launch_mediamtx

# Application constants
APP_NAME = "video-feed"
DEFAULT_PATHS = ["video/iphone-1"]
MEDIAMTX_BIN = "mediamtx"

app = typer.Typer(add_completion=False)


@app.command()
def run(
    paths: List[str] = typer.Option(DEFAULT_PATHS, "--path", "-p", help="Logical RTSP path(s) to publish/view. Can be specified multiple times."),
    bind: str = typer.Option("127.0.0.1", help="Bind IP, use 0.0.0.0 to expose on LAN."),
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="Path to pre-made mediamtx.yml"),
    tls_key: Optional[Path] = typer.Option(None, help="Path to TLS private key for RTSPS."),
    tls_cert: Optional[Path] = typer.Option(None, help="Path to TLS certificate for RTSPS."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show server configuration details."),
) -> None:
    """Start RTSP/HLS micro-server and display connection info."""
    check_mediamtx_installed(MEDIAMTX_BIN)

    # Use default TLS paths if not provided
    default_tls_key = Path(__file__).parent.parent / "server.key"
    default_tls_cert = Path(__file__).parent.parent / "server.crt"

    if not tls_key and default_tls_key.exists():
        tls_key = default_tls_key
    if not tls_cert and default_tls_cert.exists():
        tls_cert = default_tls_cert

    tls_key_path = None
    tls_cert_path = None
    use_rtsps = False

    # Validate TLS files
    if tls_key and tls_cert:
        if not tls_key.exists():
            typer.secho(f"TLS key not found: {tls_key}", fg=typer.colors.RED)
            raise typer.Exit(1)
        if not tls_cert.exists():
            typer.secho(f"TLS cert not found: {tls_cert}", fg=typer.colors.RED)
            raise typer.Exit(1)
        tls_key_path = str(tls_key)
        tls_cert_path = str(tls_cert)
        use_rtsps = True
    elif tls_key or tls_cert:
        typer.secho("Error: both --tls-key and --tls-cert must be provided for RTSPS.", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Configuration context
    if config:
        cfg_path = config
        creds = load_config_credentials(cfg_path)
        config_paths = load_config_paths(cfg_path)
        temp_context = contextlib.nullcontext()
    else:
        temp_context = tempfile.TemporaryDirectory(prefix=f"{APP_NAME}-")

    with temp_context as tmpdir:
        if not config:
            cfg_path = Path(tmpdir) / "mediamtx.yml"
            creds = get_credentials()
            write_cfg(cfg_path, bind, paths, creds, tls_key=tls_key_path, tls_cert=tls_cert_path)
            config_paths = paths

        if verbose:
            typer.secho("MediaMTX Configuration:", fg=typer.colors.BRIGHT_BLUE, bold=True)
            typer.secho(f"Config file: {cfg_path}", fg=typer.colors.BLUE)
            typer.echo(cfg_path.read_text())

        server = launch_mediamtx(cfg_path)
        typer.echo("⏳ Starting MediaMTX ...")
        try:
            server.wait(timeout=2)
        except subprocess.TimeoutExpired:
            pass  # Expected: server is running

        host_ip = detect_host_ip() if bind != "127.0.0.1" else "localhost"
        print_urls(host_ip, config_paths, creds, rtsps=use_rtsps)

        typer.secho("Press Ctrl+C to quit.\n", fg=typer.colors.BRIGHT_BLACK)
        try:
            signal.pause()
        except KeyboardInterrupt:
            typer.echo("\nShutting down ...")
            server.terminate()
            server.wait()


@app.command()
def reset():
    """Clear stored publisher/viewer credentials."""
    reset_creds()
    typer.echo("🔑 Credentials reset; regenerated on next run.")
