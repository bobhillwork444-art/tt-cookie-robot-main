#!/usr/bin/env python3
"""
Migration script: JSON files -> MongoDB Atlas
Run this once to migrate existing data to the database.
"""
import json
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import DatabaseManager


def load_json_file(filepath: str) -> dict:
    """Load JSON file safely."""
    try:
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
    return {}


def main():
    print("=" * 60)
    print("Cookie Robot - Migration to MongoDB Atlas")
    print("=" * 60)
    
    # Get base directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Load existing JSON files
    config_path = os.path.join(base_dir, "config.json")
    auto_state_path = os.path.join(base_dir, "auto_state.json")
    
    print(f"\nLoading JSON files from: {base_dir}")
    
    config = load_json_file(config_path)
    auto_state = load_json_file(auto_state_path)
    
    print(f"  config.json: {'Found' if config else 'Not found/empty'}")
    print(f"  auto_state.json: {'Found' if auto_state else 'Not found/empty'}")
    
    # Connect to database
    print("\nConnecting to MongoDB Atlas...")
    db = DatabaseManager()
    
    if not db.connect():
        print("\n❌ Failed to connect to MongoDB!")
        print("Please check your connection string and network.")
        return 1
    
    print("✓ Connected successfully")
    
    # Run migration
    print("\nStarting migration...")
    success = db.migrate_from_json(config, auto_state)
    
    # Show final stats
    print("\n" + "=" * 60)
    if success:
        print("✅ Migration completed successfully!")
        print("\nData now stored in MongoDB Atlas:")
        print(f"  Database: {db.DATABASE_NAME}")
        print("  Collections: settings, mode_settings, profiles, sites,")
        print("               youtube_queries, auto_state, daily_stats")
    else:
        print("⚠️ Migration completed with some errors.")
        print("Check the output above for details.")
    
    print("=" * 60)
    
    # Verify data
    print("\nVerification:")
    print(f"  Settings: {bool(db.get_settings())}")
    print(f"  Cookie profiles: {len(db.get_profiles('cookie'))}")
    print(f"  Google profiles: {len(db.get_profiles('google'))}")
    print(f"  Cookie sites: {len(db.get_sites('cookie_sites'))}")
    print(f"  Google sites: {len(db.get_sites('google_sites'))}")
    print(f"  YouTube queries: {len(db.get_youtube_queries())}")
    
    db.close()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
