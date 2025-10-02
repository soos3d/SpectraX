"""CLI interface for video-feed.

DEPRECATED: This module is deprecated. Use videofeed.surveillance instead.
All functionality has been moved to the surveillance module for better organization.

Usage:
    python -m videofeed.surveillance run      # Instead of: python -m videofeed.cli run
    python -m videofeed.surveillance detect   # Instead of: python -m videofeed.cli detect  
    python -m videofeed.surveillance reset    # Instead of: python -m videofeed.cli reset
"""

import typer
import warnings

# Import the new unified app
from videofeed.surveillance import app as surveillance_app

# Show deprecation warning
warnings.warn(
    "videofeed.cli is deprecated. Use 'python -m videofeed.surveillance' instead. "
    "All CLI commands have been moved to the surveillance module.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export the surveillance app for backward compatibility
app = surveillance_app


if __name__ == "__main__":
    app()
