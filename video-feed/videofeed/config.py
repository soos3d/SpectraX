"""Configuration management for video-feed."""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional
import typer


def create_config(
    bind_ip: str,
    paths: List[str],
    creds: Dict[str, str],
    tls_key: Optional[str] = None,
    tls_cert: Optional[str] = None
) -> Dict:
    """Create a MediaMTX configuration dictionary with optional TLS."""
    # Create paths configuration
    paths_config = {}
    for path in paths:
        paths_config[path] = {
            "source": creds["publish_user"]
        }
    
    # Create publisher permissions
    publisher_permissions = []
    for path in paths:
        publisher_permissions.append({"action": "publish", "path": path})
    
    # Create viewer permissions
    viewer_permissions = []
    for path in paths:
        viewer_permissions.append({"action": "read", "path": path})
        viewer_permissions.append({"action": "playback", "path": path})
    
    config = {
        "paths": paths_config,
        "rtspAddress": f"{bind_ip}:8554",
        "rtsp": True,
        "hls": True,
        "rtspTransports": ["tcp"],
        "authInternalUsers": [
            {
                "user": creds["publish_user"],
                "pass": creds["publish_pass"],
                "ips": [],
                "permissions": publisher_permissions
            },
            {
                "user": creds["read_user"],
                "pass": creds["read_pass"],
                "ips": [],
                "permissions": viewer_permissions
            }
        ],
    }

    if tls_key and tls_cert:
        config["rtspEncryption"] = "optional"
        config["rtspServerKey"] = tls_key
        config["rtspServerCert"] = tls_cert

    return config


def write_cfg(cfg_path: Path, bind_ip: str, paths: List[str], creds: Dict[str, str], 
             tls_key: Optional[str] = None, tls_cert: Optional[str] = None) -> None:
    """Generate mediamtx.yml at cfg_path."""
    config = create_config(bind_ip, paths, creds, tls_key, tls_cert)
    
    yaml_text = yaml.safe_dump(config)
    cfg_path.write_text(yaml_text)
    os.chmod(cfg_path, 0o600)


def load_config_paths(config_path: Path) -> List[str]:
    """Load paths from an existing mediamtx.yml file.
    
    Args:
        config_path: Path to existing mediamtx.yml file
        
    Returns:
        List of RTSP path strings
        
    Raises:
        typer.Exit: If paths cannot be loaded
    """
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
            
        paths_config = config.get("paths", {})
        if not paths_config:
            typer.secho("No paths found in configuration", fg=typer.colors.RED)
            raise typer.Exit(1)
            
        return list(paths_config.keys())
    except Exception as e:
        typer.secho(f"Failed to load paths: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)
