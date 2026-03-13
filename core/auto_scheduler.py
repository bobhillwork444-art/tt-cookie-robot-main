"""
Auto Mode Scheduler
Core scheduling logic for automatic profile management.
"""
import random
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class ProfileStatus(Enum):
    """Status of a profile in the scheduler."""
    SLEEPING = "sleeping"      # Outside working hours for this geo
    WAITING = "waiting"        # Ready to run, waiting for slot
    RUNNING = "running"        # Currently running
    COOLDOWN = "cooldown"      # Between sessions, cooling down
    COMPLETED = "completed"    # Done for today (reached session limit)
    SKIPPED = "skipped"        # Skipped due to errors
    MANUAL = "manual"          # Running manually by operator


@dataclass
class ScheduledProfile:
    """Profile with scheduling metadata."""
    uuid: str
    mode: str  # "cookie" or "google"
    country: str
    sessions_today: int = 0
    target_sessions: int = 0  # Daily target, set once per day
    errors_today: int = 0
    last_session_end: Optional[datetime] = None
    status: ProfileStatus = ProfileStatus.WAITING
    next_available: Optional[datetime] = None


# Timezone mapping: Country code -> UTC offset in hours
# Using representative timezone for each region
COUNTRY_TIMEZONES = {
    # North America - using CST (UTC-6) for US as requested
    'US': -6,  # CST (Central Standard Time)
    'CA': -5,  # EST (Eastern, most populated)
    'MX': -6,  # CST
    
    # Europe
    'GB': 0,   # GMT
    'IE': 0,   # GMT
    'PT': 0,   # WET
    'ES': 1,   # CET
    'FR': 1,   # CET
    'DE': 1,   # CET
    'IT': 1,   # CET
    'NL': 1,   # CET
    'BE': 1,   # CET
    'AT': 1,   # CET
    'CH': 1,   # CET
    'PL': 1,   # CET
    'CZ': 1,   # CET
    'SK': 1,   # CET
    'HU': 1,   # CET
    'SE': 1,   # CET
    'NO': 1,   # CET
    'DK': 1,   # CET
    'SI': 1,   # CET (Slovenia)
    'HR': 1,   # CET (Croatia)
    'RS': 1,   # CET (Serbia)
    'BA': 1,   # CET (Bosnia)
    'ME': 1,   # CET (Montenegro)
    'MK': 1,   # CET (North Macedonia)
    'AL': 1,   # CET (Albania)
    'XK': 1,   # CET (Kosovo)
    'LU': 1,   # CET (Luxembourg)
    'MT': 1,   # CET (Malta)
    'FI': 2,   # EET
    'EE': 2,   # EET
    'LV': 2,   # EET
    'LT': 2,   # EET
    'RO': 2,   # EET
    'BG': 2,   # EET
    'GR': 2,   # EET
    'CY': 2,   # EET (Cyprus)
    'UA': 2,   # EET
    'RU': 3,   # MSK (Moscow)
    
    # Asia
    'TR': 3,   # TRT
    'AE': 4,   # GST
    'IN': 5.5, # IST
    'TH': 7,   # ICT
    'VN': 7,   # ICT
    'SG': 8,   # SGT
    'MY': 8,   # MYT
    'PH': 8,   # PHT
    'HK': 8,   # HKT
    'TW': 8,   # CST
    'CN': 8,   # CST
    'KR': 9,   # KST
    'JP': 9,   # JST
    
    # Oceania
    'AU': 10,  # AEST (Eastern Australia)
    'NZ': 12,  # NZST
    
    # South America
    'BR': -3,  # BRT
    'AR': -3,  # ART
    'CL': -4,  # CLT
    'CO': -5,  # COT
    
    # Africa
    'ZA': 2,   # SAST
    'EG': 2,   # EET
    'NG': 1,   # WAT
    'KE': 3,   # EAT
}

