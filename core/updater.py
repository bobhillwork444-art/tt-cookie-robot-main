"""
Auto-updater module for TT Cookie Robot.
Checks GitHub releases for updates and handles download/installation.
"""

import os
import sys
import json
import tempfile
import subprocess
import threading
import platform
from typing import Optional, Dict, Any
from urllib.request import urlopen, Request
from urllib.error import URLError

from version import VERSION

# GitHub repository info
GITHUB_OWNER = "bobhillwork444-art"
GITHUB_REPO = "tt-cookie-robot-main"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"

# For private repos, set this via environment variable or config
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")


class UpdateChecker:
    """Check for updates from GitHub releases."""
    
    def __init__(self, callback=None):
        """
        Initialize update checker.
        
        Args:
            callback: Optional callback function(result: dict) called when check completes
        """
        self.callback = callback
        self._checking = False
    
    def check_async(self):
        """Check for updates in background thread."""
        if self._checking:
            return
        
        self._checking = True
        thread = threading.Thread(target=self._check_thread, daemon=True)
        thread.start()
    
    def _check_thread(self):
        """Background thread for update check."""
        try:
            result = self.check_sync()
            if self.callback:
                self.callback(result)
        finally:
            self._checking = False
    
    def check_sync(self) -> Dict[str, Any]:
        """
        Check for updates synchronously.
        
        Returns:
            dict with keys:
                - available: bool - True if update available
                - version: str - Latest version (if available)
                - download_url: str - URL to download (if available)
                - release_notes: str - Release notes (if available)
                - error: str - Error message (if failed)
        """
        try:
            # Build request with optional auth for private repos
            headers = {
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "TT-Cookie-Robot-Updater"
            }
            if GITHUB_TOKEN:
                headers["Authorization"] = f"token {GITHUB_TOKEN}"
            
            request = Request(GITHUB_API_URL, headers=headers)
            
            with urlopen(request, timeout=15) as response:
                data = json.loads(response.read().decode())
            
            # Parse version from tag (remove 'v' prefix if present)
            latest_version = data.get("tag_name", "").lstrip("v")
            
            if not latest_version:
                return {"available": False, "error": "No version tag found"}
            
            # Compare versions
            if self._is_newer(latest_version, VERSION):
                # Find appropriate download URL for this platform
                download_url = self._get_download_url(data.get("assets", []))
                
                return {
                    "available": True,
                    "version": latest_version,
                    "current_version": VERSION,
                    "download_url": download_url,
                    "release_notes": data.get("body", ""),
                    "release_name": data.get("name", f"Version {latest_version}"),
                    "published_at": data.get("published_at", ""),
                    "html_url": data.get("html_url", "")
                }
            else:
                return {
                    "available": False,
                    "current_version": VERSION,
                    "latest_version": latest_version
                }
                
        except URLError as e:
            return {"available": False, "error": f"Network error: {str(e)}"}
        except json.JSONDecodeError as e:
            return {"available": False, "error": f"Invalid response: {str(e)}"}
        except Exception as e:
            return {"available": False, "error": f"Check failed: {str(e)}"}
    
    def _is_newer(self, remote: str, local: str) -> bool:
        """
        Compare version strings.
        
        Args:
            remote: Remote version (e.g., "2.1.0")
            local: Local version (e.g., "2.0.0")
            
        Returns:
            True if remote is newer than local
        """
        try:
            remote_parts = [int(x) for x in remote.split(".")[:3]]
            local_parts = [int(x) for x in local.split(".")[:3]]
            
            # Pad with zeros if needed
            while len(remote_parts) < 3:
                remote_parts.append(0)
            while len(local_parts) < 3:
                local_parts.append(0)
            
            return remote_parts > local_parts
        except (ValueError, AttributeError):
            return False
    
    def _get_download_url(self, assets: list) -> Optional[str]:
        """
        Find appropriate download URL for current platform.
        Prioritizes .exe over .zip for Windows, .dmg for macOS.
        
        Args:
            assets: List of release assets from GitHub API
            
        Returns:
            Download URL or None if not found
        """
        system = platform.system().lower()
        
        if system == "windows":
            # Priority 1: Find .exe installer (preferred)
            for asset in assets:
                name = asset.get("name", "").lower()
                if name.endswith(".exe"):
                    # Exclude macOS files
                    if "macos" not in name and "mac" not in name and "darwin" not in name:
                        return asset.get("browser_download_url")
            
            # Priority 2: Find .zip portable (fallback)
            for asset in assets:
                name = asset.get("name", "").lower()
                if name.endswith(".zip") and ("windows" in name or "win" in name):
                    return asset.get("browser_download_url")
                    
        elif system == "darwin":
            # Priority 1: Find .dmg
            for asset in assets:
                name = asset.get("name", "").lower()
                if name.endswith(".dmg"):
                    return asset.get("browser_download_url")
            
            # Priority 2: Find .zip for macOS (fallback)
            for asset in assets:
                name = asset.get("name", "").lower()
                if name.endswith(".zip") and ("macos" in name or "mac" in name or "darwin" in name):
                    return asset.get("browser_download_url")
        else:
            # Linux
            for asset in assets:
                name = asset.get("name", "").lower()
                if name.endswith(".AppImage") or name.endswith(".tar.gz"):
                    if "windows" not in name and "macos" not in name:
                        return asset.get("browser_download_url")
        
        # Final fallback: return first asset if no match
        if assets:
            return assets[0].get("browser_download_url")
        
        return None


