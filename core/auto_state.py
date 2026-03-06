"""
Auto Mode State Manager
Handles persistence of auto mode state between sessions.
"""
import json
import os
from datetime import datetime, timezone
from typing import Dict, Optional, List
from pathlib import Path


class AutoStateManager:
    """Manages auto mode state persistence."""
    
    def __init__(self, base_dir: str = None):
        """
        Initialize state manager.
        
        Args:
            base_dir: Base directory for state files. Defaults to app directory.
        """
        if base_dir is None:
            # Default to cookie_robot directory
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        self.base_dir = base_dir
        self.state_file = os.path.join(base_dir, "auto_state.json")
        self.stats_dir = os.path.join(base_dir, "statistics")
        
        # Current state in memory
        self._state: Dict = {
            "date": "",
            "profiles": {},
            "auto_running": False,
            "auto_paused": False
        }
        
        # Load existing state
        self._load_state()
    
    def _load_state(self):
        """Load state from file."""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    
                    # Check if state is from today (UTC)
                    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                    if loaded.get("date") == today:
                        self._state = loaded
                    else:
                        # New day - reset counters but preserve some data
                        self._state = {
                            "date": today,
                            "profiles": {},
                            "auto_running": False,
                            "auto_paused": False
                        }
                        self._save_state()
        except Exception as e:
            print(f"[AutoState] Error loading state: {e}")
    
    def _save_state(self):
        """Save state to file."""
        try:
            # Update date
            self._state["date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self._state, f, indent=2, ensure_ascii=False)
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
        """Archive daily statistics to file."""
        try:
            if not date_str or date_str == "unknown":
                return
            
            # Parse date to get year-month for folder
            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                month_folder = date_obj.strftime("%Y-%m")
            except:
                month_folder = "unknown"
            
            # Create directory structure
            stats_month_dir = os.path.join(self.stats_dir, month_folder)
            os.makedirs(stats_month_dir, exist_ok=True)
            
            # Create stats file
            stats_file = os.path.join(stats_month_dir, f"{date_str}.txt")
            
            # Generate report
            summary = self.get_today_summary()
            profiles = self._state.get("profiles", {})
            
            report_lines = [
                f"=== Auto Mode Statistics: {date_str} ===",
                "",
                f"Total Sessions: {summary['total_sessions']}",
                f"  - Cookie Mode: {summary['cookie_sessions']}",
                f"  - Google Mode: {summary['google_sessions']}",
                f"Total Errors: {summary['total_errors']}",
                f"Profiles Worked: {summary['profiles_worked']}",
                "",
                "=== Profile Details ===",
                ""
            ]
            
            for uuid, data in profiles.items():
                sessions = data.get("sessions_today", 0)
                errors = data.get("errors_today", 0)
                mode = data.get("mode", "unknown")
                last = data.get("last_session", "N/A")
                
                report_lines.append(f"{uuid[:8]}... [{mode}]")
                report_lines.append(f"  Sessions: {sessions}, Errors: {errors}")
                report_lines.append(f"  Last: {last}")
                report_lines.append("")
            
            # Write to file
            with open(stats_file, "w", encoding="utf-8") as f:
                f.write("\n".join(report_lines))
            
            print(f"[AutoState] Archived stats to {stats_file}")
            
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
        
        Args:
            date_str: Date in YYYY-MM-DD format
            
        Returns:
            Contents of stats file or None if not found
        """
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            month_folder = date_obj.strftime("%Y-%m")
            stats_file = os.path.join(self.stats_dir, month_folder, f"{date_str}.txt")
            
            if os.path.exists(stats_file):
                with open(stats_file, "r", encoding="utf-8") as f:
                    return f.read()
        except Exception as e:
            print(f"[AutoState] Error reading stats: {e}")
        
        return None
    
    def get_available_stats_dates(self) -> List[str]:
        """Get list of dates for which statistics are available."""
        dates = []
        try:
            if os.path.exists(self.stats_dir):
                for month_folder in os.listdir(self.stats_dir):
                    month_path = os.path.join(self.stats_dir, month_folder)
                    if os.path.isdir(month_path):
                        for file in os.listdir(month_path):
                            if file.endswith(".txt"):
                                dates.append(file[:-4])  # Remove .txt
            dates.sort(reverse=True)  # Most recent first
        except Exception as e:
            print(f"[AutoState] Error listing stats: {e}")
        
        return dates
    
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
