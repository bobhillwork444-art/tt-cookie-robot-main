"""
MongoDB Database Manager for Cookie Robot
Handles all database operations for storing configurations, profiles, sites, and state.
"""
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError


class DatabaseManager:
    """
    Manages all MongoDB operations for Cookie Robot.
    
    Collections:
        - settings: Global application settings
        - mode_settings: Cookie/Google mode specific settings  
        - profiles: User profiles with mode assignment
        - sites: Site lists by category
        - youtube_queries: YouTube search keywords
        - auto_state: Auto mode state and profile session tracking
    """
    
    # Connection string - can be overridden via environment variable
    DEFAULT_CONNECTION_STRING = "mongodb+srv://bobhillwork444_db_user:gvQsCFhkQWzzrj3Y@cluster0.kixhzp5.mongodb.net/?appName=Cluster0"
    DATABASE_NAME = "cookie_robot"
    
    def __init__(self, connection_string: str = None):
        """
        Initialize database connection.
        
        Args:
            connection_string: MongoDB connection string. Uses default if not provided.
        """
        self.connection_string = connection_string or os.environ.get(
            "MONGODB_URI", 
            self.DEFAULT_CONNECTION_STRING
        )
        self.client = None
        self.db = None
        self._connected = False
        
    def connect(self) -> bool:
        """
        Establish connection to MongoDB.
        
        Returns:
            True if connection successful, False otherwise.
        """
        try:
            self.client = MongoClient(
                self.connection_string,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000
            )
            # Test connection
            self.client.admin.command('ping')
            self.db = self.client[self.DATABASE_NAME]
            self._connected = True
            print(f"[DB] Connected to MongoDB Atlas ({self.DATABASE_NAME})")
            return True
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            print(f"[DB] Connection failed: {e}")
            self._connected = False
            return False
        except Exception as e:
            print(f"[DB] Unexpected error: {e}")
            self._connected = False
            return False
    
    def is_connected(self) -> bool:
        """Check if database is connected."""
        return self._connected and self.db is not None
    
    def close(self):
        """Close database connection."""
        if self.client:
            self.client.close()
            self._connected = False
            print("[DB] Connection closed")
    
    # =========================================================================
    # SETTINGS
    # =========================================================================
    
    def get_settings(self) -> Dict:
        """Get global settings."""
        if not self.is_connected():
            return self._get_default_settings()
        
        try:
            settings = self.db.settings.find_one({"_id": "global"})
            if settings:
                settings.pop("_id", None)
                return settings
            return self._get_default_settings()
        except Exception as e:
            print(f"[DB] Error getting settings: {e}")
            return self._get_default_settings()
    
    def save_settings(self, settings: Dict) -> bool:
        """Save global settings."""
        if not self.is_connected():
            return False
        
        try:
            settings["_id"] = "global"
            settings["updated_at"] = datetime.now(timezone.utc)
            self.db.settings.replace_one(
                {"_id": "global"}, 
                settings, 
                upsert=True
            )
            return True
        except Exception as e:
            print(f"[DB] Error saving settings: {e}")
            return False
    
    def _get_default_settings(self) -> Dict:
        """Get default settings."""
        return {
            "api_url": "http://localhost:58888",
            "language": "Русский",
            "theme": "Dark",
            "max_parallel_profiles": 5,
            "base_delay_min": 1,
            "base_delay_max": 3,
            "geo_visiting_enabled": False,
            "geo_visiting_percent": 70,
            "max_session_duration": 900,
            "autosave_logs": False,
            "sessions_per_profile_min": 3,
            "sessions_per_profile_max": 4,
            "session_break_min": 60,
            "session_break_max": 150,
            "work_hours_weekday_start": 7,
            "work_hours_weekday_end": 23,
            "work_hours_weekend_start": 9,
            "work_hours_weekend_end": 23
        }
    
    # =========================================================================
    # MODE SETTINGS (Cookie / Google)
    # =========================================================================
    
    def get_mode_settings(self, mode: str) -> Dict:
        """
        Get settings for a specific mode.
        
        Args:
            mode: "cookie" or "google"
        """
        if not self.is_connected():
            return self._get_default_mode_settings(mode)
        
        try:
            settings = self.db.mode_settings.find_one({"_id": mode})
            if settings:
                settings.pop("_id", None)
                return settings
            return self._get_default_mode_settings(mode)
        except Exception as e:
            print(f"[DB] Error getting {mode} settings: {e}")
            return self._get_default_mode_settings(mode)
    
    def save_mode_settings(self, mode: str, settings: Dict) -> bool:
        """Save settings for a specific mode."""
        if not self.is_connected():
            return False
        
        try:
            settings["_id"] = mode
            settings["updated_at"] = datetime.now(timezone.utc)
            self.db.mode_settings.replace_one(
                {"_id": mode},
                settings,
                upsert=True
            )
            return True
        except Exception as e:
            print(f"[DB] Error saving {mode} settings: {e}")
            return False
    
    def _get_default_mode_settings(self, mode: str) -> Dict:
        """Get default mode settings."""
        if mode == "cookie":
            return {
                "min_time_on_site": 10,
                "max_time_on_site": 60,
                "sites_per_session_min": 4,
                "sites_per_session_max": 6,
                "google_search_percent": 70,
                "scroll_enabled": True,
                "scroll_percent": 90,
                "scroll_iterations_min": 2,
                "scroll_iterations_max": 6,
                "scroll_pixels_min": 50,
                "scroll_pixels_max": 150,
                "scroll_pause_min": 0.1,
                "scroll_pause_max": 0.5,
                "scroll_down_percent": 75,
                "click_links_enabled": True,
                "click_percent": 20,
                "max_clicks_per_site": 2,
                "human_behavior_enabled": True
            }
        else:  # google
            return {
                "min_time_on_site": 10,
                "max_time_on_site": 60,
                "sites_per_session_min": 4,
                "sites_per_session_max": 6,
                "google_search_percent": 70,
                "auth_on_sites": True,
                "read_gmail": True,
                "gmail_read_percent": 30,
                "gmail_read_time_min": 10,
                "gmail_read_time_max": 30,
                "gmail_promo_spam_percent": 20,
                "gmail_click_links": True,
                "gmail_check_sites_min": 4,
                "gmail_check_sites_max": 7,
                "gmail_final_check": True,
                "gmail_final_check_percent": 30,
                "youtube_enabled": True,
                "youtube_chance": 50,
                "youtube_videos_min": 1,
                "youtube_videos_max": 2,
                "youtube_watch_min": 15,
                "youtube_watch_max": 60,
                "youtube_like_percent": 20,
                "youtube_watchlater_percent": 15,
                "scroll_enabled": True,
                "scroll_percent": 90,
                "scroll_iterations_min": 2,
                "scroll_iterations_max": 6,
                "scroll_pixels_min": 50,
                "scroll_pixels_max": 150,
                "scroll_pause_min": 0.1,
                "scroll_pause_max": 0.5,
                "scroll_down_percent": 75,
                "click_links_enabled": True,
                "click_percent": 20,
                "max_clicks_per_site": 2
            }
    
    # =========================================================================
    # PROFILES
    # =========================================================================
    
    def get_profiles(self, mode: str = None) -> List[Dict]:
        """
        Get profiles as full dicts, optionally filtered by mode.
        
        Args:
            mode: "cookie", "google", or None for all
        """
        if not self.is_connected():
            return []
        
        try:
            query = {"mode": mode} if mode else {}
            profiles = list(self.db.profiles.find(query))
            # Remove MongoDB _id, use uuid as id
            for p in profiles:
                p["uuid"] = p.pop("_id")
            return profiles
        except Exception as e:
            print(f"[DB] Error getting profiles: {e}")
            return []
    
    def get_profile_uuids(self, mode: str = None) -> List[str]:
        """
        Get profile UUIDs only, optionally filtered by mode.
        This is for compatibility with existing code that expects list of strings.
        
        Args:
            mode: "cookie", "google", or None for all
        """
        if not self.is_connected():
            return []
        
        try:
            query = {"mode": mode} if mode else {}
            profiles = list(self.db.profiles.find(query, {"_id": 1}))
            return [p["_id"] for p in profiles]
        except Exception as e:
            print(f"[DB] Error getting profile UUIDs: {e}")
            return []
    
    def save_profile(self, profile: Dict) -> bool:
        """Save a single profile."""
        if not self.is_connected():
            return False
        
        try:
            uuid = profile.get("uuid")
            if not uuid:
                return False
            
            doc = profile.copy()
            doc["_id"] = uuid
            doc.pop("uuid", None)
            doc["updated_at"] = datetime.now(timezone.utc)
            
            self.db.profiles.replace_one(
                {"_id": uuid},
                doc,
                upsert=True
            )
            return True
        except Exception as e:
            print(f"[DB] Error saving profile: {e}")
            return False
    
    def save_profiles(self, profiles: List, mode: str) -> bool:
        """
        Save multiple profiles for a mode (replaces all profiles for that mode).
        
        Args:
            profiles: List of profile UUIDs (strings) or dicts with uuid field
            mode: "cookie" or "google"
        """
        if not self.is_connected():
            return False
        
        try:
            # Delete existing profiles for this mode
            self.db.profiles.delete_many({"mode": mode})
            
            # Insert new profiles
            if profiles:
                docs = []
                for p in profiles:
                    # Handle both string UUIDs and dict profiles
                    if isinstance(p, str):
                        # Simple UUID string
                        doc = {
                            "_id": p,
                            "uuid": p,
                            "mode": mode,
                            "updated_at": datetime.now(timezone.utc)
                        }
                    else:
                        # Dict with profile data
                        doc = p.copy()
                        doc["_id"] = doc.pop("uuid", doc.get("_id"))
                        doc["mode"] = mode
                        doc["updated_at"] = datetime.now(timezone.utc)
                    docs.append(doc)
                
                self.db.profiles.insert_many(docs)
            
            return True
        except Exception as e:
            print(f"[DB] Error saving profiles: {e}")
            return False
    
    def delete_profile(self, uuid: str) -> bool:
        """Delete a profile by UUID."""
        if not self.is_connected():
            return False
        
        try:
            self.db.profiles.delete_one({"_id": uuid})
            return True
        except Exception as e:
            print(f"[DB] Error deleting profile: {e}")
            return False
    
    # =========================================================================
    # SITES
    # =========================================================================
    
    def get_sites(self, category: str) -> List[str]:
        """
        Get sites for a category.
        
        Args:
            category: "cookie_sites", "google_sites", "browse_sites", "onetap_sites"
        """
        if not self.is_connected():
            return []
        
        try:
            doc = self.db.sites.find_one({"_id": category})
            if doc:
                return doc.get("urls", [])
            return []
        except Exception as e:
            print(f"[DB] Error getting sites ({category}): {e}")
            return []
    
    def save_sites(self, category: str, urls: List[str]) -> bool:
        """Save sites for a category."""
        if not self.is_connected():
            return False
        
        try:
            self.db.sites.replace_one(
                {"_id": category},
                {
                    "_id": category,
                    "urls": urls,
                    "count": len(urls),
                    "updated_at": datetime.now(timezone.utc)
                },
                upsert=True
            )
            return True
        except Exception as e:
            print(f"[DB] Error saving sites ({category}): {e}")
            return False
    
    # =========================================================================
    # YOUTUBE QUERIES
    # =========================================================================
    
    def get_youtube_queries(self) -> List[str]:
        """Get YouTube search keywords."""
        if not self.is_connected():
            return self._get_default_youtube_queries()
        
        try:
            doc = self.db.youtube_queries.find_one({"_id": "queries"})
            if doc:
                return doc.get("keywords", [])
            return self._get_default_youtube_queries()
        except Exception as e:
            print(f"[DB] Error getting YouTube queries: {e}")
            return self._get_default_youtube_queries()
    
    def save_youtube_queries(self, keywords: List[str]) -> bool:
        """Save YouTube search keywords."""
        if not self.is_connected():
            return False
        
        try:
            self.db.youtube_queries.replace_one(
                {"_id": "queries"},
                {
                    "_id": "queries",
                    "keywords": keywords,
                    "count": len(keywords),
                    "updated_at": datetime.now(timezone.utc)
                },
                upsert=True
            )
            return True
        except Exception as e:
            print(f"[DB] Error saving YouTube queries: {e}")
            return False
    
    def _get_default_youtube_queries(self) -> List[str]:
        """Get default YouTube queries."""
        return [
            "music", "news", "sports", "gaming", "cooking",
            "travel", "technology", "science", "nature", "comedy"
        ]
    
    # =========================================================================
    # AUTO STATE
    # =========================================================================
    
    def get_auto_state(self) -> Dict:
        """Get auto mode state."""
        if not self.is_connected():
            return self._get_default_auto_state()
        
        try:
            state = self.db.auto_state.find_one({"_id": "state"})
            if state:
                state.pop("_id", None)
                
                # Check if state is from today
                today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                if state.get("date") != today:
                    # New day - reset
                    state = self._get_default_auto_state()
                    self.save_auto_state(state)
                
                return state
            return self._get_default_auto_state()
        except Exception as e:
            print(f"[DB] Error getting auto state: {e}")
            return self._get_default_auto_state()
    
    def save_auto_state(self, state: Dict) -> bool:
        """Save auto mode state."""
        if not self.is_connected():
            return False
        
        try:
            state["_id"] = "state"
            state["date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            state["updated_at"] = datetime.now(timezone.utc)
            
            self.db.auto_state.replace_one(
                {"_id": "state"},
                state,
                upsert=True
            )
            return True
        except Exception as e:
            print(f"[DB] Error saving auto state: {e}")
            return False
    
    def _get_default_auto_state(self) -> Dict:
        """Get default auto state."""
        return {
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "auto_running": False,
            "auto_paused": False,
            "profiles": {},
            "skipped_profiles": {}
        }
    
    def update_profile_state(self, uuid: str, updates: Dict) -> bool:
        """
        Update specific fields in a profile's auto state.
        
        Args:
            uuid: Profile UUID
            updates: Dict of fields to update
        """
        if not self.is_connected():
            return False
        
        try:
            # Use dot notation to update nested profile
            update_fields = {f"profiles.{uuid}.{k}": v for k, v in updates.items()}
            
            self.db.auto_state.update_one(
                {"_id": "state"},
                {
                    "$set": update_fields,
                    "$currentDate": {"updated_at": True}
                },
                upsert=True
            )
            return True
        except Exception as e:
            print(f"[DB] Error updating profile state: {e}")
            return False
    
    # =========================================================================
    # STATISTICS (for archival)
    # =========================================================================
    
    def save_daily_stats(self, date_str: str, stats: Dict) -> bool:
        """Save daily statistics."""
        if not self.is_connected():
            return False
        
        try:
            stats["_id"] = date_str
            stats["archived_at"] = datetime.now(timezone.utc)
            
            self.db.daily_stats.replace_one(
                {"_id": date_str},
                stats,
                upsert=True
            )
            return True
        except Exception as e:
            print(f"[DB] Error saving daily stats: {e}")
            return False
    
    def get_daily_stats(self, date_str: str) -> Optional[Dict]:
        """Get statistics for a specific date."""
        if not self.is_connected():
            return None
        
        try:
            stats = self.db.daily_stats.find_one({"_id": date_str})
            if stats:
                stats.pop("_id", None)
                return stats
            return None
        except Exception as e:
            print(f"[DB] Error getting daily stats: {e}")
            return None
    
    def get_available_stats_dates(self) -> List[str]:
        """Get list of dates with available statistics."""
        if not self.is_connected():
            return []
        
        try:
            dates = self.db.daily_stats.distinct("_id")
            return sorted(dates, reverse=True)
        except Exception as e:
            print(f"[DB] Error getting stats dates: {e}")
            return []
    
    # =========================================================================
    # MIGRATION HELPER
    # =========================================================================
    
    def migrate_from_json(self, config: Dict, auto_state: Dict) -> bool:
        """
        Migrate data from JSON config to MongoDB.
        
        Args:
            config: Loaded config.json data
            auto_state: Loaded auto_state.json data
            
        Returns:
            True if migration successful
        """
        if not self.is_connected():
            print("[DB] Cannot migrate - not connected")
            return False
        
        print("[DB] Starting migration from JSON...")
        success = True
        
        try:
            # 1. Migrate global settings
            settings = {
                "api_url": config.get("api_url", "http://localhost:58888"),
                "language": config.get("language", "Русский"),
                "theme": config.get("theme", "Dark"),
                "max_parallel_profiles": config.get("max_parallel_profiles", 5),
                "base_delay_min": config.get("base_delay_min", 1),
                "base_delay_max": config.get("base_delay_max", 3),
                "geo_visiting_enabled": config.get("geo_visiting_enabled", False),
                "geo_visiting_percent": config.get("geo_visiting_percent", 70),
                "max_session_duration": config.get("max_session_duration", 900),
                "autosave_logs": config.get("autosave_logs", False),
                "sessions_per_profile_min": config.get("sessions_per_profile_min", 3),
                "sessions_per_profile_max": config.get("sessions_per_profile_max", 4),
                "session_break_min": config.get("session_break_min", 60),
                "session_break_max": config.get("session_break_max", 150),
                "work_hours_weekday_start": config.get("work_hours_weekday_start", 7),
                "work_hours_weekday_end": config.get("work_hours_weekday_end", 23),
                "work_hours_weekend_start": config.get("work_hours_weekend_start", 9),
                "work_hours_weekend_end": config.get("work_hours_weekend_end", 23)
            }
            if self.save_settings(settings):
                print("[DB] ✓ Migrated global settings")
            else:
                success = False
            
            # 2. Migrate mode settings
            for mode in ["cookie", "google"]:
                mode_key = f"{mode}_mode"
                if mode_key in config:
                    mode_settings = config[mode_key].get("settings", {})
                    if self.save_mode_settings(mode, mode_settings):
                        print(f"[DB] ✓ Migrated {mode} mode settings")
                    else:
                        success = False
            
            # 3. Migrate profiles
            for mode in ["cookie", "google"]:
                mode_key = f"{mode}_mode"
                if mode_key in config:
                    profiles = config[mode_key].get("profiles", [])
                    if profiles:
                        # Add mode to each profile
                        for p in profiles:
                            p["mode"] = mode
                        if self.save_profiles(profiles, mode):
                            print(f"[DB] ✓ Migrated {len(profiles)} {mode} profiles")
                        else:
                            success = False
            
            # 4. Migrate sites
            site_mappings = [
                ("cookie_mode", "sites", "cookie_sites"),
                ("google_mode", "sites", "google_sites"),
                ("google_mode", "browse_sites", "browse_sites"),
                ("google_mode", "onetap_sites", "onetap_sites"),
            ]
            
            for mode_key, sites_key, db_category in site_mappings:
                if mode_key in config:
                    sites = config[mode_key].get(sites_key, [])
                    if sites:
                        if self.save_sites(db_category, sites):
                            print(f"[DB] ✓ Migrated {len(sites)} {db_category}")
                        else:
                            success = False
            
            # 5. Migrate YouTube queries
            youtube_queries = config.get("youtube_queries", "")
            if youtube_queries:
                if isinstance(youtube_queries, str):
                    keywords = [q.strip() for q in youtube_queries.split(",") if q.strip()]
                else:
                    keywords = youtube_queries
                
                if self.save_youtube_queries(keywords):
                    print(f"[DB] ✓ Migrated {len(keywords)} YouTube queries")
                else:
                    success = False
            
            # 6. Migrate auto state
            if auto_state:
                if self.save_auto_state(auto_state):
                    print("[DB] ✓ Migrated auto state")
                else:
                    success = False
            
            print(f"[DB] Migration {'completed successfully' if success else 'completed with errors'}")
            return success
            
        except Exception as e:
            print(f"[DB] Migration error: {e}")
            return False


# Singleton instance
_db_instance: Optional[DatabaseManager] = None


def get_database() -> DatabaseManager:
    """Get the singleton database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseManager()
    return _db_instance
