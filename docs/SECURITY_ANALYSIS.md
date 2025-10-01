# Security Analysis - SentriX Surveillance System

**Date:** 2025-10-01  
**System:** Private local surveillance system with no third-party dependencies

---

## Executive Summary

SentriX is a well-architected local surveillance system built around MediaMTX (RTSP/HLS server), YOLO object detection, and FastAPI visualization. The system prioritizes **privacy-first design** with no cloud dependencies. Current security is **moderate** with good foundations but several areas need hardening for production use.

**Current Security Posture:** 🟡 **MODERATE** → 🟢 **IMPROVING**
- ✅ Local-only operation (no third-party services)
- ✅ TLS/RTSPS encryption support
- ✅ OS keyring credential storage
- ✅ **FIXED: Restricted CORS policy** (2025-10-01)
- ✅ **FIXED: Path traversal protection** (2025-10-01)
- ⚠️ Self-signed certificates (expected)
- ⚠️ Basic authentication only
- ⚠️ No rate limiting or brute-force protection
- ⚠️ Credentials in URLs (RTSP standard but risky)

---

## System Architecture Overview

### Core Components

1. **MediaMTX Server** - RTSP/RTSPS/HLS streaming server
   - Ports: 8554 (RTSP), 8322 (RTSPS), 8888 (HLS)
   - Authentication: Basic auth with publisher/viewer roles

2. **FastAPI Visualizer** - Web dashboard and API
   - Port: 8080 (default)
   - CORS: ✅ **Restricted to specific origins** (localhost + host IP)
   - Authentication: Simple credential verification endpoint

3. **YOLO Detector** - Object detection pipeline
   - Processes RTSP streams with credentials embedded in URLs
   - No additional security layer

4. **Recording Manager** - SQLite database + video files
   - Local filesystem storage
   - No encryption at rest

5. **Credential Manager** - OS keyring integration
   - Stores publisher/viewer passwords
   - 24-character URL-safe tokens

---

## Security Analysis by Layer

### 1. Stream Security (RTSP/RTSPS)

#### ✅ Current Strengths
- **RTSPS support** with TLS encryption (optional but enabled by default)
- **Separate credentials** for publishers (cameras) and viewers
- **Path-based permissions** in MediaMTX config
- **TCP transport** to avoid packet loss

#### ⚠️ Vulnerabilities & Concerns

**CRITICAL: Credentials in URLs**
```python
# From surveillance.py line 176
url = f"rtsps://{creds['read_user']}:{creds['read_pass']}@{host}:8322/{path}"
```
- Credentials embedded in RTSP URLs (standard practice but risky)
- URLs logged to console and potentially to log files
- URLs visible in process lists (`ps aux`)
- URLs may be cached in browser history or shell history

**Self-Signed Certificates**
```python
# From surveillance.py lines 77-83
default_tls_key = Path(__file__).parent.parent / "server.key"
default_tls_cert = Path(__file__).parent.parent / "server.crt"
```
- Self-signed certs trigger security warnings
- No certificate rotation mechanism
- Certificates stored in repo (if committed)
- No certificate validation in clients

**Network Exposure**
```yaml
# From surveillance.yml line 10
bind: "0.0.0.0"  # Listen on all interfaces
```
- Binds to all network interfaces by default
- No IP whitelisting
- No network segmentation guidance

**Weak Password Generation**
```python
# From credentials.py line 12
return secrets.token_urlsafe(24)  # 32 chars, ~144 bits entropy
```
- Good entropy BUT passwords never expire
- No password rotation policy
- No password complexity requirements for custom passwords

---

### 2. Web Dashboard Security (FastAPI)

#### ✅ Current Strengths
- **FastAPI framework** with modern security features
- **Credential verification endpoint** (`/auth/verify`)
- **Separate user roles** (publisher vs viewer)

#### ✅ Fixed Vulnerabilities