class AutoUpdater:
    """Download and install updates."""
    
    def __init__(self, log_callback=None, progress_callback=None):
        """
        Initialize auto-updater.
        
        Args:
            log_callback: Optional callback(message: str) for logging
            progress_callback: Optional callback(percent: int, status: str) for progress
        """
        self.log = log_callback or print
        self.progress = progress_callback or (lambda p, s: None)
        self._downloading = False
        self._cancel_requested = False
    
    def download_and_install(self, download_url: str, version: str):
        """
        Download update and start installation in background.
        
        Args:
            download_url: URL to download the update from
            version: Version string for logging
        """
        if self._downloading:
            self.log("Download already in progress")
            return
        
        self._downloading = True
        self._cancel_requested = False
        
        thread = threading.Thread(
            target=self._download_thread,
            args=(download_url, version),
            daemon=True
        )
        thread.start()
    
    def cancel_download(self):
        """Request cancellation of current download."""
        self._cancel_requested = True
    
    def _download_thread(self, download_url: str, version: str):
        """Background thread for download and installation."""
        try:
            self.log(f"Starting download of version {version}...")
            self.progress(0, "Connecting...")
            
            # Determine file extension
            if download_url.endswith(".dmg"):
                ext = ".dmg"
            elif download_url.endswith(".zip"):
                ext = ".zip"
            else:
                ext = ".exe"
            
            # Create temp file
            temp_dir = tempfile.gettempdir()
            temp_file = os.path.join(temp_dir, f"TTCookieRobot_Update_{version}{ext}")
            
            # Build request
            headers = {"User-Agent": "TT-Cookie-Robot-Updater"}
            if GITHUB_TOKEN:
                headers["Authorization"] = f"token {GITHUB_TOKEN}"
            
            request = Request(download_url, headers=headers)
            
            # Download with progress
            with urlopen(request, timeout=300) as response:
                total_size = int(response.headers.get("Content-Length", 0))
                downloaded = 0
                chunk_size = 65536  # 64KB chunks
                
                with open(temp_file, "wb") as f:
                    while True:
                        if self._cancel_requested:
                            self.log("Download cancelled")
                            self.progress(0, "Cancelled")
                            return
                        
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0:
                            percent = int(downloaded * 100 / total_size)
                            size_mb = downloaded / (1024 * 1024)
                            total_mb = total_size / (1024 * 1024)
                            self.progress(percent, f"Downloading: {size_mb:.1f}/{total_mb:.1f} MB")
            
            self.log(f"Download complete: {temp_file}")
            self.progress(100, "Download complete")
            
            # Start installation
            self._install(temp_file, version)
            
        except Exception as e:
            self.log(f"Download failed: {str(e)}")
            self.progress(0, f"Error: {str(e)}")
        finally:
            self._downloading = False
    
    def _install(self, file_path: str, version: str):
        """
        Start installation process.
        
        Args:
            file_path: Path to downloaded file
            version: Version string for logging
        """
        system = platform.system().lower()
        
        self.log(f"Starting installation of version {version}...")
        self.progress(100, "Installing...")
        
        try:
            if system == "windows":
                self._install_windows(file_path)
            elif system == "darwin":
                self._install_macos(file_path)
            else:
                self.log("Automatic installation not supported on this platform")
                self.log(f"Please manually install from: {file_path}")
                
        except Exception as e:
            self.log(f"Installation failed: {str(e)}")
            self.log(f"Please manually install from: {file_path}")
    
    def _install_windows(self, file_path: str):
        """Install on Windows."""
        if file_path.endswith(".exe"):
            # Run installer
            self.log("Launching installer...")
            subprocess.Popen([file_path], shell=True)
            self.log("Please complete the installation wizard")
            # Exit current app to allow update
            self._schedule_exit()
            
        elif file_path.endswith(".zip"):
            # For portable version - extract and replace
            self.log("Portable update downloaded")
            self.log(f"Please extract {file_path} to replace current installation")
    
    def _install_macos(self, file_path: str):
        """Install on macOS."""
        if file_path.endswith(".dmg"):
            # Mount DMG and open
            self.log("Opening DMG file...")
            subprocess.Popen(["open", file_path])
            self.log("Please drag the app to Applications folder")
            self._schedule_exit()
    
    def _schedule_exit(self):
        """Schedule application exit after short delay."""
        import time
        self.log("Application will close in 3 seconds...")
        time.sleep(3)
        sys.exit(0)


# Convenience functions
def check_for_updates(callback=None) -> Optional[Dict[str, Any]]:
    """
    Check for updates.
    
    Args:
        callback: If provided, check runs async and calls callback with result.
                  If None, check runs synchronously and returns result.
    
    Returns:
        Result dict if sync, None if async
    """
    checker = UpdateChecker(callback=callback)
    
    if callback:
        checker.check_async()
        return None
    else:
        return checker.check_sync()


def get_current_version() -> str:
    """Return current version string."""
    return VERSION
