import os
import secrets
import signal
import socket
import subprocess
import contextlib
from pathlib import Path
import tempfile
from typing import Dict, Optional

import keyring
import typer
import shutil
import yaml

# Application constants
APP_NAME = "video-feed"
KEYCHAIN_SERVICE = f"{APP_NAME}-mediamtx"
DEFAULT_PATH = "video/iphone-1"
MEDIAMTX_BIN = "mediamtx"

app = typer.Typer(add_completion=False)

def _rand_secret() -> str:
    """Return a 32-char, URL-safe random secret."""
    return secrets.token_urlsafe(24)


def _get_secret(label: str) -> str:
    """Fetch or generate a secret stored in the OS keychain."""
    secret = keyring.get_password(KEYCHAIN_SERVICE, label)
    if not secret:
        secret = _rand_secret()
        keyring.set_password(KEYCHAIN_SERVICE, label, secret)
    return secret


def _get_credentials() -> Dict[str, str]:
    """Return a dictionary with publisher and viewer credentials."""
    return {
        "publish_user": "publisher",
        "publish_pass": _get_secret("publisher"),
        "read_user": "viewer",
        "read_pass": _get_secret("viewer"),
    }


def _create_config(bind_ip: str, path: str, creds: Dict[str, str]) -> Dict:
    """Create a MediaMTX configuration dictionary."""
    return {
        "paths": {path: {"source": creds["publish_user"]}},
        "rtspAddress": f"{bind_ip}:8554",
        "rtsp": True,
        "hls": True,
        "authInternalUsers": [
            {"user": creds["publish_user"], "pass": creds["publish_pass"], "ips": [], "permissions": [{"action": "publish", "path": path}]},
            {"user": creds["read_user"],    "pass": creds["read_pass"],    "ips": [], "permissions": [{"action": "read",    "path": path}, {"action": "playback", "path": path}]}
        ],
    }


def _write_cfg(cfg_path: Path, bind_ip: str, path: str) -> Dict[str, str]:
    """Generate mediamtx.yml at cfg_path and return credential dict."""
    creds = _get_credentials()
    config = _create_config(bind_ip, path, creds)
    
    yaml_text = yaml.safe_dump(config)
    cfg_path.write_text(yaml_text)
    os.chmod(cfg_path, 0o600)
    return creds


def _detect_host_ip(prefer_iface: Optional[str] = None) -> str:
    """Return best-guess LAN IP, fallback to localhost."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"


def _print_urls(host: str, path: str, creds: Dict[str, str]) -> None:
    # Base RTSP URL without credentials, suitable for Larix Broadcaster
    base_url = f"rtsp://{host}:8554/{path}"

    typer.secho("\n🎥 RTSP Connection Settings:", fg=typer.colors.GREEN, bold=True)
    typer.echo(f"   URL: {base_url}")
    typer.echo(f"   Username: {creds['publish_user']}")
    typer.echo(f"   Password: {creds['publish_pass']}\n")

    # Viewer URL with embedded credentials for consumption tools
    view_url = f"rtsp://{creds['read_user']}:{creds['read_pass']}@{host}:8554/{path}"
    typer.secho("👀 Viewer URL (embedded credentials):", fg=typer.colors.BLUE, bold=True)
    typer.echo(f"   {view_url}\n")


def _launch_mediamtx(cfg_path: Path) -> subprocess.Popen[bytes]:
    return subprocess.Popen([MEDIAMTX_BIN, str(cfg_path)])


def _load_config_credentials(config_path: Path) -> Dict[str, str]:
    """Load credentials from an existing mediamtx.yml file."""
    try:
        cfg_data = yaml.safe_load(config_path.read_text())
        auth_users = cfg_data["authInternalUsers"]
        pub = next(u for u in auth_users if u.get("user") == "publisher")
        view = next(u for u in auth_users if u.get("user") == "viewer")
        return {
            "publish_user": pub["user"],
            "publish_pass": pub["pass"],
            "read_user": view["user"],
            "read_pass": view["pass"],
        }
    except Exception as e:
        typer.secho(f"Failed to load credentials: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)


def _check_mediamtx_installed() -> None:
    """Check if mediamtx binary is available and exit if not."""
    if shutil.which(MEDIAMTX_BIN) is None:
        typer.secho("Error: 'mediamtx' binary not found.", fg=typer.colors.RED, bold=True)
        raise typer.Exit(1)


@app.command()
def run(
    path: str = typer.Option(DEFAULT_PATH, help="Logical RTSP path to publish/view."),
    bind: str = typer.Option("127.0.0.1", help="Bind IP, use 0.0.0.0 to expose on LAN."),
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="Path to pre-made mediamtx.yml"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show server configuration details."),
) -> None:
    """Start RTSP/HLS micro-server and display connection info."""
    _check_mediamtx_installed()

    # Handle configuration context
    if config:
        cfg_path = config
        creds = _load_config_credentials(cfg_path)
        temp_context = contextlib.nullcontext()
    else:
        # Use TemporaryDirectory to automatically clean up after the server finishes
        temp_context = tempfile.TemporaryDirectory(prefix=f"{APP_NAME}-")

    with temp_context as tmpdir:
        # Create config if needed
        if not config:
            cfg_path = Path(tmpdir) / "mediamtx.yml"
            creds = _write_cfg(cfg_path, bind, path)
        
        # Show configuration if verbose mode is enabled
        if verbose:
            typer.secho("MediaMTX Configuration:", fg=typer.colors.BRIGHT_BLUE, bold=True)
            typer.secho(f"Config file: {cfg_path}", fg=typer.colors.BLUE)
            typer.echo(cfg_path.read_text())
        
        # Launch the server
        server = _launch_mediamtx(cfg_path)
        typer.echo("⏳ Starting MediaMTX ...")
        try:
            server.wait(timeout=2)
        except subprocess.TimeoutExpired:
            pass  # This is expected - server is still running

        # Display connection information
        host_ip = _detect_host_ip() if bind != "127.0.0.1" else "localhost"
        _print_urls(host_ip, path, creds)

        # Wait for user interrupt
        typer.secho("Press Ctrl+C to quit.\n", fg=typer.colors.BRIGHT_BLACK)
        try:
            signal.pause()
        except KeyboardInterrupt:
            typer.echo("\nShutting down ...")
            server.terminate()
            server.wait()


@app.command()
def reset_creds() -> None:
    """Clear stored publisher/viewer credentials."""
    for label in ("publisher", "viewer"):
        try:
            keyring.delete_password(KEYCHAIN_SERVICE, label)
        except keyring.errors.PasswordDeleteError:
            pass
    typer.echo("🔑 Credentials reset; regenerated on next run.")


if __name__ == "__main__":
    app()
