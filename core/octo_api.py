"""
Octo Browser Local API integration
"""
import requests
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class OctoAPI:
    def __init__(self, local_port: int = 58888):
        self.local_url = f"http://localhost:{local_port}"
        self.headers = {"Content-Type": "application/json"}
    
    def test_connection(self) -> bool:
        try:
            response = requests.get(f"{self.local_url}/api/profiles/active", timeout=5)
            return response.status_code in [200, 404]
        except:
            return False
    
    def start_profile(self, profile_uuid: str, headless: bool = False, minimized: bool = True, 
                      disable_fedcm: bool = True, window_position: tuple = None) -> Optional[Dict[str, Any]]:
        """Start profile with optional minimized mode, FedCM disabled, and window position"""
        try:
            args = []
            if minimized:
                args.append("--start-minimized")
            
            # Set window position (for hiding off-screen)
            if window_position:
                x, y = window_position
                args.append(f"--window-position={x},{y}")
            
            # Disable FedCM to force Google One Tap to use iframe mode
            # This allows bot to interact with Google Sign-In popup
            if disable_fedcm:
                args.extend([
                    "--disable-features=FedCm,IdentityCredential,FedCmButtonMode",
                    "--disable-blink-features=FederatedCredentialManagement",
                ])
            
            # Use print for guaranteed output
            print(f"[OctoAPI] Starting profile {profile_uuid[:8]} with args: {args}")
            
            body = {
                "uuid": profile_uuid,
                "headless": headless,
                "debug_port": True,
                "args": args,
                "flags": args,  # Try both 'args' and 'flags' parameters
            }
            
            print(f"[OctoAPI] Request body keys: {list(body.keys())}")
            
            response = requests.post(
                f"{self.local_url}/api/profiles/start",
                headers=self.headers,
                json=body,
                timeout=60
            )
            
            print(f"[OctoAPI] Response: {response.status_code} - {response.text[:200]}")
            
            if response.status_code == 200:
                data = response.json()
                connection_data = data.get("connection_data", {})
                if connection_data:
                    ip = connection_data.get("ip")
                    country = connection_data.get("country")
                    if ip:
                        data["proxy_status"] = "ok"
                        data["proxy_info"] = f"{ip} ({country})"
                    else:
                        data["proxy_status"] = "error"
                        data["proxy_info"] = "No IP detected"
                else:
                    data["proxy_status"] = "unknown"
                    data["proxy_info"] = "No connection data"
                return data
            else:
                error_msg = response.json().get("msg", response.text)
                return {"error": error_msg, "proxy_status": "error"}
        except Exception as e:
            logger.error(f"Error: {e}")
            return {"error": str(e), "proxy_status": "error"}
    
    def stop_profile(self, profile_uuid: str) -> bool:
        """Stop a running profile"""
        try:
            response = requests.post(
                f"{self.local_url}/api/profiles/stop",
                headers=self.headers,
                json={"uuid": profile_uuid},
                timeout=10
            )
            return response.status_code == 200
        except:
            return False
    
    def force_stop_profile(self, profile_uuid: str) -> bool:
        """Force stop a running profile"""
        try:
            response = requests.post(
                f"{self.local_url}/api/profiles/stop",
                headers=self.headers,
                json={"uuid": profile_uuid, "force": True},
                timeout=10
            )
            return response.status_code == 200
        except:
            return False
    
    def get_profile_info(self, profile_uuid: str) -> Optional[Dict[str, Any]]:
        """Get profile information including proxy settings"""
        try:
            response = requests.post(
                f"{self.local_url}/api/profiles",
                headers=self.headers,
                json={"uuids": [profile_uuid]},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                profiles = data.get("data", [])
                if profiles:
                    profile = profiles[0]
                    
                    # Log full profile structure for debugging
                    print(f"[OctoAPI] Profile keys: {list(profile.keys())}")
                    
                    # Extract proxy info from multiple possible locations
                    proxy = profile.get("proxy", {})
                    proxy_type = proxy.get("type", "none")
                    
                    # Try to get country from various places
                    country = ""
                    # 1. Direct country field in proxy
                    if not country:
                        country = proxy.get("country", "")
                    # 2. Country in profile root
                    if not country:
                        country = profile.get("country", "")
                    # 3. Geo location data
                    if not country:
                        geo = profile.get("geo", {})
                        country = geo.get("country", geo.get("countryCode", ""))
                    # 4. From proxy host (some proxies have country in config)
                    if not country:
                        proxy_config = profile.get("proxyConfig", {})
                        country = proxy_config.get("country", "")
                    # 5. From tags (some users tag profiles with country)
                    if not country:
                        tags = profile.get("tags", [])
                        for tag in tags:
                            tag_upper = tag.upper() if isinstance(tag, str) else ""
                            if len(tag_upper) == 2 and tag_upper.isalpha():
                                country = tag_upper
                                break
                    
                    print(f"[OctoAPI] Profile {profile_uuid[:8]}: country='{country}', proxy={proxy}")
                    
                    return {
                        "uuid": profile_uuid,
                        "title": profile.get("title", profile_uuid[:8]),
                        "proxy_type": proxy_type,
                        "proxy_host": proxy.get("host", ""),
                        "country": country
                    }
            return None
        except Exception as e:
            logger.debug(f"Get profile info error: {e}")
            return None
