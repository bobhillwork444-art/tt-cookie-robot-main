"""
Notification Manager for TT Cookie Robot
Handles in-app notifications with persistence.
"""
import json
import os
from datetime import datetime, timezone
from typing import List, Dict, Optional, Callable
from enum import Enum


class NotificationType(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"


class Notification:
    """Single notification object."""
    
    def __init__(self, 
                 message: str, 
                 notif_type: NotificationType = NotificationType.INFO,
                 title: str = "",
                 notif_id: str = None):
        self.id = notif_id or datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
        self.message = message
        self.title = title
        self.type = notif_type
        self.timestamp = datetime.now(timezone.utc)
        self.read = False
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "message": self.message,
            "title": self.title,
            "type": self.type.value,
            "timestamp": self.timestamp.isoformat(),
            "read": self.read
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Notification':
        notif = cls(
            message=data.get("message", ""),
            notif_type=NotificationType(data.get("type", "info")),
            title=data.get("title", ""),
            notif_id=data.get("id")
        )
        notif.read = data.get("read", False)
        try:
            notif.timestamp = datetime.fromisoformat(data.get("timestamp", ""))
        except:
            notif.timestamp = datetime.now(timezone.utc)
        return notif
    
    def get_icon(self) -> str:
        """Get emoji icon for notification type."""
        icons = {
            NotificationType.INFO: "ℹ️",
            NotificationType.WARNING: "⚠️",
            NotificationType.ERROR: "❌",
            NotificationType.SUCCESS: "✅"
        }
        return icons.get(self.type, "📢")
    
    def get_time_ago(self) -> str:
        """Get human-readable time since notification."""
        now = datetime.now(timezone.utc)
        diff = now - self.timestamp
        
        seconds = int(diff.total_seconds())
        
        if seconds < 60:
            return "just now"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes}m ago"
        elif seconds < 86400:
            hours = seconds // 3600
            return f"{hours}h ago"
        else:
            days = seconds // 86400
            return f"{days}d ago"


class NotificationManager:
    """Manages application notifications."""
    
    # Maximum notifications to keep
    MAX_NOTIFICATIONS = 50
    
    def __init__(self, base_dir: str = None):
        """
        Initialize notification manager.
        
        Args:
            base_dir: Base directory for persistence. Defaults to app directory.
        """
        if base_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        self.notifications_file = os.path.join(base_dir, "notifications.json")
        self._notifications: List[Notification] = []
        self._callbacks: List[Callable] = []
        
        # Load existing notifications
        self._load()
    
    def _load(self):
        """Load notifications from file."""
        try:
            if os.path.exists(self.notifications_file):
                with open(self.notifications_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._notifications = [
                        Notification.from_dict(n) for n in data.get("notifications", [])
                    ]
        except Exception as e:
            print(f"[Notifications] Error loading: {e}")
            self._notifications = []
    
    def _save(self):
        """Save notifications to file."""
        try:
            data = {
                "notifications": [n.to_dict() for n in self._notifications]
            }
            with open(self.notifications_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Notifications] Error saving: {e}")
    
    def _notify_callbacks(self):
        """Call all registered callbacks."""
        for callback in self._callbacks:
            try:
                callback()
            except Exception as e:
                print(f"[Notifications] Callback error: {e}")
    
    def on_change(self, callback: Callable):
        """Register a callback for notification changes."""
        self._callbacks.append(callback)
    
    def add(self, 
            message: str, 
            notif_type: NotificationType = NotificationType.INFO,
            title: str = "") -> Notification:
        """
        Add a new notification.
        
        Args:
            message: Notification message
            notif_type: Type of notification
            title: Optional title
            
        Returns:
            Created notification object
        """
        notif = Notification(message, notif_type, title)
        
        # Add to beginning (newest first)
        self._notifications.insert(0, notif)
        
        # Trim old notifications
        if len(self._notifications) > self.MAX_NOTIFICATIONS:
            self._notifications = self._notifications[:self.MAX_NOTIFICATIONS]
        
        self._save()
        self._notify_callbacks()
        
        return notif
    
    def add_warning(self, message: str, title: str = "") -> Notification:
        """Add a warning notification."""
        return self.add(message, NotificationType.WARNING, title)
    
    def add_error(self, message: str, title: str = "") -> Notification:
        """Add an error notification."""
        return self.add(message, NotificationType.ERROR, title)
    
    def add_success(self, message: str, title: str = "") -> Notification:
        """Add a success notification."""
        return self.add(message, NotificationType.SUCCESS, title)
    
    def add_info(self, message: str, title: str = "") -> Notification:
        """Add an info notification."""
        return self.add(message, NotificationType.INFO, title)
    
    def mark_read(self, notif_id: str):
        """Mark a notification as read."""
        for notif in self._notifications:
            if notif.id == notif_id:
                notif.read = True
                self._save()
                self._notify_callbacks()
                break
    
    def mark_all_read(self):
        """Mark all notifications as read."""
        changed = False
        for notif in self._notifications:
            if not notif.read:
                notif.read = True
                changed = True
        
        if changed:
            self._save()
            self._notify_callbacks()
    
    def delete(self, notif_id: str):
        """Delete a notification."""
        self._notifications = [n for n in self._notifications if n.id != notif_id]
        self._save()
        self._notify_callbacks()
    
    def clear_all(self):
        """Clear all notifications."""
        self._notifications = []
        self._save()
        self._notify_callbacks()
    
    def get_unread_count(self) -> int:
        """Get count of unread notifications."""
        return sum(1 for n in self._notifications if not n.read)
    
    def get_all(self) -> List[Notification]:
        """Get all notifications (newest first)."""
        return self._notifications.copy()
    
    def get_unread(self) -> List[Notification]:
        """Get only unread notifications."""
        return [n for n in self._notifications if not n.read]
    
    def has_unread(self) -> bool:
        """Check if there are unread notifications."""
        return any(not n.read for n in self._notifications)
    
    # === Auto Mode Specific Notifications ===
    
    def notify_daily_cycle_complete(self, summary: Dict):
        """Notify when daily cycle is complete."""
        msg = (
            f"Sessions completed: {summary.get('total_sessions', 0)}\n"
            f"Cookie: {summary.get('cookie_sessions', 0)} | "
            f"Google: {summary.get('google_sessions', 0)}\n"
            f"Errors: {summary.get('total_errors', 0)}"
        )
        self.add_success(msg, "Daily Cycle Complete")
    
    def notify_profile_errors(self, uuid: str, error_count: int, action: str):
        """Notify when profile has too many errors."""
        msg = (
            f"Profile {uuid[:8]}... has failed {error_count} times.\n"
            f"Action: {action}"
        )
        self.add_error(msg, "Profile Errors")
    
    def notify_not_enough_time(self, planned: int, actual: int, deficit: int):
        """Notify when there's not enough time for all profiles."""
        msg = (
            f"Planned sessions: {planned}\n"
            f"Possible today: {actual}\n"
            f"Deficit: {deficit} sessions\n\n"
            "Consider reducing profiles or sessions per profile."
        )
        self.add_warning(msg, "Schedule Overload")