**CORS Policy - FIXED (2025-10-01)**
```python
# From visualizer.py - NOW SECURE
allowed_origins = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    f"http://{host_ip}:8080",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # ✅ Restricted origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "PUT"],  # ✅ Specific methods
    allow_headers=["Content-Type", "Authorization", "Cookie"],  # ✅ Specific headers
)
```
- ✅ **CSRF attacks blocked** from unauthorized origins
- ✅ **Limited attack surface** with specific methods/headers
- ✅ **Preflight caching** for performance

**No Authentication Middleware**
```python
# Most endpoints have NO authentication check
@app.get("/status")
async def get_status(feed: Optional[str] = None):
    # No auth check - anyone can access
```
- `/status`, `/feeds`, `/video/stream`, `/api/recordings` are **UNAUTHENTICATED**
- Only `/auth/verify` checks credentials (but doesn't enforce them)
- Anyone on the network can view streams and recordings

**No Rate Limiting**
- Brute force attacks on `/auth/verify` are trivial
- No protection against DoS attacks
- No request throttling

**Session Management Missing**
- No JWT tokens or session cookies
- Credentials must be sent with every request
- No session timeout or invalidation

**Sensitive Data Exposure**
```python
# From visualizer.py line 325
return {
    "running": self.running,
    "fps": self.fps,
    "source": self._mask_credentials(self.source_url),  # Good!
    # But other endpoints may leak info
}
```
- Stream paths and camera names exposed
- System configuration details visible
- Recording metadata accessible without auth

---

### 3. Credential Storage

#### ✅ Current Strengths
```python
# From credentials.py lines 15-21
def get_secret(label: str) -> str:
    secret = keyring.get_password(KEYCHAIN_SERVICE, label)
    if not secret:
        secret = rand_secret()
        keyring.set_password(KEYCHAIN_SERVICE, label, secret)
    return secret
```
- **OS keyring integration** (Keychain on macOS, Secret Service on Linux)
- **Automatic generation** of strong passwords
- **No plaintext storage** in config files

#### ⚠️ Concerns

**Keyring Security Depends on OS**
- macOS Keychain: Good, but accessible if system is unlocked
- Linux Secret Service: Varies by distribution
- No additional encryption layer

**No Key Rotation**
- Credentials persist indefinitely
- Manual reset required (`surveillance.py reset`)
- No automated rotation schedule

**MediaMTX Config File**
```python
# From config.py line 75
os.chmod(cfg_path, 0o600)  # Good! But...
```
- Temporary config files contain credentials
- Config files may be left behind on crashes
- No secure deletion mechanism

---

### 4. Recording Storage

#### ⚠️ Major Concerns

**No Encryption at Rest**
```python
# From recorder.py lines 340-346
writer = cv2.VideoWriter(
    video_path, 
    self.fourcc, 
    actual_fps, 
    (width, height)
)
```
- Video files stored as plaintext MP4
- SQLite database unencrypted
- Thumbnails unencrypted
- Anyone with filesystem access can view recordings

**Database Security**
```python
# From recorder.py line 87
self.db_conn = sqlite3.connect(self.db_path, check_same_thread=False)
```
- No database password
- No connection encryption
- `check_same_thread=False` allows concurrent access (potential race conditions)

**File Permissions**
- No explicit file permission setting on recordings
- Default umask applies (typically 0644 - world readable!)
- No directory permission hardening

**Storage Location**
```yaml
# From surveillance.yml line 30
recordings_dir: "~/video-feed-recordings"
```
- Predictable location
- No obfuscation
- Easy target for attackers

---

### 5. API Security

#### 🚨 Critical Issues

**Unauthenticated Endpoints**
- `/api/recordings` - List all recordings
- `/api/recordings/{id}` - Get recording details
- `/recordings/{file_path}` - Download recordings
- `/api/alerts` - View detection alerts
- `/api/stats/*` - System statistics
- `/status` - System status
- `/feeds` - List all camera feeds

**Input Validation - FIXED (2025-10-01)**
```python
# From visualizer.py - NOW SECURE
@app.get("/recordings/{file_path:path}")
async def serve_recording_file(file_path: str):
    recordings_path = Path(recordings_directory).resolve()
    requested_path = (recordings_path / file_path).resolve()
    
    # ✅ Prevent path traversal
    if not requested_path.is_relative_to(recordings_path):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # ✅ Validate file type
    allowed_extensions = {'.mp4', '.jpg', '.jpeg', '.png', '.webm', '.enc'}
    if requested_path.suffix.lower() not in allowed_extensions:
        raise HTTPException(status_code=403, detail="File type not allowed")
```
- ✅ **Path traversal attacks blocked**
- ✅ **File type whitelist** enforced
- ✅ **Audit logging** for all file access

**SQL Injection Risk** (Low but present)
- Using parameterized queries (good!)
- But complex query building in `api.py` may have edge cases

**No HTTPS for Web Dashboard**
- FastAPI runs on HTTP by default
- Credentials sent in plaintext over network
- Man-in-the-middle attacks possible

---

## Threat Model

### Attack Scenarios

#### 1. **Local Network Attacker** (Most Likely)
**Threat:** Someone on your WiFi/LAN
- Can access all unauthenticated endpoints
- Can view live streams without credentials
- Can download all recordings
- Can enumerate camera locations
- Can perform reconnaissance for physical attacks

#### 2. **Compromised Device**
**Threat:** Malware on a device on your network
- Can steal credentials from keyring (if device is unlocked)
- Can access recordings from filesystem
- Can inject malicious streams
- Can DoS the system

#### 3. **Physical Access**
**Threat:** Someone with physical access to the server
- Can read all recordings (no encryption at rest)
- Can extract credentials from keyring
- Can modify code to exfiltrate data
- Can install backdoors

#### 4. **Web-Based Attack**
**Threat:** Malicious website visited by user
- Can exploit wide-open CORS to access API
- Can enumerate system information
- Can attempt to view streams (if user is authenticated elsewhere)

---

## Recommended Security Improvements

### 🔴 CRITICAL (Implement Immediately)

#### 1. **Add Authentication Middleware**
```python
# Protect ALL sensitive endpoints with auth
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

security = HTTPBasic()

async def verify_viewer(credentials: HTTPBasicCredentials = Depends(security)):
    creds = get_credentials()
    if credentials.username != creds["read_user"] or \
       credentials.password != creds["read_pass"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# Apply to endpoints
@app.get("/api/recordings", dependencies=[Depends(verify_viewer)])
async def get_recordings(...):
    ...
```

#### 2. **Fix CORS Policy**
```python
# Restrict to specific origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        f"http://{detect_host_ip()}:8080"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],  # Only what's needed
    allow_headers=["Content-Type", "Authorization"],
)
```

#### 3. **Fix Path Traversal Vulnerability**
```python
from pathlib import Path

@app.get("/recordings/{file_path:path}")
async def serve_recording_file(file_path: str):
    # Validate and sanitize path
    recordings_path = Path(recordings_directory).resolve()
    requested_path = (recordings_path / file_path).resolve()
    
    # Ensure requested path is within recordings directory
    if not requested_path.is_relative_to(recordings_path):
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not requested_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(requested_path)
```

#### 4. **Add Rate Limiting**
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/auth/verify")
@limiter.limit("5/minute")  # Max 5 attempts per minute
async def verify_credentials(request: Request, user_creds: UserCredentials):
    ...
```

---

### 🟡 HIGH PRIORITY (Implement Soon)

#### 5. **Add HTTPS Support for Web Dashboard**
```python
# Use uvicorn with SSL
uvicorn.run(
    app,
    host=host,
    port=port,
    ssl_keyfile="path/to/key.pem",
    ssl_certfile="path/to/cert.pem"
)
```

#### 6. **Implement Session-Based Authentication**
```python
from fastapi import Cookie
import secrets
import time

# Session store (use Redis in production)
sessions = {}

@app.post("/auth/login")
async def login(user_creds: UserCredentials):
    # Verify credentials
    if verify_credentials(user_creds):
        session_id = secrets.token_urlsafe(32)
        sessions[session_id] = {
            "username": user_creds.username,
            "created": time.time(),
            "expires": time.time() + 3600  # 1 hour
        }
        response = JSONResponse({"success": True})
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            secure=True,  # HTTPS only
            samesite="strict"
        )
        return response
    raise HTTPException(status_code=401)

