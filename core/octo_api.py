"""
Octo Browser Local API integration
"""
import requests
import logging
import socks
import socket
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# Octo Remote API base URL
OCTO_REMOTE_API = "https://app.octobrowser.net/api/v2"


class OctoAPI:
    def __init__(self, local_port: int = 58888, api_token: str = ""):
        self.local_url = f"http://localhost:{local_port}"
        self.headers = {"Content-Type": "application/json"}
        self.api_token = api_token
        self.remote_headers = {
            "Content-Type": "application/json",
            "X-Octo-Api-Token": api_token
        }
    
    def set_api_token(self, token: str):
        """Set Octo API token for remote API access."""
        self.api_token = token
        self.remote_headers["X-Octo-Api-Token"] = token
    
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
    
    def get_active_profiles(self) -> Optional[list]:
        """Get list of currently active (running) profiles"""
        try:
            response = requests.get(
                f"{self.local_url}/api/profiles/active",
                headers=self.headers,
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                # Octo API returns {"data": [...]} or just [...]
                profiles = data.get("data", data) if isinstance(data, dict) else data
                return profiles if isinstance(profiles, list) else []
            return []
        except:
            return []
    
    def is_profile_running(self, profile_uuid: str) -> bool:
        """Check if a specific profile is currently running"""
        try:
            # First check active profiles list
            active = self.get_active_profiles()
            if active:
                for p in active:
                    # Check various possible UUID field names
                    uuid = p.get("uuid") or p.get("id") or p.get("profile_id") or ""
                    if uuid == profile_uuid:
                        return True
            
            # Fallback: try to get WS endpoint - if exists, profile is running
            response = requests.get(
                f"{self.local_url}/api/profiles/{profile_uuid}/ws",
                headers=self.headers,
                timeout=3
            )
            # If we get a valid response with ws_url, profile is running
            if response.status_code == 200:
                data = response.json()
                if data.get("ws_url") or data.get("port"):
                    return True
            return False
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
    
    def check_proxy(self, profile_uuid: str) -> Dict[str, Any]:
        """
        Check if profile's proxy is working using Remote API + direct connection test.
        Also determines country via IP geolocation.
        
        Args:
            profile_uuid: Profile UUID to check
            
        Returns:
            Dict with 'success': bool, 'message': str, 'ip': str, 'country': str
        """
        try:
            # Get proxy details from Remote API
            proxy_data = self.get_proxy_from_remote_api(profile_uuid)
            
            if not proxy_data:
                return {
                    "success": False,
                    "message": "Cannot get proxy data (check API token)",
                    "ip": "",
                    "country": ""
                }
            
            if not proxy_data.get("host"):
                return {
                    "success": False,
                    "message": "No proxy configured",
                    "ip": "",
                    "country": ""
                }
            
            # Test the proxy directly
            proxy_type = proxy_data.get("type", "socks5")
            host = proxy_data.get("host", "")
            port = proxy_data.get("port", 0)
            login = proxy_data.get("login", "")
            password = proxy_data.get("password", "")
            
            success, message, external_ip, country = self.test_proxy_connection_with_geo(
                proxy_type, host, port, login, password
            )
            
            return {
                "success": success,
                "message": message,
                "ip": external_ip if success else "",
                "country": country
            }
                
        except Exception as e:
            logger.debug(f"Check proxy error: {e}")
            return {
                "success": False,
                "message": str(e)[:50],
                "ip": "",
                "country": ""
            }
    
    def get_profile_country_from_remote_api(self, profile_uuid: str) -> str:
        """
        Get profile's proxy country using Octo Remote API.
        This works even when the profile has never been started.
        
        Args:
            profile_uuid: Profile UUID
            
        Returns:
            Country code (e.g., "US", "GB") or empty string
        """
        if not self.api_token:
            return ""
        
        try:
            # Get proxy details from Remote API
            response = requests.get(
                f"{OCTO_REMOTE_API}/automation/profiles/{profile_uuid}",
                headers=self.remote_headers,
                params={"fields": "proxy,geo"},
                timeout=15
            )
            
            if response.status_code != 200:
                return ""
            
            data = response.json()
            if not data.get("success") or not data.get("data"):
                return ""
            
            profile_data = data["data"]
            
            # Try multiple sources for country
            country = ""
            
            # 1. From proxy.externalIp.country or proxy.changeIpUrl (geo-targeted proxies)
            proxy = profile_data.get("proxy", {})
            if proxy:
                # Some proxies have country in external IP info
                ext_ip = proxy.get("externalIp", {})
                if ext_ip and isinstance(ext_ip, dict):
                    country = ext_ip.get("country", "")
                
                # Check proxy type - geo-targeted proxies often have country in config
                if not country:
                    country = proxy.get("country", "")
            
            # 2. From geo field
            if not country:
                geo = profile_data.get("geo", {})
                if geo:
                    country = geo.get("country", geo.get("countryCode", ""))
            
            # 3. From title (users sometimes put country in title)
            if not country:
                title = profile_data.get("title", "")
                if title:
                    # Check if title starts with 2-letter country code
                    parts = title.split()
                    if parts and len(parts[0]) == 2 and parts[0].isalpha():
                        country = parts[0].upper()
            
            print(f"[OctoAPI] Remote API country for {profile_uuid[:8]}: '{country}'")
            return country
            
        except Exception as e:
            print(f"[OctoAPI] Remote API country error: {e}")
            return ""
    
    def get_proxy_from_remote_api(self, profile_uuid: str) -> Optional[Dict]:
        """
        Get proxy details for a profile using Octo Remote API.
        
        Args:
            profile_uuid: Profile UUID
            
        Returns:
            Dict with proxy details or None
        """
        if not self.api_token:
            logger.warning("[OctoAPI] No API token set for remote API")
            return None
        
        try:
            # Octo Remote API - get specific profile
            response = requests.get(
                f"{OCTO_REMOTE_API}/automation/profiles/{profile_uuid}",
                headers=self.remote_headers,
                params={"fields": "proxy"},
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and data.get("data"):
                    return data["data"].get("proxy", {})
            
            logger.debug(f"[OctoAPI] Remote API response: {response.status_code}")
            return None
            
        except Exception as e:
            logger.error(f"[OctoAPI] Remote API error: {e}")
            return None
    
    def get_all_proxies_from_remote_api(self, profile_uuids: List[str]) -> Dict[str, Dict]:
        """
        Get proxy details for multiple profiles using Octo Remote API.
        
        Args:
            profile_uuids: List of profile UUIDs
            
        Returns:
            Dict mapping UUID to proxy data
        """
        if not self.api_token:
            logger.warning("[OctoAPI] No API token set for remote API")
            return {}
        
        result = {}
        
        try:
            # Octo Remote API - get profiles list with proxy field
            # We need to paginate through all profiles
            page = 0
            while True:
                response = requests.get(
                    f"{OCTO_REMOTE_API}/automation/profiles",
                    headers=self.remote_headers,
                    params={
                        "page": page,
                        "page_len": 100,
                        "fields": "proxy"
                    },
                    timeout=30
                )
                
                if response.status_code != 200:
                    break
                
                data = response.json()
                if not data.get("success") or not data.get("data"):
                    break
                
                profiles = data.get("data", [])
                for profile in profiles:
                    uuid = profile.get("uuid", "")
                    if uuid in profile_uuids:
                        result[uuid] = profile.get("proxy", {})
                
                # Check if we have all profiles or reached end
                if len(result) >= len(profile_uuids):
                    break
                
                total = data.get("total_count", 0)
                if (page + 1) * 100 >= total:
                    break
                
                page += 1
            
            return result
            
        except Exception as e:
            logger.error(f"[OctoAPI] Remote API batch error: {e}")
            return result
    
    def test_proxy_connection(self, proxy_type: str, host: str, port: int, 
                              login: str = "", password: str = "") -> tuple:
        """
        Test proxy connection by connecting to a test server.
        
        Args:
            proxy_type: "socks5", "socks4", "http"
            host: Proxy host
            port: Proxy port
            login: Proxy username (optional)
            password: Proxy password (optional)
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            if proxy_type.lower() in ["socks5", "socks"]:
                return self._test_socks5_proxy(host, port, login, password)
            elif proxy_type.lower() == "socks4":
                return self._test_socks4_proxy(host, port)
            elif proxy_type.lower() in ["http", "https"]:
                return self._test_http_proxy(host, port, login, password)
            else:
                return False, f"Unknown proxy type: {proxy_type}"
                
        except Exception as e:
            return False, str(e)[:50]
    
    def test_proxy_connection_with_geo(self, proxy_type: str, host: str, port: int, 
                                        login: str = "", password: str = "") -> tuple:
        """
        Test proxy connection and get external IP + country via geolocation.
        
        Args:
            proxy_type: "socks5", "socks4", "http"
            host: Proxy host
            port: Proxy port
            login: Proxy username (optional)
            password: Proxy password (optional)
            
        Returns:
            Tuple of (success: bool, message: str, external_ip: str, country: str)
        """
        try:
            if proxy_type.lower() in ["socks5", "socks"]:
                return self._test_socks5_proxy_with_geo(host, port, login, password)
            elif proxy_type.lower() == "socks4":
                success, msg = self._test_socks4_proxy(host, port)
                return success, msg, host if success else "", ""
            elif proxy_type.lower() in ["http", "https"]:
                return self._test_http_proxy_with_geo(host, port, login, password)
            else:
                return False, f"Unknown proxy type: {proxy_type}", "", ""
                
        except Exception as e:
            return False, str(e)[:50], "", ""
    
    def _get_ip_geolocation(self, proxy_url: str, proxy_type: str = "http") -> tuple:
        """
        Get external IP and country through proxy using ip-api.com.
        
        Returns:
            Tuple of (ip: str, country_code: str)
        """
        try:
            # Use ip-api.com - free, no API key required
            if proxy_type in ["socks5", "socks4"]:
                proxies = {
                    "http": proxy_url,
                    "https": proxy_url
                }
            else:
                proxies = {
                    "http": proxy_url,
                    "https": proxy_url
                }
            
            response = requests.get(
                "http://ip-api.com/json/?fields=query,countryCode",
                proxies=proxies,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                ip = data.get("query", "")
                country = data.get("countryCode", "")
                return ip, country
            
            return "", ""
            
        except Exception as e:
            print(f"[OctoAPI] Geolocation error: {e}")
            return "", ""
    
    def _test_socks5_proxy(self, host: str, port: int, login: str, password: str) -> tuple:
        """Test SOCKS5 proxy connectivity."""
        try:
            s = socks.socksocket()
            
            if login and password:
                s.set_proxy(socks.SOCKS5, host, port, username=login, password=password)
            else:
                s.set_proxy(socks.SOCKS5, host, port)
            
            s.settimeout(10)
            # Try to connect to Google DNS
            s.connect(("8.8.8.8", 53))
            s.close()
            return True, f"SOCKS5 OK ({host})"
            
        except socks.ProxyConnectionError as e:
            return False, f"Connection refused"
        except socks.SOCKS5AuthError as e:
            return False, f"Auth failed"
        except socket.timeout:
            return False, f"Timeout"
        except Exception as e:
            return False, str(e)[:30]
    
    def _test_socks5_proxy_with_geo(self, host: str, port: int, login: str, password: str) -> tuple:
        """Test SOCKS5 proxy connectivity and get geo info."""
        try:
            # First test basic connectivity
            s = socks.socksocket()
            
            if login and password:
                s.set_proxy(socks.SOCKS5, host, port, username=login, password=password)
            else:
                s.set_proxy(socks.SOCKS5, host, port)
            
            s.settimeout(10)
            s.connect(("8.8.8.8", 53))
            s.close()
            
            # Now get geo info through the proxy
            if login and password:
                proxy_url = f"socks5://{login}:{password}@{host}:{port}"
            else:
                proxy_url = f"socks5://{host}:{port}"
            
            external_ip, country = self._get_ip_geolocation(proxy_url, "socks5")
            
            if external_ip:
                return True, f"SOCKS5 OK", external_ip, country
            else:
                return True, f"SOCKS5 OK ({host})", host, ""
            
        except socks.ProxyConnectionError as e:
            return False, f"Connection refused", "", ""
        except socks.SOCKS5AuthError as e:
            return False, f"Auth failed", "", ""
        except socket.timeout:
            return False, f"Timeout", "", ""
        except Exception as e:
            return False, str(e)[:30], "", ""
    
    def _test_socks4_proxy(self, host: str, port: int) -> tuple:
        """Test SOCKS4 proxy connectivity."""
        try:
            s = socks.socksocket()
            s.set_proxy(socks.SOCKS4, host, port)
            s.settimeout(10)
            s.connect(("8.8.8.8", 53))
            s.close()
            return True, f"SOCKS4 OK ({host})"
            
        except Exception as e:
            return False, str(e)[:30]
    
    def _test_http_proxy(self, host: str, port: int, login: str, password: str) -> tuple:
        """Test HTTP proxy connectivity."""
        try:
            if login and password:
                proxy_url = f"http://{login}:{password}@{host}:{port}"
            else:
                proxy_url = f"http://{host}:{port}"
            
            proxies = {
                "http": proxy_url,
                "https": proxy_url
            }
            
            response = requests.get(
                "http://httpbin.org/ip",
                proxies=proxies,
                timeout=10
            )
            
            if response.status_code == 200:
                ip = response.json().get("origin", host)
                return True, f"HTTP OK ({ip})"
            else:
                return False, f"HTTP error: {response.status_code}"
                
        except requests.exceptions.Timeout:
            return False, "Timeout"
        except Exception as e:
            return False, str(e)[:30]
    
    def _test_http_proxy_with_geo(self, host: str, port: int, login: str, password: str) -> tuple:
        """Test HTTP proxy connectivity and get geo info."""
        try:
            if login and password:
                proxy_url = f"http://{login}:{password}@{host}:{port}"
            else:
                proxy_url = f"http://{host}:{port}"
            
            external_ip, country = self._get_ip_geolocation(proxy_url, "http")
            
            if external_ip:
                return True, f"HTTP OK", external_ip, country
            else:
                # Fallback - just test connectivity
                proxies = {
                    "http": proxy_url,
                    "https": proxy_url
                }
                response = requests.get(
                    "http://httpbin.org/ip",
                    proxies=proxies,
                    timeout=10
                )
                if response.status_code == 200:
                    ip = response.json().get("origin", host)
                    return True, f"HTTP OK ({ip})", ip, ""
                else:
                    return False, f"HTTP error: {response.status_code}", "", ""
                
        except requests.exceptions.Timeout:
            return False, "Timeout", "", ""
        except Exception as e:
            return False, str(e)[:30], "", ""

