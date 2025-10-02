"""Credential management functionality for video-feed."""

import secrets
import keyring
from typing import Dict

from .constants import APP_NAME, KEYCHAIN_SERVICE


def rand_secret() -> str:
    """Return a 32-char, URL-safe random secret."""
    return secrets.token_urlsafe(24)


def get_secret(label: str) -> str:
    """Fetch or generate a secret stored in the OS keychain."""
    secret = keyring.get_password(KEYCHAIN_SERVICE, label)
    if not secret:
        secret = rand_secret()
        keyring.set_password(KEYCHAIN_SERVICE, label, secret)
    return secret


def get_credentials() -> Dict[str, str]:
    """Return a dictionary with publisher and viewer credentials."""
    return {
        "publish_user": "publisher",
        "publish_pass": get_secret("publisher"),
        "read_user": "viewer",
        "read_pass": get_secret("viewer"),
    }


def reset_creds() -> None:
    """Clear stored publisher/viewer credentials."""
    for label in ("publisher", "viewer"):
        try:
            keyring.delete_password(KEYCHAIN_SERVICE, label)
        except keyring.errors.PasswordDeleteError:
            pass


def load_config_credentials(config_path) -> Dict[str, str]:
    """Load credentials from an existing mediamtx.yml file.
    
    Args:
        config_path: Path to existing mediamtx.yml file
        
    Returns:
        Dictionary of credentials
        
    Raises:
        typer.Exit: If configuration cannot be loaded
    """
    import yaml
    import typer
    
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
            
        creds = {}
        if "authInternalUsers" in config:
            for user_info in config["authInternalUsers"]:
                if user_info.get("permissions"):
                    for perm in user_info["permissions"]:
                        if perm.get("action") == "publish":
                            creds["publish_user"] = user_info["user"]
                            creds["publish_pass"] = user_info["pass"]
                        elif perm.get("action") == "read":
                            creds["read_user"] = user_info["user"]
                            creds["read_pass"] = user_info["pass"]
        
        # Validate we have all required credentials
        required_keys = ["publish_user", "publish_pass", "read_user", "read_pass"]
        if not all(k in creds for k in required_keys):
            typer.secho(f"Missing required credentials in config", fg=typer.colors.RED)
            raise typer.Exit(1)
            
        return creds
    except Exception as e:
        typer.secho(f"Failed to load credentials: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)