async def get_current_user(session_id: str = Cookie(None)):
    if not session_id or session_id not in sessions:
        raise HTTPException(status_code=401)
    
    session = sessions[session_id]
    if time.time() > session["expires"]:
        del sessions[session_id]
        raise HTTPException(status_code=401)
    
    return session["username"]
```

#### 7. **Encrypt Recordings at Rest**
```python
from cryptography.fernet import Fernet
import os

class EncryptedRecordingManager(RecordingManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Generate or load encryption key
        key_path = self.recordings_dir / ".encryption_key"
        if key_path.exists():
            self.encryption_key = key_path.read_bytes()
        else:
            self.encryption_key = Fernet.generate_key()
            key_path.write_bytes(self.encryption_key)
            os.chmod(key_path, 0o600)
        self.cipher = Fernet(self.encryption_key)
    
    def _save_recording(self, video_path: str):
        # Read video file
        with open(video_path, 'rb') as f:
            data = f.read()
        
        # Encrypt
        encrypted_data = self.cipher.encrypt(data)
        
        # Save encrypted version
        encrypted_path = video_path + ".enc"
        with open(encrypted_path, 'wb') as f:
            f.write(encrypted_data)
        
        # Delete unencrypted version
        os.remove(video_path)
        
        return encrypted_path
```

#### 8. **Harden File Permissions**
```python
import os
import stat

# For recordings directory
os.chmod(recordings_dir, stat.S_IRWXU)  # 0700 - owner only

# For each recording file
def save_recording(path):
    # ... save file ...
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)  # 0600 - owner read/write only
```

#### 9. **Add Credential Rotation**
```python
from datetime import datetime, timedelta

