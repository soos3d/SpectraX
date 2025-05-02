#!/usr/bin/env python3
"""Compatibility wrapper for video-feed package.

This file preserves the original command interface for backward compatibility.
It simply imports and re-exports functionality from the videofeed package.
"""

# Import from the refactored package
from videofeed.cli import app

if __name__ == "__main__":
    app()
