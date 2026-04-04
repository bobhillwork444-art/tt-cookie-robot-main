"""
Version information for TT Cookie Robot.
This file is automatically updated by GitHub Actions during build.
"""

VERSION = "2.0.0"
BUILD_DATE = "2025-12-15"

def get_version() -> str:
    """Return the current version string."""
    return VERSION

def get_version_tuple() -> tuple:
    """Return version as tuple (major, minor, patch)."""
    parts = VERSION.split(".")
    return tuple(int(p) for p in parts[:3])