class CredentialManager:
    def __init__(self):
        self.rotation_interval = timedelta(days=90)
    
    def check_rotation_needed(self, label: str) -> bool:
        last_rotation = keyring.get_password(KEYCHAIN_SERVICE, f"{label}_last_rotation")
        if not last_rotation:
            return True
        
        last_date = datetime.fromisoformat(last_rotation)
        return datetime.now() - last_date > self.rotation_interval
    
    def rotate_credentials(self, label: str):
        new_secret = rand_secret()
        keyring.set_password(KEYCHAIN_SERVICE, label, new_secret)
        keyring.set_password(KEYCHAIN_SERVICE, f"{label}_last_rotation", 
                           datetime.now().isoformat())
        return new_secret
```

---

### 🟢 MEDIUM PRIORITY (Enhance Over Time)

#### 10. **Add Audit Logging**
```python
import logging
from datetime import datetime

audit_logger = logging.getLogger('audit')
audit_logger.setLevel(logging.INFO)
handler = logging.FileHandler('audit.log')
audit_logger.addHandler(handler)

def log_access(user: str, action: str, resource: str, success: bool):
    audit_logger.info(f"{datetime.now().isoformat()} | {user} | {action} | {resource} | {'SUCCESS' if success else 'FAILED'}")

# Use in endpoints
@app.get("/api/recordings")
async def get_recordings(user: str = Depends(get_current_user)):
    log_access(user, "VIEW_RECORDINGS", "all", True)
    ...
```

#### 11. **Network Segmentation Guidance**
Add to documentation:
```markdown
## Network Security Best Practices

1. **VLAN Isolation**: Place surveillance system on separate VLAN
2. **Firewall Rules**: 
   - Block all incoming traffic except from trusted IPs
   - Allow only necessary ports (8322, 8080, 8888)