# Country name to ISO code mapping (Octo API returns full names)
COUNTRY_NAME_TO_CODE = {
    "UNITED STATES": "US", "USA": "US", "UNITED STATES OF AMERICA": "US",
    "UNITED KINGDOM": "GB", "UK": "GB", "GREAT BRITAIN": "GB", "ENGLAND": "GB",
    "GERMANY": "DE", "DEUTSCHLAND": "DE",
    "FRANCE": "FR",
    "ITALY": "IT", "ITALIA": "IT",
    "SPAIN": "ES", "ESPANA": "ES",
    "NETHERLANDS": "NL", "THE NETHERLANDS": "NL", "HOLLAND": "NL",
    "POLAND": "PL", "POLSKA": "PL",
    "RUSSIA": "RU", "RUSSIAN FEDERATION": "RU",
    "UKRAINE": "UA",
    "CANADA": "CA",
    "AUSTRALIA": "AU",
    "JAPAN": "JP",
    "SOUTH KOREA": "KR", "KOREA": "KR",
    "CHINA": "CN",
    "BRAZIL": "BR", "BRASIL": "BR",
    "MEXICO": "MX",
    "ARGENTINA": "AR",
    "INDIA": "IN",
    "SINGAPORE": "SG",
    "SWEDEN": "SE",
    "NORWAY": "NO",
    "FINLAND": "FI",
    "DENMARK": "DK",
    "SWITZERLAND": "CH",
    "AUSTRIA": "AT",
    "BELGIUM": "BE",
    "PORTUGAL": "PT",
    "CZECH REPUBLIC": "CZ", "CZECHIA": "CZ",
    "GREECE": "GR",
    "TURKEY": "TR",
    "ISRAEL": "IL",
    "UNITED ARAB EMIRATES": "AE", "UAE": "AE",
    "SOUTH AFRICA": "ZA",
    "THAILAND": "TH",
    "VIETNAM": "VN",
    "INDONESIA": "ID",
    "MALAYSIA": "MY",
    "PHILIPPINES": "PH",
    "HONG KONG": "HK",
    "TAIWAN": "TW",
    "NEW ZEALAND": "NZ",
    "IRELAND": "IE",
    "ROMANIA": "RO",
    "HUNGARY": "HU",
    "SLOVAKIA": "SK",
    "BULGARIA": "BG",
    "CROATIA": "HR",
    "SERBIA": "RS",
    "LITHUANIA": "LT",
    "LATVIA": "LV",
    "ESTONIA": "EE",
    "CHILE": "CL",
    "COLOMBIA": "CO",
    "PERU": "PE",
    "SLOVENIA": "SI",
    "CYPRUS": "CY",
    "MALTA": "MT",
    "LUXEMBOURG": "LU",
    "ICELAND": "IS",
    "EGYPT": "EG",
    "NIGERIA": "NG",
    "KENYA": "KE",
}

# Default timezone for unknown countries
DEFAULT_TIMEZONE = 0  # UTC


