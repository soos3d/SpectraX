# Security Improvements Implementation Guide

This document provides **ready-to-implement** code for securing your SentriX surveillance system.

---

## Table of Contents

1. [Quick Security Fixes (30 minutes)](#quick-security-fixes)
2. [Authentication Middleware (1 hour)](#authentication-middleware)
3. [CORS Policy Fix (15 minutes)](#cors-policy-fix)
4. [Path Traversal Fix (15 minutes)](#path-traversal-fix)
5. [Rate Limiting (30 minutes)](#rate-limiting)
6. [HTTPS Support (30 minutes)](#https-support)
7. [File Encryption (2 hours)](#file-encryption)
8. [Complete Security Module](#complete-security-module)

---

## Updates Status

### Completed (2025-10-01)

✅ **Secured .gitignore** - Added certificates, recordings, logs
✅ **Changed default bind to localhost** - Restricted network exposure
✅ **Fixed CORS policy** - Restricted to specific origins only
✅ **Fixed path traversal vulnerability** - Added path validation and file type whitelist

### In Progress

⏳ Authentication middleware for all endpoints
⏳ Rate limiting on auth endpoint

### Pending

⏸️ HTTPS support for web dashboard
⏸️ File encryption at rest
⏸️ Session-based authentication
⏸️ Credential rotation mechanism

## Quick Security Fixes

### 1. Update Default Configuration

**File: `surveillance.yml`**
```yaml
# Network settings - SECURE DEFAULTS
network:
  bind: "127.0.0.1"  # ✅ Changed from 0.0.0.0 - localhost only
  api_port: 3333

# Security settings
security:
  use_tls: true
  tls_key: ""
  tls_cert: ""
  # New settings
  require_auth: true  # Require authentication for all endpoints
  session_timeout: 3600  # 1 hour
  max_login_attempts: 5
  lockout_duration: 300  # 5 minutes
```

### 2. Add to `.gitignore`

**File: `.gitignore`**
```
# Security-sensitive files
server.key
server.crt
*.pem
*.p12
*.pfx

# Recordings and database
video-feed-recordings/
*.db
*.db-journal

# Logs
audit.log
security.log
*.log

# Environment files
.env
.env.local
secrets/
```

### 3. Set File Permissions on Startup

**File: `video-feed/videofeed/recorder.py`** (add to `__init__`)
```python
def __init__(self, ...):
    # ... existing code ...
    
    # Set secure permissions
    self._set_secure_permissions()

def _set_secure_permissions(self):
    """Set secure file permissions on recordings directory and database."""
    import stat
    
    # Recordings directory: owner only (0700)
    os.chmod(self.recordings_dir, stat.S_IRWXU)
    
    # Database file: owner read/write only (0600)
    if os.path.exists(self.db_path):
        os.chmod(self.db_path, stat.S_IRUSR | stat.S_IWUSR)
    
    logger.info("Set secure file permissions on recordings directory and database")
```

---

## Authentication Middleware

Create a new security module for centralized authentication.

### Create Security Module

**File: `video-feed/videofeed/security.py`** (NEW FILE)
```python
"""Security and authentication for video-feed."""

import secrets
import time
import logging
from typing import Optional, Dict
from functools import wraps

from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from videofeed.credentials import get_credentials

logger = logging.getLogger('security')

# HTTP Basic Auth
security = HTTPBasic()

# Session store (in-memory, use Redis for production)
sessions: Dict[str, Dict] = {}

# Rate limiting store
rate_limit_store: Dict[str, list] = {}

# Failed login attempts
failed_attempts: Dict[str, Dict] = {}


class SecurityConfig:
    """Security configuration."""
    SESSION_TIMEOUT = 3600  # 1 hour
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION = 300  # 5 minutes
    RATE_LIMIT_WINDOW = 60  # 1 minute
    RATE_LIMIT_MAX_REQUESTS = 10


def check_rate_limit(client_ip: str, endpoint: str, max_requests: int = 10, window: int = 60) -> bool:
    """Check if client has exceeded rate limit.
    
    Args:
        client_ip: Client IP address
        endpoint: Endpoint being accessed
        max_requests: Maximum requests allowed in window
        window: Time window in seconds
    
    Returns:
        True if within rate limit, False if exceeded
    """
    key = f"{client_ip}:{endpoint}"
    current_time = time.time()
    
    if key not in rate_limit_store:
        rate_limit_store[key] = []
    
    # Remove old entries
    rate_limit_store[key] = [
        timestamp for timestamp in rate_limit_store[key]
        if current_time - timestamp < window
    ]
    
    # Check limit
    if len(rate_limit_store[key]) >= max_requests:
        return False
    
    # Add current request
    rate_limit_store[key].append(current_time)
    return True


def check_account_lockout(username: str) -> bool:
    """Check if account is locked due to failed login attempts.
    
    Args:
        username: Username to check
    
    Returns:
        True if account is locked, False otherwise
    """
    if username not in failed_attempts:
        return False
    
    attempts = failed_attempts[username]
    current_time = time.time()
    
    # Check if lockout has expired
    if current_time - attempts['last_attempt'] > SecurityConfig.LOCKOUT_DURATION:
        # Reset attempts
        del failed_attempts[username]
        return False
    
    # Check if locked
    return attempts['count'] >= SecurityConfig.MAX_LOGIN_ATTEMPTS


def record_failed_login(username: str):
    """Record a failed login attempt.
    
    Args:
        username: Username that failed to login
    """
    current_time = time.time()
    
    if username not in failed_attempts:
        failed_attempts[username] = {'count': 0, 'last_attempt': current_time}
    
    attempts = failed_attempts[username]
    
    # Reset if last attempt was more than lockout duration ago
    if current_time - attempts['last_attempt'] > SecurityConfig.LOCKOUT_DURATION:
        attempts['count'] = 1
    else:
        attempts['count'] += 1
    
    attempts['last_attempt'] = current_time
    
    if attempts['count'] >= SecurityConfig.MAX_LOGIN_ATTEMPTS:
        logger.warning(f"Account locked due to failed login attempts: {username}")


def reset_failed_logins(username: str):
    """Reset failed login attempts for a user.
    
    Args:
        username: Username to reset
    """
    if username in failed_attempts:
        del failed_attempts[username]


def verify_credentials(username: str, password: str) -> Optional[str]:
    """Verify username and password.
    
    Args:
        username: Username to verify
        password: Password to verify
    
    Returns:
        User type ('publisher' or 'viewer') if valid, None otherwise
    """
    # Check if account is locked
    if check_account_lockout(username):
        logger.warning(f"Login attempt for locked account: {username}")
        return None
    
    creds = get_credentials()
    
    # Check publisher credentials
    if username == creds["publish_user"] and password == creds["publish_pass"]:
        reset_failed_logins(username)
        return "publisher"
    
    # Check viewer credentials
    if username == creds["read_user"] and password == creds["read_pass"]:
        reset_failed_logins(username)
        return "viewer"
    
    # Invalid credentials
    record_failed_login(username)
    return None


def create_session(username: str, user_type: str) -> str:
    """Create a new session for a user.
    
    Args:
        username: Username
        user_type: User type ('publisher' or 'viewer')
    
    Returns:
        Session ID
    """
    session_id = secrets.token_urlsafe(32)
    sessions[session_id] = {
        "username": username,
        "user_type": user_type,
        "created": time.time(),
        "expires": time.time() + SecurityConfig.SESSION_TIMEOUT,
        "last_activity": time.time()
    }
    return session_id


def get_session(session_id: str) -> Optional[Dict]:
    """Get session information.
    
    Args:
        session_id: Session ID
    
    Returns:
        Session dict if valid, None otherwise
    """
    if not session_id or session_id not in sessions:
        return None
    
    session = sessions[session_id]
    current_time = time.time()
    
    # Check if expired
    if current_time > session["expires"]:
        del sessions[session_id]
        return None
    
    # Update last activity
    session["last_activity"] = current_time
    
    return session


def delete_session(session_id: str):
    """Delete a session.
    
    Args:
        session_id: Session ID to delete
    """
    if session_id in sessions:
        del sessions[session_id]


def cleanup_expired_sessions():
    """Remove expired sessions from store."""
    current_time = time.time()
    expired = [
        session_id for session_id, session in sessions.items()
        if current_time > session["expires"]
    ]
    for session_id in expired:
        del sessions[session_id]
    
    if expired:
        logger.info(f"Cleaned up {len(expired)} expired sessions")


# FastAPI Dependencies

async def verify_viewer_basic(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    """Verify viewer credentials using HTTP Basic Auth.
    
    Args:
        credentials: HTTP Basic Auth credentials
    
    Returns:
        Username if valid
    
    Raises:
        HTTPException: If credentials are invalid
    """
    user_type = verify_credentials(credentials.username, credentials.password)
    
    if user_type not in ["viewer", "publisher"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    return credentials.username


async def verify_publisher_basic(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    """Verify publisher credentials using HTTP Basic Auth.
    
    Args:
        credentials: HTTP Basic Auth credentials
    
    Returns:
        Username if valid
    
    Raises:
        HTTPException: If credentials are invalid or not publisher
    """
    user_type = verify_credentials(credentials.username, credentials.password)
    
    if user_type != "publisher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Publisher access required",
        )
    
    return credentials.username


async def get_current_user_from_session(request: Request) -> str:
    """Get current user from session cookie.
    
    Args:
        request: FastAPI request object
    
    Returns:
        Username if valid session
    
    Raises:
        HTTPException: If session is invalid
    """
    session_id = request.cookies.get("session_id")
    
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    session = get_session(session_id)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session"
        )
    
    return session["username"]


def require_rate_limit(max_requests: int = 10, window: int = 60):
    """Decorator to enforce rate limiting on endpoints.
    
    Args:
        max_requests: Maximum requests allowed in window
        window: Time window in seconds
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            client_ip = request.client.host
            endpoint = request.url.path
            
            if not check_rate_limit(client_ip, endpoint, max_requests, window):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded"
                )
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator
```

---

## CORS Policy Fix ✅ COMPLETED

### Update CORS Configuration

**File: `video-feed/videofeed/visualizer.py`** ✅ **IMPLEMENTED 2025-10-01**

~~Replace the CORS middleware section (lines 36-42) with:~~ **DONE:**

```python
from videofeed.utils import detect_host_ip

# Get host IP for CORS configuration
host_ip = detect_host_ip()

# Configure CORS middleware with restricted origins
allowed_origins = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    f"http://{host_ip}:8080",
    "http://localhost:3000",  # If you have a separate frontend
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # ✅ Restricted origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "PUT"],  # ✅ Specific methods only
    allow_headers=["Content-Type", "Authorization", "Cookie"],  # ✅ Specific headers
    max_age=3600,  # Cache preflight requests for 1 hour
)

logger.info(f"CORS configured for origins: {allowed_origins}")
```

---

## Path Traversal Fix ✅ COMPLETED

### Secure File Serving

**File: `video-feed/videofeed/visualizer.py`** ✅ **IMPLEMENTED 2025-10-01**

~~Replace the `serve_recording_file` function (lines 155-168) with:~~ **DONE:**

```python
from pathlib import Path

@app.get("/recordings/{file_path:path}")
async def serve_recording_file(
    file_path: str,
    user: str = Depends(verify_viewer_basic)  # ✅ Add authentication
):
    """Serve a recording file (video or thumbnail) with security checks."""
    global recordings_directory
    
    if not recordings_directory:
        raise HTTPException(status_code=404, detail="Recording directory not configured")
    
    try:
        # Convert to Path objects and resolve to absolute paths
        recordings_path = Path(recordings_directory).resolve()
        requested_path = (recordings_path / file_path).resolve()
        
        # ✅ CRITICAL: Ensure requested path is within recordings directory
        # This prevents path traversal attacks like "../../../etc/passwd"
        if not requested_path.is_relative_to(recordings_path):
            logger.warning(f"Path traversal attempt blocked: {file_path} from user {user}")
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Check if file exists
        if not requested_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
        
        # Check if it's a file (not a directory)
        if not requested_path.is_file():
            raise HTTPException(status_code=403, detail="Not a file")
        
        # ✅ Validate file extension (only allow expected types)
        allowed_extensions = {'.mp4', '.jpg', '.jpeg', '.png', '.webm'}
        if requested_path.suffix.lower() not in allowed_extensions:
            logger.warning(f"Unauthorized file type access attempt: {requested_path.suffix} from user {user}")
            raise HTTPException(status_code=403, detail="File type not allowed")
        
        # Log access for audit
        logger.info(f"File access: {file_path} by user {user}")
        
        return FileResponse(requested_path)
        
    except ValueError as e:
        # is_relative_to can raise ValueError
        logger.error(f"Path validation error: {e}")
        raise HTTPException(status_code=403, detail="Invalid path")
    except Exception as e:
        logger.error(f"Error serving file {file_path}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
```

---

## Rate Limiting

### Add Rate Limiting to Auth Endpoint

**File: `video-feed/videofeed/visualizer.py`**

First, add the import at the top:
```python
from videofeed.security import require_rate_limit, verify_credentials as verify_creds_secure
```

Then update the `/auth/verify` endpoint (lines 503-528):

```python
@app.post("/auth/verify")
@require_rate_limit(max_requests=5, window=60)  # ✅ Max 5 attempts per minute
async def verify_credentials(request: Request, user_creds: UserCredentials):
    """Verify if credentials match those in the system keychain with rate limiting."""
    
    # Use secure verification function
    user_type = verify_creds_secure(user_creds.username, user_creds.password)
    
    if user_type:
        # Log successful authentication
        logger.info(f"Successful authentication: {user_creds.username} ({user_type})")
        
        return {
            "authenticated": True,
            "user_type": user_type,
            "username": user_creds.username
        }
    
    # Log failed authentication
    client_ip = request.client.host
    logger.warning(f"Failed authentication attempt: {user_creds.username} from {client_ip}")
    
    # Invalid credentials
    raise HTTPException(
        status_code=401,
        detail="Invalid credentials or account locked"
    )
```

---

## HTTPS Support

### Generate Self-Signed Certificate (Development)

**File: `video-feed/generate_certs.sh`** (NEW FILE)
```bash
#!/bin/bash

# Generate self-signed certificate for development
# For production, use Let's Encrypt or a proper CA

CERT_DIR="$(dirname "$0")"
DAYS=365
HOST_IP=$(hostname -I | awk '{print $1}')

echo "Generating self-signed certificate for HTTPS..."
echo "Host IP: $HOST_IP"

openssl req -x509 -newkey rsa:4096 -nodes \
  -keyout "$CERT_DIR/server.key" \
  -out "$CERT_DIR/server.crt" \
  -days $DAYS \
  -subj "/CN=surveillance.local/O=SentriX/C=US" \
  -addext "subjectAltName=DNS:surveillance.local,DNS:localhost,IP:127.0.0.1,IP:$HOST_IP"

# Set secure permissions
chmod 600 "$CERT_DIR/server.key"
chmod 644 "$CERT_DIR/server.crt"

echo "✅ Certificate generated successfully!"
echo "   Key: $CERT_DIR/server.key"
echo "   Cert: $CERT_DIR/server.crt"
echo ""
echo "⚠️  This is a self-signed certificate for development only."
echo "   Browsers will show security warnings."
echo "   For production, use a certificate from a trusted CA."
```

Make it executable:
```bash
chmod +x video-feed/generate_certs.sh
```

### Enable HTTPS in Visualizer

**File: `video-feed/videofeed/visualizer.py`**

Update the `start_visualizer` function (lines 636-649):

```python
def start_visualizer(
    rtsp_urls: List[str],
    host: str = "0.0.0.0",
    port: int = 8000,
    model_path: str = "yolov8n.pt",
    confidence: float = 0.4,
    resolution: tuple = (960, 540),
    enable_recording: bool = False,
    recordings_dir: Optional[str] = None,
    min_confidence: float = 0.5,
    pre_detection_buffer: int = 5,
    post_detection_buffer: int = 5,
    use_https: bool = True,  # ✅ New parameter
    ssl_keyfile: Optional[str] = None,  # ✅ New parameter
    ssl_certfile: Optional[str] = None  # ✅ New parameter
):
    """Start the API server with object detection for multiple streams.
    
    Args:
        ... existing args ...
        use_https: Enable HTTPS
        ssl_keyfile: Path to SSL key file
        ssl_certfile: Path to SSL certificate file
    """
    # ... existing code ...
    
    # Determine SSL paths
    if use_https:
        if not ssl_keyfile or not ssl_certfile:
            # Use default paths
            default_key = Path(__file__).parent.parent / "server.key"
            default_cert = Path(__file__).parent.parent / "server.crt"
            
            if default_key.exists() and default_cert.exists():
                ssl_keyfile = str(default_key)
                ssl_certfile = str(default_cert)
                logger.info("Using default SSL certificates")
            else:
                logger.warning("HTTPS requested but no certificates found. Run generate_certs.sh")
                use_https = False
    
    # Config for Uvicorn with optional SSL
    config_kwargs = {
        "app": app,
        "host": host,
        "port": port,
        "log_level": "info",
        "timeout_keep_alive": 2,
        "timeout_graceful_shutdown": 3
    }
    
    if use_https:
        config_kwargs["ssl_keyfile"] = ssl_keyfile
        config_kwargs["ssl_certfile"] = ssl_certfile
        protocol = "https"
    else:
        protocol = "http"
    
    config = uvicorn.Config(**config_kwargs)
    
    # Start Uvicorn server
    server = uvicorn.Server(config)
    logger.info(f"Starting API server at {protocol}://{host}:{port}")
    logger.info("Press Ctrl+C once to exit cleanly.")
    server.run()
```

---

## File Encryption

### Encrypted Recording Manager

**File: `video-feed/videofeed/encryption.py`** (NEW FILE)
```python
"""Encryption utilities for video recordings."""

import os
import logging
from pathlib import Path
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger('encryption')


class EncryptionManager:
    """Manage encryption/decryption of recording files."""
    
    def __init__(self, recordings_dir: Path, password: Optional[str] = None):
        """Initialize encryption manager.
        
        Args:
            recordings_dir: Directory where recordings are stored
            password: Optional password for key derivation (uses keyfile if not provided)
        """
        self.recordings_dir = Path(recordings_dir)
        self.key_file = self.recordings_dir / ".encryption_key"
        self.salt_file = self.recordings_dir / ".encryption_salt"
        
        # Initialize or load encryption key
        if password:
            self.cipher = self._init_with_password(password)
        else:
            self.cipher = self._init_with_keyfile()
    
    def _init_with_keyfile(self) -> Fernet:
        """Initialize encryption with a keyfile."""
        if self.key_file.exists():
            # Load existing key
            key = self.key_file.read_bytes()
            logger.info("Loaded existing encryption key")
        else:
            # Generate new key
            key = Fernet.generate_key()
            self.key_file.write_bytes(key)
            os.chmod(self.key_file, 0o600)  # Owner read/write only
            logger.info("Generated new encryption key")
        
        return Fernet(key)
    
    def _init_with_password(self, password: str) -> Fernet:
        """Initialize encryption with a password-derived key."""
        if self.salt_file.exists():
            salt = self.salt_file.read_bytes()
        else:
            salt = os.urandom(16)
            self.salt_file.write_bytes(salt)
            os.chmod(self.salt_file, 0o600)
        
        # Derive key from password
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = kdf.derive(password.encode())
        
        # Fernet requires base64-encoded key
        from base64 import urlsafe_b64encode
        key_b64 = urlsafe_b64encode(key)
        
        return Fernet(key_b64)
    
    def encrypt_file(self, file_path: str) -> str:
        """Encrypt a file in place.
        
        Args:
            file_path: Path to file to encrypt
        
        Returns:
            Path to encrypted file
        """
        try:
            path = Path(file_path)
            
            # Read file
            with open(path, 'rb') as f:
                data = f.read()
            
            # Encrypt
            encrypted_data = self.cipher.encrypt(data)
            
            # Write encrypted file
            encrypted_path = path.with_suffix(path.suffix + '.enc')
            with open(encrypted_path, 'wb') as f:
                f.write(encrypted_data)
            
            # Set secure permissions
            os.chmod(encrypted_path, 0o600)
            
            # Delete original
            os.remove(path)
            
            logger.info(f"Encrypted file: {path.name}")
            return str(encrypted_path)
            
        except Exception as e:
            logger.error(f"Failed to encrypt file {file_path}: {e}")
            raise
    
    def decrypt_file(self, encrypted_path: str, output_path: Optional[str] = None) -> str:
        """Decrypt a file.
        
        Args:
            encrypted_path: Path to encrypted file
            output_path: Optional output path (defaults to removing .enc extension)
        
        Returns:
            Path to decrypted file
        """
        try:
            enc_path = Path(encrypted_path)
            
            # Read encrypted file
            with open(enc_path, 'rb') as f:
                encrypted_data = f.read()
            
            # Decrypt
            data = self.cipher.decrypt(encrypted_data)
            
            # Determine output path
            if output_path is None:
                if enc_path.suffix == '.enc':
                    output_path = enc_path.with_suffix('')
                else:
                    output_path = enc_path.with_suffix('.decrypted')
            
            # Write decrypted file
            with open(output_path, 'wb') as f:
                f.write(data)
            
            logger.info(f"Decrypted file: {enc_path.name}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Failed to decrypt file {encrypted_path}: {e}")
            raise
    
    def encrypt_stream(self, data: bytes) -> bytes:
        """Encrypt data in memory.
        
        Args:
            data: Data to encrypt
        
        Returns:
            Encrypted data
        """
        return self.cipher.encrypt(data)
    
    def decrypt_stream(self, encrypted_data: bytes) -> bytes:
        """Decrypt data in memory.
        
        Args:
            encrypted_data: Encrypted data
        
        Returns:
            Decrypted data
        """
        return self.cipher.decrypt(encrypted_data)
```

### Update Recording Manager to Use Encryption

**File: `video-feed/videofeed/recorder.py`**

Add at the top:
```python
from videofeed.encryption import EncryptionManager
```

Update `__init__`:
```python
def __init__(self, ..., enable_encryption: bool = True):
    # ... existing code ...
    
    # Initialize encryption if enabled
    self.enable_encryption = enable_encryption
    if enable_encryption:
        self.encryption_manager = EncryptionManager(self.recordings_dir)
        logger.info("Encryption enabled for recordings")
    else:
        self.encryption_manager = None
```

Update `_finalize_recording`:
```python
def _finalize_recording(self, recording_id: str):
    """Finalize a recording and save to database."""
    logger.info(f"Finalizing recording {recording_id}")
    with self._lock:
        if recording_id not in self.active_recordings:
            return
            
        recording = self.active_recordings[recording_id]
        stream_id = recording['stream_id']
        
        # Release the video writer
        writer = recording['writer']
        writer.release()
        
        # ✅ Encrypt the recording if encryption is enabled
        file_path = recording['file_path']
        if self.enable_encryption and self.encryption_manager:
            try:
                encrypted_path = self.encryption_manager.encrypt_file(file_path)
                file_path = encrypted_path
                logger.info(f"Encrypted recording: {recording_id}")
            except Exception as e:
                logger.error(f"Failed to encrypt recording {recording_id}: {e}")
        
        # ✅ Encrypt thumbnail if encryption is enabled
        thumbnail_path = recording['thumbnail_path']
        if self.enable_encryption and self.encryption_manager and thumbnail_path:
            try:
                encrypted_thumb = self.encryption_manager.encrypt_file(thumbnail_path)
                thumbnail_path = encrypted_thumb
            except Exception as e:
                logger.error(f"Failed to encrypt thumbnail: {e}")
        
        # ... rest of existing code ...
        # Update file_path and thumbnail_path in database insert
```

---

## Complete Security Module

### Security Utilities

**File: `video-feed/videofeed/security_utils.py`** (NEW FILE)
```python
"""Security utility functions."""

import hashlib
import secrets
import logging
from typing import Optional

logger = logging.getLogger('security-utils')


def generate_strong_password(length: int = 32) -> str:
    """Generate a cryptographically strong password.
    
    Args:
        length: Length of password (default 32)
    
    Returns:
        Strong random password
    """
    return secrets.token_urlsafe(length)


def hash_password(password: str, salt: Optional[bytes] = None) -> tuple:
    """Hash a password with salt.
    
    Args:
        password: Password to hash
        salt: Optional salt (generated if not provided)
    
    Returns:
        Tuple of (hash, salt)
    """
    if salt is None:
        salt = secrets.token_bytes(32)
    
    # Use PBKDF2 with SHA-256
    from hashlib import pbkdf2_hmac
    hash_value = pbkdf2_hmac('sha256', password.encode(), salt, 100000)
    
    return hash_value, salt


def verify_password(password: str, hash_value: bytes, salt: bytes) -> bool:
    """Verify a password against a hash.
    
    Args:
        password: Password to verify
        hash_value: Expected hash value
        salt: Salt used in hashing
    
    Returns:
        True if password matches, False otherwise
    """
    computed_hash, _ = hash_password(password, salt)
    return secrets.compare_digest(computed_hash, hash_value)


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename to prevent path traversal.
    
    Args:
        filename: Filename to sanitize
    
    Returns:
        Sanitized filename
    """
    import re
    # Remove any path separators and special characters
    sanitized = re.sub(r'[^\w\s.-]', '', filename)
    # Remove leading dots to prevent hidden files
    sanitized = sanitized.lstrip('.')
    return sanitized


def mask_sensitive_data(data: str, visible_chars: int = 4) -> str:
    """Mask sensitive data for logging.
    
    Args:
        data: Data to mask
        visible_chars: Number of characters to leave visible
    
    Returns:
        Masked string
    """
    if len(data) <= visible_chars:
        return '*' * len(data)
    
    return data[:visible_chars] + '*' * (len(data) - visible_chars)
```

---

## Testing the Security Improvements

### Security Test Script

**File: `video-feed/test_security.py`** (NEW FILE)
```python
"""Security tests for video-feed."""

import requests
import time
from typing import Dict

BASE_URL = "http://localhost:8080"


def test_rate_limiting():
    """Test rate limiting on auth endpoint."""
    print("Testing rate limiting...")
    
    # Try to exceed rate limit
    for i in range(10):
        response = requests.post(
            f"{BASE_URL}/auth/verify",
            json={"username": "test", "password": "test"}
        )
        print(f"Attempt {i+1}: {response.status_code}")
        
        if response.status_code == 429:
            print("✅ Rate limiting working!")
            return True
    
    print("❌ Rate limiting not working")
    return False


def test_authentication():
    """Test authentication on protected endpoints."""
    print("\nTesting authentication...")
    
    # Try to access protected endpoint without auth
    response = requests.get(f"{BASE_URL}/api/recordings")
    
    if response.status_code == 401:
        print("✅ Authentication required for protected endpoints")
        return True
    else:
        print(f"❌ Endpoint not protected: {response.status_code}")
        return False


def test_path_traversal():
    """Test path traversal protection."""
    print("\nTesting path traversal protection...")
    
    # Try path traversal attack
    malicious_paths = [
        "../../../etc/passwd",
        "..%2F..%2F..%2Fetc%2Fpasswd",
        "....//....//....//etc/passwd"
    ]
    
    for path in malicious_paths:
        response = requests.get(f"{BASE_URL}/recordings/{path}")
        
        if response.status_code in [403, 404]:
            print(f"✅ Blocked: {path}")
        else:
            print(f"❌ Not blocked: {path} ({response.status_code})")
            return False
    
    print("✅ Path traversal protection working")
    return True


def test_cors():
    """Test CORS policy."""
    print("\nTesting CORS policy...")
    
    # Try request from unauthorized origin
    headers = {"Origin": "http://evil.com"}
    response = requests.options(f"{BASE_URL}/api/recordings", headers=headers)
    
    cors_header = response.headers.get("Access-Control-Allow-Origin")
    
    if cors_header == "*":
        print("❌ CORS allows all origins")
        return False
    elif cors_header and "evil.com" not in cors_header:
        print("✅ CORS properly restricted")
        return True
    else:
        print("✅ CORS header not present (good)")
        return True


if __name__ == "__main__":
    print("Running security tests...\n")
    
    results = {
        "Rate Limiting": test_rate_limiting(),
        "Authentication": test_authentication(),
        "Path Traversal": test_path_traversal(),
        "CORS": test_cors()
    }
    
    print("\n" + "="*50)
    print("SECURITY TEST RESULTS")
    print("="*50)
    
    for test, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test}: {status}")
    
    all_passed = all(results.values())
    print("\n" + ("="*50))
    if all_passed:
        print("🎉 All security tests passed!")
    else:
        print("⚠️  Some security tests failed. Review and fix.")
```

Run tests:
```bash
python video-feed/test_security.py
```

---

## Deployment Checklist

Before deploying to production:

- [ ] Change default bind address to `127.0.0.1`
- [ ] Generate proper SSL certificates
- [ ] Enable authentication on all endpoints
- [ ] Fix CORS policy
- [ ] Enable rate limiting
- [ ] Enable file encryption
- [ ] Set secure file permissions
- [ ] Review and update `.gitignore`
- [ ] Test all security features
- [ ] Set up firewall rules
- [ ] Document security procedures
- [ ] Create backup and recovery plan
- [ ] Set up monitoring and alerting

---

## Next Steps

1. **Implement Critical Fixes First** (30 minutes)
   - Update CORS policy
   - Fix path traversal
   - Add authentication to endpoints

2. **Add Rate Limiting** (30 minutes)
   - Implement rate limiting middleware
   - Apply to auth endpoint

3. **Enable HTTPS** (30 minutes)
   - Generate certificates
   - Update visualizer configuration

4. **Add File Encryption** (2 hours)
   - Implement encryption manager
   - Update recording manager
   - Test encryption/decryption

5. **Test Everything** (1 hour)
   - Run security test script
   - Manual testing
   - Fix any issues

**Total Time: ~5 hours for complete security hardening**

---

## Support

For questions or issues:
1. Check the main `SECURITY_ANALYSIS.md` document
2. Review FastAPI security documentation
3. Consult the MediaMTX security guide

Remember: **Security is a process, not a destination.** Regularly review and update security measures.