3. **VPN Access**: Require VPN for remote access
4. **mDNS/Bonjour**: Disable if not needed
```

#### 12. **Certificate Management**
```bash
# Generate proper certificates with SAN
openssl req -x509 -newkey rsa:4096 -nodes \
  -keyout server.key -out server.crt -days 365 \
  -subj "/CN=surveillance.local" \
  -addext "subjectAltName=DNS:surveillance.local,IP:192.168.1.100"

# Set up certificate rotation
# Add to cron: 0 0 1 * * /path/to/rotate_certs.sh
```

#### 13. **Input Validation Library**
```python
from pydantic import BaseModel, validator, constr
from typing import Optional

class RecordingQuery(BaseModel):
    stream_id: Optional[constr(regex=r'^[a-zA-Z0-9_-]+$')] = None
    limit: int = 100
    offset: int = 0
    
    @validator('limit')
    def limit_range(cls, v):
        if not 1 <= v <= 1000:
            raise ValueError('limit must be between 1 and 1000')
        return v
    
    @validator('offset')
    def offset_positive(cls, v):
        if v < 0:
            raise ValueError('offset must be non-negative')
        return v

@app.get("/api/recordings")
async def get_recordings(query: RecordingQuery = Depends()):
    ...
```

#### 14. **Security Headers**
```python
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware

# Add security headers
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response

# Trusted hosts
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["localhost", "127.0.0.1", detect_host_ip()]
)
```

---

## Implementation Roadmap

### Phase 1: Critical Fixes (Week 1)
- [ ] Add authentication middleware to all endpoints
- [x] **Fix CORS policy** ✅ Completed 2025-10-01
- [x] **Fix path traversal vulnerability** ✅ Completed 2025-10-01
- [ ] Add rate limiting to auth endpoint
- [ ] Harden file permissions

### Phase 2: High Priority (Weeks 2-3)
- [ ] Implement session-based authentication
- [ ] Add HTTPS support for web dashboard
- [ ] Encrypt recordings at rest
- [ ] Add credential rotation mechanism
- [ ] Implement audit logging

### Phase 3: Medium Priority (Month 2)
- [ ] Add comprehensive input validation
- [ ] Implement security headers
- [ ] Set up proper certificate management
- [ ] Create network segmentation guide
- [ ] Add intrusion detection logging

### Phase 4: Hardening (Ongoing)
- [ ] Regular security audits
- [ ] Penetration testing
- [ ] Dependency vulnerability scanning
- [ ] Security documentation updates

---

## Quick Wins (Easy to Implement)

1. **Change default bind address** in `surveillance.yml`:
   ```yaml
   bind: "127.0.0.1"  # Localhost only by default
   ```

2. **Add `.gitignore` entries**:
   ```
   server.key
   server.crt
   *.db
   video-feed-recordings/
   audit.log
   ```

3. **Set restrictive permissions on startup**:
   ```python
   # In surveillance.py
   os.chmod(recordings_dir, 0o700)
   os.chmod(db_path, 0o600)
   ```

4. **Add security warning to README**:
   ```markdown
   ## ⚠️ Security Notice
   
   This system is designed for LOCAL network use only. Before deploying:
   1. Change default bind address to 127.0.0.1
   2. Use strong, unique passwords
   3. Enable HTTPS for web dashboard
   4. Restrict network access with firewall rules
   5. Never expose to the public internet without VPN
   ```

---

## Conclusion

Your surveillance system has a **solid foundation** with good privacy-first design principles. The main security gaps are:

1. **Lack of authentication** on most endpoints
2. **Wide-open CORS** policy
3. **No encryption at rest** for recordings
4. **Missing rate limiting** and session management

The good news: **All of these are fixable** without major architectural changes. The system's local-only design already eliminates entire classes of cloud-based attacks.

**Recommended Next Steps:**
1. Implement the 4 critical fixes (authentication, CORS, path traversal, rate limiting)
2. Add HTTPS support for the web dashboard
3. Encrypt recordings at rest
4. Document network security best practices for users

With these improvements, your system will be **production-ready** for home/small business use.

