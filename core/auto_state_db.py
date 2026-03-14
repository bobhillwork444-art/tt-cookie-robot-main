"""
Auto Mode State Manager (MongoDB version)
Handles persistence of auto mode state using MongoDB Atlas.
"""
from datetime import datetime, timezone
from typing import Dict, Optional, List
from core.database import get_database, DatabaseManager


class AutoStateManager:
    """Manages auto mode state persistence via MongoDB."""
    
    def __init__(self, base_dir: str = None):
        """
        Initialize state manager.
        
        Args:
            base_dir: Ignored (kept for API compatibility). Data is stored in MongoDB.
        """
        self.db: DatabaseManager = get_database()
        self._connected = False
        
        # Local cache of state for performance
        self._state: Dict = {
            "date": "",
            "profiles": {},
            "skipped_profiles": {},
            "auto_running": False,
            "auto_paused": False
        }
        
        # Try to connect and load state
        self._connect_and_load()
    
    def _connect_and_load(self):
        """Connect to database and load initial state."""
        if not self.db.is_connected():
            self._connected = self.db.connect()
        else:
            self._connected = True
        
        if self._connected:
            self._load_state()
    
    def _load_state(self):
        """Load state from database."""
        if not self._connected:
            return
        
        try:
            loaded = self.db.get_auto_state()
            if loaded:
                # Check if state is from today (UTC)
                today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                if loaded.get("date") == today:
                    self._state = loaded
                else:
                    # New day - reset counters
                    # Archive old state first
                    if self._state.get("profiles"):
                        self._archive_daily_stats(self._state.get("date", "unknown"))
                    
                    self._state = {
                        "date": today,
                        "profiles": {},
                        "skipped_profiles": {},
                        "auto_running": False,
                        "auto_paused": False
                    }
                    self._save_state()
        except Exception as e:
            print(f"[AutoState] Error loading state: {e}")
    
    def _save_state(self):
        """Save state to database."""
        if not self._connected:
            return
        
        try:
            self._state["date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            self.db.save_auto_state(self._state)
        except Exception as e:
            print(f"[AutoState] Error saving state: {e}")
    
    def _check_day_reset(self):
        """Check if day changed and reset if needed."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if self._state.get("date") != today:
            # Archive yesterday's stats before reset
            if self._state.get("profiles"):
                self._archive_daily_stats(self._state.get("date", "unknown"))
            
            # Reset for new day
            self._state = {
                "date": today,
                "profiles": {},
                "skipped_profiles": {},
                "auto_running": self._state.get("auto_running", False),
                "auto_paused": self._state.get("auto_paused", False)
            }
            self._save_state()
    
    # === Profile Session Tracking ===
    
    def get_profile_sessions_today(self, uuid: str) -> int:
        """Get number of sessions completed today for a profile."""
        self._check_day_reset()
        profile_data = self._state.get("profiles", {}).get(uuid, {})
        return profile_data.get("sessions_today", 0)
    
    def increment_profile_session(self, uuid: str, mode: str):
        """Increment session count for a profile."""
        self._check_day_reset()
        
        if "profiles" not in self._state:
            self._state["profiles"] = {}
        
        if uuid not in self._state["profiles"]:
            self._state["profiles"][uuid] = {
                "sessions_today": 0,
                "errors_today": 0,
                "target_sessions": 0,
                "last_session": None,
                "mode": mode
            }
        
        self._state["profiles"][uuid]["sessions_today"] += 1
        self._state["profiles"][uuid]["last_session"] = datetime.now(timezone.utc).isoformat()
        self._state["profiles"][uuid]["mode"] = mode
        
        self._save_state()
    
    def get_last_session_time(self, uuid: str) -> Optional[datetime]:
        """Get last session time for a profile."""
        self._check_day_reset()
        profile_data = self._state.get("profiles", {}).get(uuid, {})
        last_session = profile_data.get("last_session")
        
        if last_session:
            try:
                return datetime.fromisoformat(last_session)
            except:
                pass
        return None
    
    def get_profile_target_sessions(self, uuid: str) -> int:
        """Get target sessions for a profile (set once per day)."""
        self._check_day_reset()
        profile_data = self._state.get("profiles", {}).get(uuid, {})
        return profile_data.get("target_sessions", 0)
    
    def set_profile_target_sessions(self, uuid: str, target: int):
        """Set target sessions for a profile (should be called once per day)."""
        self._check_day_reset()
        
        if "profiles" not in self._state:
            self._state["profiles"] = {}
        
        if uuid not in self._state["profiles"]:
            self._state["profiles"][uuid] = {
                "sessions_today": 0,
                "errors_today": 0,
                "target_sessions": 0,
                "last_session": None,
                "mode": ""
            }
        
        self._state["profiles"][uuid]["target_sessions"] = target
        self._save_state()
    
    # === Error Tracking ===
    
    def get_profile_errors_today(self, uuid: str) -> int:
        """Get number of errors today for a profile."""
        self._check_day_reset()
        profile_data = self._state.get("profiles", {}).get(uuid, {})
        return profile_data.get("errors_today", 0)
    
    def increment_profile_error(self, uuid: str):
        """Increment error count for a profile."""
        self._check_day_reset()
        
        if "profiles" not in self._state:
            self._state["profiles"] = {}
        
        if uuid not in self._state["profiles"]:
            self._state["profiles"][uuid] = {
                "sessions_today": 0,
                "errors_today": 0,
                "last_session": None,
                "mode": ""
            }
        
        self._state["profiles"][uuid]["errors_today"] += 1
        self._save_state()
    
    def reset_profile_errors(self, uuid: str):
        """Reset error count for a profile (after successful session)."""
        self._check_day_reset()
        
        if uuid in self._state.get("profiles", {}):
            self._state["profiles"][uuid]["errors_today"] = 0
            self._save_state()
    
    # === Auto Mode Status ===
    
    def is_auto_running(self) -> bool:
        """Check if auto mode is running."""
        return self._state.get("auto_running", False)
    
    def is_auto_paused(self) -> bool:
        """Check if auto mode is paused."""
        return self._state.get("auto_paused", False)
    
    def set_auto_running(self, running: bool):
        """Set auto mode running state."""
        self._state["auto_running"] = running
        if not running:
            self._state["auto_paused"] = False
        self._save_state()
    
    def set_auto_paused(self, paused: bool):
        """Set auto mode paused state."""
        self._state["auto_paused"] = paused
        self._save_state()
    
    # === Statistics ===
    
    def get_today_summary(self) -> Dict:
        """Get summary of today's activity."""
        self._check_day_reset()
        
        profiles = self._state.get("profiles", {})
        
        total_sessions = sum(p.get("sessions_today", 0) for p in profiles.values())
        total_errors = sum(p.get("errors_today", 0) for p in profiles.values())
        
        cookie_sessions = sum(
            p.get("sessions_today", 0) 
            for p in profiles.values() 
            if p.get("mode") == "cookie"
        )
        google_sessions = sum(
            p.get("sessions_today", 0) 
            for p in profiles.values() 
            if p.get("mode") == "google"
        )
        
        return {
            "date": self._state.get("date", ""),
            "total_sessions": total_sessions,
            "cookie_sessions": cookie_sessions,
            "google_sessions": google_sessions,
            "total_errors": total_errors,
            "profiles_worked": len([p for p in profiles.values() if p.get("sessions_today", 0) > 0])
        }
    
    def _archive_daily_stats(self, date_str: str):
        """Archive daily statistics to database."""
        try:
            if not date_str or date_str == "unknown":
                return
            
            if not self._connected:
                return
            
            summary = self.get_today_summary()
            profiles_data = {}
            
            for uuid, data in self._state.get("profiles", {}).items():
                profiles_data[uuid] = {
                    "sessions": data.get("sessions_today", 0),
                    "errors": data.get("errors_today", 0),
                    "mode": data.get("mode", "unknown"),
                    "last_session": data.get("last_session")
                }
            
            stats = {
                "date": date_str,
                "summary": summary,
                "profiles": profiles_data
            }
            
            self.db.save_daily_stats(date_str, stats)
            print(f"[AutoState] Archived stats for {date_str}")
            
        except Exception as e:
            print(f"[AutoState] Error archiving stats: {e}")
    
    def save_current_stats(self):
        """Force save current day's statistics (call at end of day or on stop)."""
        self._check_day_reset()
        date_str = self._state.get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        self._archive_daily_stats(date_str)
    
    def get_stats_for_date(self, date_str: str) -> Optional[str]:
        """
        Get statistics for a specific date.
        
        Returns formatted text report.
        """
        if not self._connected:
            return None
        
        try:
            stats = self.db.get_daily_stats(date_str)
            if not stats:
                return None
            
            # Format as text report
            summary = stats.get("summary", {})
            profiles = stats.get("profiles", {})
            
            report_lines = [
                f"=== Auto Mode Statistics: {date_str} ===",
                "",
                f"Total Sessions: {summary.get('total_sessions', 0)}",
                f"  - Cookie Mode: {summary.get('cookie_sessions', 0)}",
                f"  - Google Mode: {summary.get('google_sessions', 0)}",
                f"Total Errors: {summary.get('total_errors', 0)}",
                f"Profiles Worked: {summary.get('profiles_worked', 0)}",
                "",
                "=== Profile Details ===",
                ""
            ]
            
            for uuid, data in profiles.items():
                sessions = data.get("sessions", 0)
                errors = data.get("errors", 0)
                mode = data.get("mode", "unknown")
                last = data.get("last_session", "N/A")
                
                report_lines.append(f"{uuid[:8]}... [{mode}]")
                report_lines.append(f"  Sessions: {sessions}, Errors: {errors}")
                report_lines.append(f"  Last: {last}")
                report_lines.append("")
            
            return "\n".join(report_lines)
            
        except Exception as e:
            print(f"[AutoState] Error reading stats: {e}")
            return None
    
    def get_available_stats_dates(self) -> List[str]:
        """Get list of dates for which statistics are available."""
        if not self._connected:
            return []
        
        return self.db.get_available_stats_dates()
    
    # === Skipped Profiles (due to errors) ===
    
    def mark_profile_skipped(self, uuid: str, until: str = "today"):
        """
        Mark a profile as skipped.
        
        Args:
            uuid: Profile UUID
            until: "today" or ISO datetime string
        """
        if "skipped_profiles" not in self._state:
            self._state["skipped_profiles"] = {}
        
        self._state["skipped_profiles"][uuid] = {
            "until": until,
            "reason": "errors"
        }
        self._save_state()
    
    def is_profile_skipped(self, uuid: str) -> bool:
        """Check if a profile is currently skipped."""
        skipped = self._state.get("skipped_profiles", {}).get(uuid)
        if not skipped:
            return False
        
        until = skipped.get("until", "")
        
        if until == "today":
            # Skipped for today - check if still same day
            return self._state.get("date") == datetime.now(timezone.utc).strftime("%Y-%m-%d")
        else:
            # Skipped until specific time
            try:
                until_dt = datetime.fromisoformat(until)
                return datetime.now(timezone.utc) < until_dt
            except:
                return False
    
    def clear_profile_skip(self, uuid: str):
        """Clear skip status for a profile."""
        if "skipped_profiles" in self._state and uuid in self._state["skipped_profiles"]:
            del self._state["skipped_profiles"][uuid]
            self._save_state()
