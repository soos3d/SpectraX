import streamlit as st
from streamlit.components.v1 import html
from urllib.parse import urlparse
import ipaddress
import time
import re

def init_page_config():
    """Initialize page configuration and styling"""
    # 1. PAGE CONFIG
    st.set_page_config(
        page_title="🔴 Live Video Feed",
        page_icon="🎥",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # 2. CUSTOM STYLING
    st.markdown(
        """
        <style>
        .reportview-container, .main {
            background-color: #121212;
            color: #f0f0f0;
        }
        h1 {
            text-align: center;
            font-family: 'Segoe UI', sans-serif;
            margin-bottom: 1rem;
        }
        .video-container video {
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }
        .status-indicator {
            border-radius: 4px;
            padding: 5px 10px;
            display: inline-block;
            margin: 5px 0;
            text-align: center;
            font-weight: bold;
        }
        .status-connected {
            background-color: rgba(0,180,0,0.2);
            color: #7fff7f;
        }
        .status-connecting {
            background-color: rgba(180,180,0,0.2);
            color: #ffff7f;
        }
        .status-error {
            background-color: rgba(180,0,0,0.2);
            color: #ff7f7f;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

def collect_user_input():
    """Collect user input from sidebar"""
    st.sidebar.header("HLS Stream Settings")
    default_url = "http://localhost:8888/video/iphone-1/index.m3u8"
    hls_url = st.sidebar.text_input("HLS URL (no credentials)", default_url)
    viewer_user = st.sidebar.text_input("Viewer Username", value="viewer")
    viewer_pass = st.sidebar.text_input("Viewer Password", type="password")
    
    # Advanced options in an expandable section
    with st.sidebar.expander("Advanced Settings"):
        buffer_length = st.slider("Buffer Length (seconds)", 5, 60, 30)
        max_buffer_length = st.slider("Max Buffer Length (seconds)", 30, 120, 60)
        auto_reconnect = st.checkbox("Auto Reconnect", value=True)
        max_retries = st.slider("Max Reconnection Attempts", 3, 20, 5) if auto_reconnect else 0
    
    return {
        "hls_url": hls_url,
        "viewer_user": viewer_user,
        "viewer_pass": viewer_pass,
        "buffer_length": buffer_length,
        "max_buffer_length": max_buffer_length,
        "auto_reconnect": auto_reconnect,
        "max_retries": max_retries
    }

def validate_url(hls_url):
    """Validate the HLS URL format and security"""
    parsed = urlparse(hls_url)
    host = parsed.hostname or ""
    
    # Validate hostname
    try:
        if host != "localhost":
            ipaddress.ip_address(host)
    except ValueError:
        st.sidebar.error("❌ Host must be localhost or a valid IPv4 address")
        return False, parsed, None
    
    # Validate path format
    if "." in parsed.path and ".." in parsed.path:
        st.sidebar.error("❌ Path must not contain '..'")
        return False, parsed, None
        
    # Ensure path ends with .m3u8
    if not re.search(r'\.m3u8$', parsed.path):
        st.sidebar.error("❌ Path must end with '.m3u8'")
        return False, parsed, None
    
    # Build clean URL
    netloc = parsed.netloc
    scheme = parsed.scheme or "http"
    clean_url = f"{scheme}://{netloc}{parsed.path}"
    
    return True, parsed, clean_url

def build_player_html(config, clean_url):
    """Build the HLS.js player HTML with the given configuration"""
    timestamp = int(time.time())  # Add cache-busting timestamp
    
    return f"""
    <div class="video-container" style="display:flex;flex-direction:column;align-items:center;">
      <div id="status-indicator" class="status-indicator status-connecting">Connecting to stream...</div>
      <video id="video" controls autoplay muted style="width:80vw; max-width:1000px; height:auto;"></video>
      <div id="stream-info" style="margin-top:8px;font-size:12px;color:#aaa;">Stream Quality Information</div>
      <div id="buffer-status" style="margin-top:4px;font-size:11px;color:#888;"></div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/hls.js@1.4.0"></script>
    <script>
      // Configuration
      const cleanUrl = '{clean_url}?_cb={timestamp}';
      const authUser = '{config["viewer_user"]}';
      const authPass = '{config["viewer_pass"]}';
      const authHeader = 'Basic ' + btoa(authUser + ':' + authPass);
      const bufferLength = {config["buffer_length"]};  // Buffer length in seconds
      const maxBufferLength = {config["max_buffer_length"]};  // Max buffer length
      const autoReconnect = {str(config["auto_reconnect"]).lower()};
      const maxRetries = {config["max_retries"]};
      
      // Elements
      const video = document.getElementById('video');
      const statusIndicator = document.getElementById('status-indicator');
      const streamInfo = document.getElementById('stream-info');
      const bufferStatus = document.getElementById('buffer-status');
      
      // Variables
      let hlsInstance;
      let retryCount = 0;
      let bufferingCount = 0;
      let lastBufferingTime = 0;
      let bufferUpdateInterval;
      
      function updateStatus(status, message) {{
        statusIndicator.className = 'status-indicator status-' + status;
        statusIndicator.textContent = message;
      }}
      
      function updateBufferInfo() {{
        if (hlsInstance && hlsInstance.media) {{
          const buffered = hlsInstance.media.buffered;
          if (buffered.length > 0) {{
            const bufferedEnd = buffered.end(buffered.length - 1);
            const duration = hlsInstance.media.duration;
            const currentTime = hlsInstance.media.currentTime;
            const bufferedAhead = bufferedEnd - currentTime;
            
            bufferStatus.textContent = 'Buffer: ' + Math.round(bufferedAhead) + 's ahead | ' + Math.round(bufferedAhead/duration*100) + '% | Level: ' + hlsInstance.currentLevel;
          }}
        }}
      }}
      
      function createHlsPlayer() {{
        // Destroy existing instance if it exists
        if (hlsInstance) {{
          hlsInstance.destroy();
        }}
        
        // Clear any existing interval
        if (bufferUpdateInterval) {{
          clearInterval(bufferUpdateInterval);
        }}
        
        if (retryCount > 0) {{
          updateStatus('connecting', 'Reconnecting (Attempt ' + retryCount + '/' + maxRetries + ')...');
        }}
        
        hlsInstance = new Hls({{
          // Essential buffering parameters
          maxBufferLength: bufferLength,
          maxMaxBufferLength: maxBufferLength,
          
          // Additional optimizations to reduce buffering
          highBufferWatchdogPeriod: 3,        // Faster detection of buffer issues
          abrEwmaDefaultEstimate: 500000,     // Initial bandwidth estimate (500kbps)
          abrEwmaFastLive: 3.0,               // Faster adaptation for live streams
          maxStarvationDelay: 4,              // Max starvation delay when rebuffering
          maxLoadingDelay: 4,                 // Max loading delay
          startLevel: -1,                     // Auto-select starting quality
          fragLoadingTimeOut: 20000,          // Fragment loading timeout (ms)
          manifestLoadingTimeOut: 10000,      // Manifest loading timeout (ms)
          manifestLoadingMaxRetry: 4,         // Manifest loading retries
          fragLoadingMaxRetry: 6,             // Fragment loading retries
          levelLoadingTimeOut: 10000,         // Level loading timeout (ms)
          
          // More aggressive recovery from stalling
          fragLoadingRetryDelay: 500,         // Fragment retry delay (ms)
          
          // Auth header setup
          xhrSetup: function(xhr, url) {{
            xhr.setRequestHeader('Authorization', authHeader);
          }}
        }});
        
        hlsInstance.loadSource(cleanUrl);
        hlsInstance.attachMedia(video);
        
        // Set up buffer info update interval
        bufferUpdateInterval = setInterval(updateBufferInfo, 1000);
        
        hlsInstance.on(Hls.Events.MANIFEST_PARSED, function(event, data) {{
          updateStatus('connected', 'Connected');
          video.play();
          
          // Show stream quality information
          const levels = data.levels;
          if (levels && levels.length > 0) {{
            // Start with a reasonable quality level (not the highest)
            if (levels.length > 1) {{
              const midLevel = Math.floor(levels.length / 2);
              hlsInstance.currentLevel = midLevel;
            }}
            
            const level = levels[hlsInstance.currentLevel];
            streamInfo.textContent = 'Resolution: ' + level.width + 'x' + level.height + ', Bitrate: ' + Math.round(level.bitrate/1000) + ' kbps';
          }}
        }});
        
        // Track level switching for adaptive streaming
        hlsInstance.on(Hls.Events.LEVEL_SWITCHED, (event, data) => {{
          const levels = hlsInstance.levels;
          if (levels && levels.length > 0) {{
            const level = levels[data.level];
            streamInfo.textContent = 'Resolution: ' + level.width + 'x' + level.height + ', Bitrate: ' + Math.round(level.bitrate/1000) + ' kbps';
          }}
        }});
        
        // Handle fragment loading events
        hlsInstance.on(Hls.Events.FRAG_LOADED, () => {{
          if (bufferingCount > 0) {{
            // Reset buffering state when fragments load successfully
            bufferingCount = 0;
            streamInfo.textContent = streamInfo.textContent.replace(' [Buffering...]', '');
          }}
        }});
        
        hlsInstance.on(Hls.Events.ERROR, (event, data) => {{
          const now = Date.now();
          
          if (data.fatal) {{
            updateStatus('error', 'Error: ' + data.type);
            switch (data.type) {{
              case Hls.ErrorTypes.NETWORK_ERROR:
                if (autoReconnect && retryCount < maxRetries) {{
                  retryCount++;
                  setTimeout(() => createHlsPlayer(), 2000);
                }} else if (retryCount >= maxRetries) {{
                  updateStatus('error', 'Failed after ' + maxRetries + ' attempts');
                }}
                break;
            }}
          }} else if (data.details === Hls.ErrorDetails.BUFFER_STALLED_ERROR) {{
            // Handle buffering more intelligently
            bufferingCount++;
            
            // Only show buffering message if it's been at least 3 seconds since last one
            if (now - lastBufferingTime > 3000) {{
              streamInfo.textContent = streamInfo.textContent.replace(' [Buffering...]', '') + ' [Buffering...]';
              lastBufferingTime = now;
            }}
            
            // Only try to recover if buffering persists
            if (bufferingCount > 2) {{
              // Try to switch to a lower quality level if possible
              const currentLevel = hlsInstance.currentLevel;
              if (currentLevel > 0) {{
                hlsInstance.nextLevel = currentLevel - 1;
              }}
              
              // Also recover media error
              hlsInstance.recoverMediaError();
              bufferingCount = 0;
            }}
          }}
        }});
      }}
      
      if (Hls.isSupported()) {{
        // Give the browser a moment to initialize before starting playback
        setTimeout(() => {{
          createHlsPlayer();
        }}, 100);
      }} else if (video.canPlayType('application/vnd.apple.mpegurl')) {{
        // For Safari - we use XHR to handle auth instead of putting credentials in URL
        updateStatus('connecting', 'Connecting via native HLS...');
        const xhr = new XMLHttpRequest();
        xhr.open('GET', cleanUrl, true);
        xhr.setRequestHeader('Authorization', authHeader);
        xhr.onreadystatechange = function() {{
          if (xhr.readyState === 4) {{
            if (xhr.status === 200) {{
              video.src = cleanUrl;
              video.addEventListener('loadedmetadata', function() {{
                updateStatus('connected', 'Connected (Native HLS)');
                video.play();
              }});
            }} else {{
              updateStatus('error', 'Error: HTTP ' + xhr.status);
            }}
          }}
        }};
        xhr.send();
      }} else {{
        updateStatus('error', 'HLS not supported in this browser');
      }}
    </script>
    """

# Run the application
init_page_config()
config = collect_user_input()
valid, parsed, clean_url = validate_url(config["hls_url"])

if not valid:
    st.stop()

st.title("Live Surveillance Feed")

# Display description and instructions
st.markdown("""### Stream Instructions
- The stream will auto-connect when the page loads
- If connection fails, it will attempt to reconnect automatically
- Use the advanced settings to adjust buffer length for smoother playback
""")

# Embed player with updated configuration
player_html = build_player_html(config, clean_url)
html(player_html, height=600)

# Add a debug section at the bottom
with st.expander("Debug Information"):
    st.code(f"Clean URL: {clean_url}\nBuffer Length: {config['buffer_length']}s\nMax Buffer: {config['max_buffer_length']}s")
    if st.button("Force Refresh"):
        st.experimental_rerun()