class AutoScheduler:
    """
    Scheduler for Auto Mode.
    Manages profile scheduling based on timezones, session limits, and cooldowns.
    """
    
    def __init__(self, settings: Dict = None, auto_state = None):
        """
        Initialize scheduler.
        
        Args:
            settings: Auto mode settings dictionary
            auto_state: AutoStateManager instance for persisting target_sessions
        """
        self.settings = settings or {}
        self.auto_state = auto_state  # For persisting target_sessions
        self._profiles: Dict[str, ScheduledProfile] = {}
        self._running_profiles: List[str] = []
        self._manually_running: List[str] = []
        
        # Default settings
        self._load_settings()
    
    def _load_settings(self):
        """Load settings from dictionary."""
        # Working hours (in local time of profile)
        self.work_start_weekday = self.settings.get("work_start_weekday", 7)  # 7:00
        self.work_end_weekday = self.settings.get("work_end_weekday", 23)     # 23:00
        self.work_start_weekend = self.settings.get("work_start_weekend", 9)  # 9:00
        self.work_end_weekend = self.settings.get("work_end_weekend", 25)     # 01:00 next day (25 = 1:00)
        
        # Session limits
        self.sessions_min = self.settings.get("sessions_per_profile_min", 2)
        self.sessions_max = self.settings.get("sessions_per_profile_max", 4)
        
        # Cooldown between sessions (minutes)
        self.cooldown_min = self.settings.get("cooldown_min", 30)
        self.cooldown_max = self.settings.get("cooldown_max", 120)
        
        # Start time randomization (minutes)
        self.start_randomization = self.settings.get("start_randomization", 30)
        
        # Error handling
        self.max_errors = self.settings.get("max_errors", 3)
        self.error_action = self.settings.get("error_action", "skip_today")  # skip_today, skip_hour, notify
        
        # Max parallel profiles
        self.max_parallel = self.settings.get("max_parallel", 5)
    
    def update_settings(self, settings: Dict):
        """Update scheduler settings."""
        self.settings = settings
        self._load_settings()
    
    def _normalize_country_code(self, country: str) -> str:
        """Convert country name to ISO code if needed."""
        if not country:
            return ""
        
        country_upper = country.upper().strip()
        
        # If already a 2-letter ISO code, return as-is
        if len(country_upper) == 2 and country_upper in COUNTRY_TIMEZONES:
            return country_upper
        
        # Try to find in name mapping
        if country_upper in COUNTRY_NAME_TO_CODE:
            return COUNTRY_NAME_TO_CODE[country_upper]
        
        # Return original (will use default timezone)
        return country_upper
    
    def get_timezone_offset(self, country_code: str) -> float:
        """Get UTC offset for a country."""
        normalized = self._normalize_country_code(country_code)
        return COUNTRY_TIMEZONES.get(normalized, DEFAULT_TIMEZONE)
    
    def get_local_time(self, country_code: str) -> datetime:
        """Get current local time for a country."""
        utc_now = datetime.now(timezone.utc)
        offset_hours = self.get_timezone_offset(country_code)
        local_time = utc_now + timedelta(hours=offset_hours)
        return local_time
    
    def is_weekend(self, dt: datetime = None) -> bool:
        """Check if given datetime (or now UTC) is weekend."""
        if dt is None:
            dt = datetime.now(timezone.utc)
        return dt.weekday() >= 5  # Saturday = 5, Sunday = 6
    
    def is_profile_awake(self, country_code: str) -> bool:
        """
        Check if a profile should be "awake" based on its local time.
        
        Args:
            country_code: ISO country code (e.g., "US", "DE")
            
        Returns:
            True if profile is within working hours
        """
        # UNKNOWN country - always awake (need to start to detect real country)
        if country_code == "UNKNOWN" or not country_code:
            logging.info(f"[SCHEDULER_DEBUG] is_profile_awake({country_code}) = True (UNKNOWN, needs detection)")
            return True
        
        local_time = self.get_local_time(country_code)
        hour = local_time.hour + local_time.minute / 60.0
        
        # Determine working hours based on weekend
        is_wknd = self.is_weekend(local_time)
        if is_wknd:
            start = self.work_start_weekend
            end = self.work_end_weekend
        else:
            start = self.work_start_weekday
            end = self.work_end_weekday
        
        logging.info(f"[SCHEDULER_DEBUG] is_profile_awake({country_code}): local_time={local_time}, hour={hour:.2f}, weekend={is_wknd}, work_hours={start}-{end}")
        
        # Handle overnight schedules (e.g., 9:00 - 01:00 means work until 1 AM)
        if end > 24:
            # Overnight schedule: work from 'start' until midnight (24:00)
            # Early morning hours (00:00 to end-24) are NOT working hours
            # because we don't want to START new sessions after midnight
            # (that's "yesterday's late work", not "today's work")
            result = start <= hour < 24
        else:
            result = start <= hour < end
        
        logging.info(f"[SCHEDULER_DEBUG] is_profile_awake({country_code}) = {result}")
        return result
    
    def get_wake_time(self, country_code: str) -> Optional[datetime]:
        """
        Get the next wake time for a profile.
        
        Args:
            country_code: ISO country code
            
        Returns:
            Next datetime when profile will wake up, or None if already awake
        """
        if self.is_profile_awake(country_code):
            return None
        
        local_time = self.get_local_time(country_code)
        offset_hours = self.get_timezone_offset(country_code)
        
        # Determine start hour
        if self.is_weekend(local_time):
            start_hour = self.work_start_weekend
        else:
            start_hour = self.work_start_weekday
        
        # Calculate wake time
        wake_local = local_time.replace(hour=int(start_hour), minute=0, second=0, microsecond=0)
        
        # If we're past start time today, wake time is tomorrow
        if local_time.hour >= start_hour:
            wake_local += timedelta(days=1)
            # Check if tomorrow is weekend
            if self.is_weekend(wake_local):
                wake_local = wake_local.replace(hour=self.work_start_weekend)
            else:
                wake_local = wake_local.replace(hour=self.work_start_weekday)
        
        # Add randomization
        random_minutes = random.randint(-self.start_randomization, self.start_randomization)
        wake_local += timedelta(minutes=random_minutes)
        
        # Convert back to UTC
        wake_utc = wake_local - timedelta(hours=offset_hours)
        return wake_utc.replace(tzinfo=timezone.utc)
    
    def get_sleep_time(self, country_code: str) -> Optional[datetime]:
        """
        Get the time when profile will go to sleep.
        
        Args:
            country_code: ISO country code
            
        Returns:
            Datetime when profile will sleep, or None if already sleeping
        """
        if not self.is_profile_awake(country_code):
            return None
        
        local_time = self.get_local_time(country_code)
        offset_hours = self.get_timezone_offset(country_code)
        
        # Determine end hour
        if self.is_weekend(local_time):
            end_hour = self.work_end_weekend
        else:
            end_hour = self.work_end_weekday
        
        # Calculate sleep time
        if end_hour > 24:
            # Past midnight
            sleep_local = local_time.replace(hour=0, minute=0, second=0, microsecond=0)
            sleep_local += timedelta(days=1, hours=end_hour - 24)
        else:
            sleep_local = local_time.replace(hour=int(end_hour), minute=0, second=0, microsecond=0)
            if local_time.hour >= end_hour:
                sleep_local += timedelta(days=1)
        
        # Convert back to UTC
        sleep_utc = sleep_local - timedelta(hours=offset_hours)
        return sleep_utc.replace(tzinfo=timezone.utc)
    
    # === Profile Management ===
    
    def add_profile(self, uuid: str, mode: str, country: str, 
                    sessions_today: int = 0, errors_today: int = 0,
                    target_sessions: int = 0,
                    last_session_end: datetime = None):
        """Add a profile to the scheduler."""
        profile = ScheduledProfile(
            uuid=uuid,
            mode=mode,
            country=country,
            sessions_today=sessions_today,
            target_sessions=target_sessions,
            errors_today=errors_today,
            last_session_end=last_session_end
        )
        self._update_profile_status(profile)
        self._profiles[uuid] = profile
    
    def remove_profile(self, uuid: str):
        """Remove a profile from the scheduler."""
        if uuid in self._profiles:
            del self._profiles[uuid]
        if uuid in self._running_profiles:
            self._running_profiles.remove(uuid)
    
    def update_profile_country(self, uuid: str, new_country: str):
        """Update a profile's country (e.g., after proxy change)."""
        if uuid in self._profiles:
            old_country = self._profiles[uuid].country
            self._profiles[uuid].country = new_country
            logging.info(f"[SCHEDULER_DEBUG] Updated {uuid[:8]} country: {old_country} -> {new_country}")
            # Re-evaluate status with new country
            self._update_profile_status(self._profiles[uuid])
    
    def clear_profiles(self):
        """Clear all profiles."""
        self._profiles.clear()
        self._running_profiles.clear()
    
    def _update_profile_status(self, profile: ScheduledProfile):
        """Update profile status based on current state."""
        logging.info(f"[SCHEDULER_DEBUG] _update_profile_status: {profile.uuid[:8]}, country={profile.country}")
        
        # Check if manually running
        if profile.uuid in self._manually_running:
            profile.status = ProfileStatus.MANUAL
            logging.info(f"[SCHEDULER_DEBUG] {profile.uuid[:8]} -> MANUAL")
            return
        
        # Check if currently running
        if profile.uuid in self._running_profiles:
            profile.status = ProfileStatus.RUNNING
            logging.info(f"[SCHEDULER_DEBUG] {profile.uuid[:8]} -> RUNNING")
            return
        
        # Check error limit
        if profile.errors_today >= self.max_errors:
            profile.status = ProfileStatus.SKIPPED
            logging.info(f"[SCHEDULER_DEBUG] {profile.uuid[:8]} -> SKIPPED (errors)")
            return
        
        # Check session limit - target_sessions is set ONCE per day
        # If not set yet (0), generate random target
        if profile.target_sessions == 0:
            profile.target_sessions = random.randint(self.sessions_min, self.sessions_max)
            logging.info(f"[SCHEDULER_DEBUG] {profile.uuid[:8]} daily target set to {profile.target_sessions}")
            
            # Save to persistent state if available
            if self.auto_state:
                self.auto_state.set_profile_target_sessions(profile.uuid, profile.target_sessions)
        
        if profile.sessions_today >= profile.target_sessions:
            profile.status = ProfileStatus.COMPLETED
            logging.info(f"[SCHEDULER_DEBUG] {profile.uuid[:8]} -> COMPLETED ({profile.sessions_today}/{profile.target_sessions})")
            return
        
        # Check if sleeping (timezone)
        is_awake = self.is_profile_awake(profile.country)
        logging.info(f"[SCHEDULER_DEBUG] {profile.uuid[:8]} is_profile_awake({profile.country}) = {is_awake}")
        if not is_awake:
            profile.status = ProfileStatus.SLEEPING
            profile.next_available = self.get_wake_time(profile.country)
            logging.info(f"[SCHEDULER_DEBUG] {profile.uuid[:8]} -> SLEEPING")
            return
        
        # Check cooldown
        if profile.last_session_end:
            cooldown_minutes = random.randint(self.cooldown_min, self.cooldown_max)
            cooldown_end = profile.last_session_end + timedelta(minutes=cooldown_minutes)
            
            if datetime.now(timezone.utc) < cooldown_end:
                profile.status = ProfileStatus.COOLDOWN
                profile.next_available = cooldown_end
                logging.info(f"[SCHEDULER_DEBUG] {profile.uuid[:8]} -> COOLDOWN")
                return
        
        # Ready to run
        profile.status = ProfileStatus.WAITING
        profile.next_available = None
        logging.info(f"[SCHEDULER_DEBUG] {profile.uuid[:8]} -> WAITING")
    
    def update_all_statuses(self):
        """Update status for all profiles."""
        for profile in self._profiles.values():
            self._update_profile_status(profile)
    
    def get_profile(self, uuid: str) -> Optional[ScheduledProfile]:
        """Get a profile by UUID."""
        return self._profiles.get(uuid)
    
    def get_all_profiles(self) -> List[ScheduledProfile]:
        """Get all profiles."""
        return list(self._profiles.values())
    
    # === Scheduling Logic ===
    
    def get_available_slots(self) -> int:
        """Get number of available slots for new profiles."""
        running = len(self._running_profiles)
        return max(0, self.max_parallel - running)
    
    def get_profiles_to_start(self) -> List[ScheduledProfile]:
        """
        Get profiles that should be started now.
        Returns profiles respecting proportional distribution.
        """
        self.update_all_statuses()
        
        available_slots = self.get_available_slots()
        logging.info(f"[SCHEDULER_DEBUG] get_profiles_to_start: available_slots={available_slots}")
        if available_slots <= 0:
            return []
        
        # Log all profiles and their statuses
        for uuid, p in self._profiles.items():
            logging.info(f"[SCHEDULER_DEBUG] Profile {uuid[:8]}: country={p.country}, status={p.status.value}")
        
        # Get waiting profiles by mode
        waiting_cookie = [p for p in self._profiles.values() 
                         if p.status == ProfileStatus.WAITING and p.mode == "cookie"]
        waiting_google = [p for p in self._profiles.values() 
                         if p.status == ProfileStatus.WAITING and p.mode == "google"]
        
        logging.info(f"[SCHEDULER_DEBUG] waiting_cookie={len(waiting_cookie)}, waiting_google={len(waiting_google)}")
        
        total_waiting = len(waiting_cookie) + len(waiting_google)
        if total_waiting == 0:
            return []
        
        # Calculate proportional distribution
        cookie_ratio = len(waiting_cookie) / total_waiting if total_waiting > 0 else 0
        google_ratio = len(waiting_google) / total_waiting if total_waiting > 0 else 0
        
        # Distribute slots proportionally
        cookie_slots = round(available_slots * cookie_ratio)
        google_slots = available_slots - cookie_slots
        
        # Ensure at least 1 slot for non-empty queues
        if waiting_cookie and cookie_slots == 0 and available_slots > 0:
            cookie_slots = 1
            google_slots = available_slots - 1
        if waiting_google and google_slots == 0 and available_slots > 0:
            google_slots = 1
            cookie_slots = available_slots - 1
        
        # Select profiles (prioritize by longest wait / freshness)
        to_start = []
        
        # Sort by last session (oldest first = freshest for work)
        waiting_cookie.sort(key=lambda p: p.last_session_end or datetime.min.replace(tzinfo=timezone.utc))
        waiting_google.sort(key=lambda p: p.last_session_end or datetime.min.replace(tzinfo=timezone.utc))
        
        to_start.extend(waiting_cookie[:cookie_slots])
        to_start.extend(waiting_google[:google_slots])
        
        logging.info(f"[SCHEDULER_DEBUG] Returning {len(to_start)} profiles to start")
        return to_start
    
    def mark_profile_started(self, uuid: str):
        """Mark a profile as started."""
        if uuid in self._profiles:
            self._profiles[uuid].status = ProfileStatus.RUNNING
            if uuid not in self._running_profiles:
                self._running_profiles.append(uuid)
    
    def mark_profile_completed(self, uuid: str, success: bool = True):
        """Mark a profile session as completed."""
        if uuid in self._running_profiles:
            self._running_profiles.remove(uuid)
        
        profile = self._profiles.get(uuid)
        if profile:
            profile.last_session_end = datetime.now(timezone.utc)
            
            if success:
                profile.sessions_today += 1
                profile.errors_today = 0  # Reset error count on success
            else:
                profile.errors_today += 1
            
            self._update_profile_status(profile)
    
    def mark_profile_manual(self, uuid: str, is_manual: bool):
        """Mark a profile as manually running (by operator)."""
        if is_manual:
            if uuid not in self._manually_running:
                self._manually_running.append(uuid)
            # Remove from auto running if it was there
            if uuid in self._running_profiles:
                self._running_profiles.remove(uuid)
        else:
            if uuid in self._manually_running:
                self._manually_running.remove(uuid)
        
        if uuid in self._profiles:
            self._update_profile_status(self._profiles[uuid])
    
    # === Statistics ===
    
    def get_summary(self) -> Dict:
        """Get scheduler summary."""
        self.update_all_statuses()
        
        profiles = list(self._profiles.values())
        
        by_status = {}
        for status in ProfileStatus:
            by_status[status.value] = len([p for p in profiles if p.status == status])
        
        cookie_profiles = [p for p in profiles if p.mode == "cookie"]
        google_profiles = [p for p in profiles if p.mode == "google"]
        
        total_sessions_today = sum(p.sessions_today for p in profiles)
        cookie_sessions = sum(p.sessions_today for p in cookie_profiles)
        google_sessions = sum(p.sessions_today for p in google_profiles)
        
        # Calculate planned vs possible
        total_planned = len(profiles) * ((self.sessions_min + self.sessions_max) // 2)
        
        return {
            "total_profiles": len(profiles),
            "cookie_profiles": len(cookie_profiles),
            "google_profiles": len(google_profiles),
            "by_status": by_status,
            "running": len(self._running_profiles),
            "sessions_today": total_sessions_today,
            "cookie_sessions": cookie_sessions,
            "google_sessions": google_sessions,
            "planned_sessions": total_planned,
            "available_slots": self.get_available_slots()
        }
    
    def get_next_action_time(self) -> Tuple[Optional[datetime], str]:
        """
        Get time of next scheduled action.
        
        Returns:
            Tuple of (datetime, description)
        """
        self.update_all_statuses()
        
        # Find earliest next_available among cooldown and sleeping profiles
        next_time = None
        description = ""
        
        for profile in self._profiles.values():
            if profile.next_available:
                if next_time is None or profile.next_available < next_time:
                    next_time = profile.next_available
                    if profile.status == ProfileStatus.SLEEPING:
                        description = f"Wake up: {profile.country} profiles"
                    elif profile.status == ProfileStatus.COOLDOWN:
                        description = f"Cooldown end: {profile.uuid[:8]}..."
        
        # Check if we have waiting profiles (immediate action)
        waiting = [p for p in self._profiles.values() if p.status == ProfileStatus.WAITING]
        if waiting and self.get_available_slots() > 0:
            return (datetime.now(timezone.utc), f"Ready to start: {len(waiting)} profiles")
        
        return (next_time, description)
    
    def estimate_daily_capacity(self) -> Dict:
        """
        Estimate how many sessions can be completed today.
        
        Returns:
            Dictionary with capacity analysis
        """
        self.update_all_statuses()
        
        now = datetime.now(timezone.utc)
        
        total_remaining_sessions = 0
        profiles_with_time = 0
        profiles_no_time = 0
        
        for profile in self._profiles.values():
            # Skip already completed or skipped
            if profile.status in (ProfileStatus.COMPLETED, ProfileStatus.SKIPPED):
                continue
            
            # Get remaining sessions for this profile
            target = random.randint(self.sessions_min, self.sessions_max)
            remaining = max(0, target - profile.sessions_today)
            
            if remaining == 0:
                continue
            
            # Check if profile has time today
            sleep_time = self.get_sleep_time(profile.country)
            if sleep_time:
                # Estimate time needed for remaining sessions
                avg_session_duration = 15  # minutes (rough estimate)
                avg_cooldown = (self.cooldown_min + self.cooldown_max) // 2
                time_needed = remaining * (avg_session_duration + avg_cooldown)
                
                time_available = (sleep_time - now).total_seconds() / 60  # minutes
                
                if time_available >= time_needed:
                    total_remaining_sessions += remaining
                    profiles_with_time += 1
                else:
                    # Can only do partial
                    possible = int(time_available // (avg_session_duration + avg_cooldown))
                    total_remaining_sessions += possible
                    if possible < remaining:
                        profiles_no_time += 1
                    else:
                        profiles_with_time += 1
            else:
                # Profile is sleeping, check tomorrow
                profiles_no_time += 1
        
        return {
            "remaining_sessions": total_remaining_sessions,
            "profiles_with_time": profiles_with_time,
            "profiles_insufficient_time": profiles_no_time
        }
