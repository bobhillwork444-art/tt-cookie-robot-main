"""
Worker Thread - Background automation worker for profile processing
"""
import asyncio
from PyQt5.QtCore import QThread, pyqtSignal

from core.browser import BrowserAutomation


class WorkerThread(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str, str)
    country_detected = pyqtSignal(str, str)  # uuid, country_code
    
    def __init__(self, profile_uuid, sites, settings, octo_api, mode="cookie", start_minimized=True):
        super().__init__()
        self.profile_uuid = profile_uuid
        self.sites = sites
        self.settings = settings
        self.octo_api = octo_api
        self.mode = mode
        self.start_minimized = start_minimized
        self.should_stop = False
        self.automation = None
    
    def run(self):
        asyncio.run(self._run_async())
    
    async def _run_async(self):
        try:
            self.log_signal.emit(f"[{self.profile_uuid[:8]}] Starting ({self.mode})...")
            
            connection = self.octo_api.start_profile(
                self.profile_uuid, 
                minimized=self.start_minimized
            )
            
            if not connection:
                self.log_signal.emit(f"[{self.profile_uuid[:8]}] Failed to start")
                self.error_signal.emit(self.profile_uuid, "Failed to start profile")
                return
            
            if "error" in connection:
                self.log_signal.emit(f"[{self.profile_uuid[:8]}] Error: {connection.get('error')}")
                self.error_signal.emit(self.profile_uuid, connection.get("error"))
                return
            
            proxy_info = connection.get("proxy_info", "")
            
            # Extract and emit country from connection_data
            connection_data = connection.get("connection_data", {})
            country = connection_data.get("country", "")
            if country:
                self.country_detected.emit(self.profile_uuid, country)
            
            if connection.get("proxy_status") == "error" or not connection.get("ws_endpoint"):
                self.log_signal.emit(f"[{self.profile_uuid[:8]}] PROXY ERROR")
                self.octo_api.stop_profile(self.profile_uuid)
                return
            
            self.log_signal.emit(f"[{self.profile_uuid[:8]}] Proxy: {proxy_info}")
            
            ws_endpoint = connection.get("ws_endpoint")
            debug_port = connection.get("debug_port")
            
            if ws_endpoint or debug_port:
                self.automation = BrowserAutomation(
                    log_callback=lambda x: self.log_signal.emit(f"[{self.profile_uuid[:8]}] {x}")
                )
                
                try:
                    connected = await self.automation.connect_to_octo(ws_endpoint=ws_endpoint, debug_port=debug_port)
                except Exception as e:
                    self.log_signal.emit(f"[{self.profile_uuid[:8]}] Connection failed: {e}")
                    self.octo_api.stop_profile(self.profile_uuid)
                    return
                
                if connected:
                    # Try to minimize browser window if setting enabled
                    if self.start_minimized:
                        await self._try_minimize_browser()
                    
                    self.automation.should_stop = self.should_stop
                    try:
                        if self.mode == "cookie":
                            await self.automation.run_session(
                                sites=self.sites.copy(),
                                settings=self.settings
                            )
                        elif self.mode == "google":
                            await self.automation.run_google_warmup(
                                sites=self.sites.copy(),
                                settings=self.settings
                            )
                    except Exception as e:
                        self.log_signal.emit(f"[{self.profile_uuid[:8]}] Error: {e}")
                    await self.automation.disconnect()
            
            self.octo_api.stop_profile(self.profile_uuid)
            self.log_signal.emit(f"[{self.profile_uuid[:8]}] Done")
            
        except Exception as e:
            self.log_signal.emit(f"[{self.profile_uuid[:8]}] Error: {e}")
        finally:
            self.finished_signal.emit(self.profile_uuid)
    
    async def _try_minimize_browser(self):
        """Try to minimize browser window using CDP or pywin32."""
        try:
            # Small delay for browser to initialize
            await asyncio.sleep(0.3)
            
            if self.automation and self.automation.page:
                # Method 1: Use CDP to minimize window
                try:
                    cdp = await self.automation.page.context.new_cdp_session(self.automation.page)
                    # Get window bounds
                    window_id = await cdp.send("Browser.getWindowForTarget")
                    if window_id and window_id.get("windowId"):
                        # Set window state to minimized
                        await cdp.send("Browser.setWindowBounds", {
                            "windowId": window_id.get("windowId"),
                            "bounds": {"windowState": "minimized"}
                        })
                        self.log_signal.emit(f"[{self.profile_uuid[:8]}] Window minimized via CDP")
                        return
                except Exception as e:
                    self.log_signal.emit(f"[{self.profile_uuid[:8]}] CDP minimize failed: {e}")
                
                # Method 2: Use pywin32 on Windows
                try:
                    import win32gui
                    import win32con
                    
                    def minimize_by_title(title_part):
                        def callback(hwnd, results):
                            if win32gui.IsWindowVisible(hwnd):
                                window_title = win32gui.GetWindowText(hwnd)
                                if title_part.lower() in window_title.lower():
                                    win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                                    return False  # Stop enumeration
                            return True
                        win32gui.EnumWindows(callback, None)
                    
                    # Try to find Octo Browser window by profile UUID
                    minimize_by_title(self.profile_uuid[:8])
                    self.log_signal.emit(f"[{self.profile_uuid[:8]}] Window minimized via pywin32")
                except ImportError:
                    pass  # pywin32 not available
                    
        except Exception as e:
            self.log_signal.emit(f"[{self.profile_uuid[:8]}] Minimize failed: {e}")
    
    def stop(self):
        self.should_stop = True
        if self.automation:
            self.automation.should_stop = True
