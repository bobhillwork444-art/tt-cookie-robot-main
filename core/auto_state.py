"""
Auto Mode State Manager
Handles persistence of auto mode state between sessions.

This module now uses MongoDB for storage. The AutoStateManager class
is imported from auto_state_db.py which handles all database operations.
"""

# Import MongoDB-backed implementation
from core.auto_state_db import AutoStateManager

# Re-export for compatibility
__all__ = ['AutoStateManager']
