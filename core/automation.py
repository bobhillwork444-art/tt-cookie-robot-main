"""
Browser automation with network-level audio blocking
"""
import asyncio
import random
import logging
import time
import re
from typing import List, Optional, Callable
from playwright.async_api import async_playwright, Page, Browser, Route

# URL parsing for Google search navigation
try:
    import tldextract
except ImportError:
    tldextract = None

# Import the new Google Auth module
from core.google_auth import (
    GoogleAuthManager,
    GoogleAuthConfig,
    is_google_auth_url,
    find_google_button_and_click,
    find_login_button_and_click,
    is_logged_in as google_is_logged_in,
)

logger = logging.getLogger(__name__)

# === COOKIE CONSENT ===
COOKIE_SELECTORS = [
    '#accept-cookies', '#acceptCookies', '#cookie-accept', '#cookieAccept',
    '#accept-all', '#acceptAll', '#accept_all', '#onetrust-accept-btn-handler',
    '#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll',
    '#didomi-notice-agree-button', '#consent-accept', '#cookie-consent-accept',
    '#tarteaucitronPersonalize2', '#axeptio_btn_acceptAll',
    '.accept-cookies', '.accept-all', '.cookie-accept', '.consent-accept',
    '.agree-button', '.accept-button', '.cookie-agree', '.cookies-accept',
    '[data-action="accept"]', '[data-consent="accept"]',
    'button[data-gdpr-expression="acceptAll"]',
]

COOKIE_BUTTON_TEXTS = [
    'Accept', 'Accept all', 'Accept All', 'Accept cookies', 'Accept Cookies',
    'Agree', 'Agree all', 'Agree All', 'I agree', 'I Agree', 'Agree and close',
    'OK', 'Ok', 'Okay', 'Got it', 'Got It',
    'Allow', 'Allow all', 'Allow All', 'Allow cookies',
    'Continue', 'Understood', 'I understand',
    'Accepter', 'Tout accepter', "J'accepte", 'Autoriser', 'Continuer',
    'Accepter et continuer', 'Accepter et fermer', 'Accepter tout',
    'Akzeptieren', 'Alle akzeptieren', 'Zustimmen', 'Alles akzeptieren',
    'Aceptar', 'Aceptar todo', 'Acepto', 'Aceptar todas',
    'Accetta', 'Accetta tutto', 'Accetto',
    'Aceitar', 'Aceitar tudo',
    'Принять', 'Принять все', 'Согласен', 'Согласиться', 'ОК', 'Понятно',
]

CLOSE_SELECTORS = [
    'button[aria-label="Close"]', 'button[aria-label="close"]',
    'button[aria-label="Fermer"]', '[aria-label="Close"]',
    '.close-button', '.close-btn', '.btn-close', '.modal-close',
    '[data-dismiss="modal"]', '[data-close]',
]

CLOSE_TEXTS = [
    'Close', 'X', '×', '✕', '✖', '✗',
    'Dismiss', 'Cancel', 'No thanks', 'Not now', 'Later', 'Skip',
    'Fermer', 'Non merci', 'Schließen', 'Cerrar', 'Закрыть',
]

# Audio/Video file patterns to block
BLOCKED_MEDIA_PATTERNS = [
    r'\.mp3(\?|$)',
    r'\.mp4(\?|$)',
    r'\.webm(\?|$)',
    r'\.ogg(\?|$)',
    r'\.wav(\?|$)',
    r'\.m4a(\?|$)',
    r'\.aac(\?|$)',
    r'\.flac(\?|$)',
    r'\.m3u8(\?|$)',  # HLS streams
    r'\.mpd(\?|$)',   # DASH streams
    r'/videoplayback',  # YouTube-style
    r'/audio/',
    r'googlevideo\.com',
    r'doubleclick\.net.*video',
    r'googleads.*video',
]

# Ad domains to block (they often have autoplay videos)
BLOCKED_AD_DOMAINS = [
    'doubleclick.net',
    'googlesyndication.com',
    'googleadservices.com',
    'moatads.com',
    'amazon-adsystem.com',
    'facebook.com/tr',
    'adnxs.com',
    'rubiconproject.com',
    'pubmatic.com',
    'openx.net',
    'casalemedia.com',
    'outbrain.com',
    'taboola.com',
    'criteo.com',
    'teads.tv',
    'smartadserver.com',
]

# === YOUTUBE ACTIVITY CONSTANTS ===
YOUTUBE_SEARCH_WORDS = [
    'music', 'gaming', 'vlog', 'tutorial', 'review', 'unboxing', 'podcast', 
    'documentary', 'interview', 'prank', 'challenge', 'workout', 'meditation', 
    'cooking', 'baking', 'travel', 'animation', 'trailer', 'reaction', 
    'livestream', 'news', 'highlights', 'compilation', 'remix', 'cover', 
    'parody', 'experiment', 'science', 'technology', 'programming', 'coding', 
    'design', 'photography', 'cinematography', 'editing', 'marketing', 'finance', 
    'investing', 'crypto', 'stocks', 'motivation', 'inspiration', 'speech', 
    'debate', 'politics', 'history', 'geography', 'psychology', 'philosophy', 
    'education', 'math', 'algebra', 'calculus', 'physics', 'chemistry', 
    'biology', 'astronomy', 'nature', 'wildlife', 'ocean', 'space', 'nasa', 
    'spacex', 'robotics', 'ai', 'gadgets', 'smartphones', 'laptops', 'cars', 
    'supercars', 'motorcycles', 'fashion', 'makeup', 'skincare', 'fitness', 
    'yoga', 'pilates', 'boxing', 'football', 'basketball', 'soccer', 'tennis', 
    'golf', 'baseball', 'hockey', 'esports', 'minecraft', 'fortnite', 'roblox', 
    'gta', 'minecraftmods', 'speedrun', 'walkthrough', 'gameplay', 'strategy', 
    'tips', 'hacks', 'secrets', 'bloopers', 'fails', 'memes', 'shorts', 
    'tiktok', 'reels', 'aesthetic', 'ambience', 'lofi', 'jazz', 'rock', 'pop', 
    'classical', 'metal', 'hiphop', 'rap', 'country', 'reggae', 'blues', 
    'instrumental', 'karaoke', 'orchestra', 'piano', 'guitar', 'drums', 
    'violin', 'singing', 'dance', 'choreography', 'ballet', 'salsa', 'tango', 
    'kpop', 'anime', 'manga', 'marvel', 'dc', 'starwars', 'harrypotter', 
    'disney', 'pixar', 'netflix', 'series', 'movie', 'horror', 'thriller', 
    'comedy', 'drama', 'action', 'adventure', 'fantasy', 'mystery', 'crime', 
    'detective', 'survival', 'camping', 'fishing', 'hunting', 'diy', 'crafts', 
    'woodworking', 'gardening', 'farming', 'minimalism', 'productivity', 
    'startup', 'entrepreneurship', 'freelancing', 'remote', 'codinglife', 
    'debugging', 'cybersecurity', 'hacking', 'privacy', 'blockchain', 'web3', 
    'ecommerce', 'dropshipping', 'amazon', 'shopify', 'branding', 'storytelling', 
    'voiceover', 'asmr', 'relaxation', 'sleep', 'thunder', 'rain', 'fireplace', 
    'timelapse', 'sunrise', 'sunset', 'mountains', 'forest', 'desert', 'island', 
    'waterfall', 'volcano', 'earthquake', 'tornado', 'hurricane', 'tsunami',
]

# === GEO DOMAIN CONSTANTS FOR AUTOMATION ===
# EU member states TLDs (27 countries)
EU_TLDS = {
    'at', 'be', 'bg', 'hr', 'cy', 'cz', 'dk', 'ee', 'fi', 'fr',
    'de', 'gr', 'hu', 'ie', 'it', 'lv', 'lt', 'lu', 'mt', 'nl',
    'pl', 'pt', 'ro', 'sk', 'si', 'es', 'se'
}

# Generic TLDs (not country-specific)
GENERIC_TLDS = {
    'com', 'org', 'net', 'io', 'xyz', 'info', 'biz', 'co', 'app',
    'dev', 'ai', 'tech', 'online', 'site', 'website', 'blog', 'shop',
    'store', 'cloud', 'digital', 'media', 'news', 'tv', 'fm', 'me'
}

# Country code to TLD mapping (expanded)
COUNTRY_TO_TLD = {
    'US': ['us', 'com'],  # US includes .com as local
    'GB': ['uk', 'co.uk'],
    'CA': ['ca'],
    'AU': ['au', 'com.au'],
    'NZ': ['nz', 'co.nz'],
    # EU countries
    'DE': ['de'], 'FR': ['fr'], 'IT': ['it'], 'ES': ['es'],
    'NL': ['nl'], 'PL': ['pl'], 'PT': ['pt'], 'AT': ['at'],
    'BE': ['be'], 'SE': ['se'], 'FI': ['fi'], 'DK': ['dk'],
    'CZ': ['cz'], 'GR': ['gr'], 'RO': ['ro'], 'HU': ['hu'],
    'SK': ['sk'], 'BG': ['bg'], 'HR': ['hr'], 'SI': ['si'],
    'LT': ['lt'], 'LV': ['lv'], 'EE': ['ee'], 'IE': ['ie'],
    'CY': ['cy'], 'MT': ['mt'], 'LU': ['lu'],
    # Non-EU Europe
    'CH': ['ch'], 'NO': ['no'], 'IS': ['is'],
    'RU': ['ru'], 'UA': ['ua'], 'BY': ['by'], 'MD': ['md'],
    'RS': ['rs'], 'ME': ['me'], 'MK': ['mk'], 'AL': ['al'], 'BA': ['ba'],
    # Middle East & Asia
    'TR': ['tr'], 'IL': ['il'], 'AE': ['ae'], 'SA': ['sa'], 'QA': ['qa'],
    'JP': ['jp'], 'KR': ['kr'], 'CN': ['cn'], 'IN': ['in'],
    'TH': ['th'], 'VN': ['vn'], 'ID': ['id'], 'MY': ['my'], 'PH': ['ph'],
    'SG': ['sg'], 'HK': ['hk'], 'TW': ['tw'],
    # Americas
    'BR': ['br', 'com.br'], 'MX': ['mx'], 'AR': ['ar'],
    'CL': ['cl'], 'CO': ['co'], 'PE': ['pe'], 'VE': ['ve'],
    # Africa
    'ZA': ['za', 'co.za'], 'EG': ['eg'], 'NG': ['ng'], 'KE': ['ke'],
    'MA': ['ma'], 'DZ': ['dz'], 'TN': ['tn'],
}

# Country name to code mapping for normalization (full list)
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
    "MONACO": "MC",
    "ANDORRA": "AD",
    "LIECHTENSTEIN": "LI",
    "SAN MARINO": "SM",
    "MONTENEGRO": "ME",
    "NORTH MACEDONIA": "MK", "MACEDONIA": "MK",
    "ALBANIA": "AL",
    "BOSNIA AND HERZEGOVINA": "BA", "BOSNIA": "BA",
    "KOSOVO": "XK",
    "MOLDOVA": "MD",
    "BELARUS": "BY",
    "GEORGIA": "GE",
    "ARMENIA": "AM",
    "AZERBAIJAN": "AZ",
    "KAZAKHSTAN": "KZ",
    "UZBEKISTAN": "UZ",
    "PAKISTAN": "PK",
    "BANGLADESH": "BD",
    "SRI LANKA": "LK",
    "NEPAL": "NP",
    "CAMBODIA": "KH",
    "MYANMAR": "MM", "BURMA": "MM",
    "LAOS": "LA",
    "MONGOLIA": "MN",
    "NORTH KOREA": "KP",
    "SAUDI ARABIA": "SA",
    "QATAR": "QA",
    "KUWAIT": "KW",
    "BAHRAIN": "BH",
    "OMAN": "OM",
    "JORDAN": "JO",
    "LEBANON": "LB",
    "IRAQ": "IQ",
    "IRAN": "IR",
    "EGYPT": "EG",
    "MOROCCO": "MA",
    "ALGERIA": "DZ",
    "TUNISIA": "TN",
    "LIBYA": "LY",
    "NIGERIA": "NG",
    "KENYA": "KE",
    "GHANA": "GH",
    "ETHIOPIA": "ET",
    "TANZANIA": "TZ",
    "UGANDA": "UG",
    "VENEZUELA": "VE",
    "ECUADOR": "EC",
    "BOLIVIA": "BO",
    "PARAGUAY": "PY",
    "URUGUAY": "UY",
    "COSTA RICA": "CR",
    "PANAMA": "PA",
    "GUATEMALA": "GT",
    "CUBA": "CU",
    "DOMINICAN REPUBLIC": "DO",
    "PUERTO RICO": "PR",
    "JAMAICA": "JM",
}

def normalize_country_code(country: str) -> str:
    """Normalize country name to 2-letter code."""
    if not country:
        return ""
    country_upper = country.upper().strip()
    # Already a 2-letter code
    if len(country_upper) == 2:
        return country_upper
    # Look up in mapping
    return COUNTRY_NAME_TO_CODE.get(country_upper, country_upper)

def get_site_tld_auto(url: str) -> str:
    """Extract TLD from URL. Returns both compound TLD (co.uk) and simple TLD (uk) for matching."""
    try:
        domain = url.lower().replace('https://', '').replace('http://', '')
        domain = domain.split('/')[0].split(':')[0]
        parts = domain.split('.')
        if len(parts) >= 2:
            # Only treat as compound TLD if it's a known second-level domain pattern
            # co.uk, com.au, org.uk, etc. - but NOT gov.uk (gov is just a subdomain)
            if len(parts) >= 3 and parts[-2] in ('co', 'com', 'org', 'net', 'ac'):
                return f"{parts[-2]}.{parts[-1]}"
            return parts[-1]
        return ''
    except:
        return ''

def is_site_local_geo(url: str, country_code: str) -> bool:
    """Check if site matches the profile's country geo."""
    if not country_code:
        return False
    # Normalize country code (handle full names like "Slovenia" -> "SI")
    normalized_code = normalize_country_code(country_code)
    tld = get_site_tld_auto(url)
    local_tlds = COUNTRY_TO_TLD.get(normalized_code.upper(), [normalized_code.lower()])
    return tld in local_tlds

def is_site_generic(url: str) -> bool:
    """Check if site has a generic (non-country) TLD."""
    tld = get_site_tld_auto(url)
    return tld in GENERIC_TLDS

def split_sites_by_geo(sites: List[str], country_code: str) -> tuple:
    """Split sites into local geo and generic lists."""
    local_sites = []
    generic_sites = []
    
    for site in sites:
        if is_site_local_geo(site, country_code):
            local_sites.append(site)
        elif is_site_generic(site):
            generic_sites.append(site)
        else:
            # Non-matching country TLD goes to generic pool
            generic_sites.append(site)
    
    return local_sites, generic_sites


class HumanBehavior:
    @staticmethod
    async def random_delay(min_sec: float = 0.5, max_sec: float = 3.0):
        await asyncio.sleep(random.uniform(min_sec, max_sec))
    
    @staticmethod
    async def smooth_scroll(page: Page, direction: str = "down", 
                            iterations_min: int = 3, iterations_max: int = 6,
                            pixels_min: int = 50, pixels_max: int = 150,
                            pause_min: float = 0.1, pause_max: float = 0.3):
        try:
            for _ in range(random.randint(iterations_min, iterations_max)):
                scroll = random.randint(pixels_min, pixels_max) * (1 if direction == "down" else -1)
                await page.evaluate(f"window.scrollBy(0, {scroll})")
                await asyncio.sleep(random.uniform(pause_min, pause_max))
        except:
            pass
    
    @staticmethod
    async def random_mouse(page: Page):
        try:
            vp = await page.evaluate("() => ({w: window.innerWidth, h: window.innerHeight})")
            await page.mouse.move(
                random.randint(100, max(200, vp['w'] - 100)),
                random.randint(100, max(200, vp['h'] - 100)),
                steps=random.randint(5, 10)
            )
        except:
            pass
    
    @staticmethod
    async def simulate_reading(page: Page):
        for _ in range(random.randint(2, 4)):
            await HumanBehavior.smooth_scroll(page, "down")
            await HumanBehavior.random_delay(1, 3)


class BrowserAutomation:
    def __init__(self, log_callback: Optional[Callable] = None):
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.context = None
        self.cdp = None
        self.is_running = False
        self.should_stop = False
        self.log_callback = log_callback or (lambda x: logger.info(x))
        self._blocked_count = 0
        
        # Google Auth Manager (new architecture)
        self._google_auth_manager: Optional[GoogleAuthManager] = None
    
    def log(self, msg: str):
        logger.info(msg)
        self.log_callback(msg)
    
    async def _block_media_handler(self, route: Route):
        """Block audio/video requests"""
        url = route.request.url.lower()
        
        # Check media patterns
        for pattern in BLOCKED_MEDIA_PATTERNS:
            if re.search(pattern, url):
                self._blocked_count += 1
                await route.abort()
                return
        
        # Check ad domains
        for domain in BLOCKED_AD_DOMAINS:
            if domain in url:
                self._blocked_count += 1
                await route.abort()
                return
        
        # Allow other requests
        await route.continue_()
    
    async def connect_to_octo(self, debug_port: int = None, ws_endpoint: str = None) -> bool:
        try:
            self.playwright = await async_playwright().start()
            
            if ws_endpoint:
                self.browser = await self.playwright.chromium.connect_over_cdp(ws_endpoint)
            elif debug_port:
                self.browser = await self.playwright.chromium.connect_over_cdp(f"http://localhost:{debug_port}")
            else:
                return False
            
            contexts = self.browser.contexts
            if contexts:
                self.context = contexts[0]
                pages = self.context.pages
                self.page = pages[0] if pages else await self.context.new_page()
            else:
                self.context = await self.browser.new_context()
                self.page = await self.context.new_page()
            
            # === SETUP NETWORK BLOCKING ===
            # Block media files at network level
            await self.context.route("**/*", self._block_media_handler)
            self.log("Media blocking enabled")
            
            # === CDP FOR PERMISSIONS ===
            try:
                self.cdp = await self.context.new_cdp_session(self.page)
                await self.cdp.send("Browser.setPermission", {
                    "permission": {"name": "notifications"},
                    "setting": "denied"
                })
                self.log("Notifications blocked")
            except:
                pass
            
            # Dialog handler
            self.page.on("dialog", lambda d: asyncio.create_task(d.dismiss()))
            
            # Mute existing media
            await self.mute_page()
            
            self.log("Connected to Octo Browser")
            return True
            
        except Exception as e:
            self.log(f"Connection failed: {e}")
            return False
    
    async def mute_page(self):
        """Mute all media on page via JS"""
        if not self.page:
            return
        try:
            await self.page.evaluate("""
                () => {
                    // Mute existing
                    document.querySelectorAll('video, audio').forEach(el => {
                        el.muted = true;
                        el.volume = 0;
                        el.pause();
                    });
                    
                    // Override for future elements
                    Object.defineProperty(HTMLMediaElement.prototype, 'volume', {
                        set: function() {},
                        get: function() { return 0; }
                    });
                    
                    // MutationObserver for dynamic content
                    new MutationObserver(() => {
                        document.querySelectorAll('video, audio').forEach(el => {
                            el.muted = true;
                            el.pause();
                        });
                    }).observe(document.body, {childList: true, subtree: true});
                }
            """)
        except:
            pass
    
    async def minimize_window(self):
        """Minimize browser window using CDP."""
        try:
            if self.page and not self.page.is_closed():
                cdp = await self.page.context.new_cdp_session(self.page)
                window_id = await cdp.send("Browser.getWindowForTarget")
                if window_id and window_id.get("windowId"):
                    await cdp.send("Browser.setWindowBounds", {
                        "windowId": window_id.get("windowId"),
                        "bounds": {"windowState": "minimized"}
                    })
                    return True
        except:
            pass
        return False
    
    async def disconnect(self):
        try:
            # Close all extra tabs before disconnecting (keep only one to preserve session)
            await self._close_all_extra_tabs()
            
            if self.cdp:
                await self.cdp.detach()
            if self.browser:
                await self.browser.close()
            if hasattr(self, 'playwright'):
                await self.playwright.stop()
        except:
            pass
        
        if self._blocked_count > 0:
            self.log(f"Blocked {self._blocked_count} media requests")
    
    async def _close_all_extra_tabs(self):
        """Close all tabs except one to clean up before session end."""
        try:
            if not self.context:
                return
            
            pages = self.context.pages
            if len(pages) <= 1:
                return
            
            self.log(f"🧹 Closing {len(pages) - 1} extra tab(s)...")
            
            # Keep the first page, close all others
            for page in pages[1:]:
                try:
                    await page.close()
                    await asyncio.sleep(0.2)
                except:
                    pass
            
            # Navigate the remaining page to a clean state (about:blank or google.com)
            if self.page and not self.page.is_closed():
                try:
                    await self.page.goto("about:blank", timeout=5000)
                except:
                    pass
            
            self.log("✅ Tabs cleaned up")
        except Exception as e:
            self.log(f"⚠️ Tab cleanup warning: {e}")
    
    async def close_popups(self):
        if not self.page:
            return
        
        for sel in CLOSE_SELECTORS:
            try:
                btn = await self.page.query_selector(sel)
                if btn and await btn.is_visible():
                    await btn.click()
                    await asyncio.sleep(0.3)
            except:
                continue
        
        for text in CLOSE_TEXTS:
            try:
                elem = await self.page.query_selector(f'button:has-text("{text}")')
                if elem and await elem.is_visible():
                    box = await elem.bounding_box()
                    if box and box['width'] < 80:
                        await elem.click()
                        await asyncio.sleep(0.3)
            except:
                continue
        
        try:
            await self.page.keyboard.press("Escape")
        except:
            pass
    
    async def accept_cookies(self) -> bool:
        if not self.page:
            return False
        
        for sel in COOKIE_SELECTORS:
            try:
                btn = await self.page.query_selector(sel)
                if btn and await btn.is_visible():
                    await btn.click()
                    self.log(f"Cookies: OK")
                    return True
            except:
                continue
        
        for text in COOKIE_BUTTON_TEXTS:
            try:
                btn = await self.page.query_selector(f'button:has-text("{text}")')
                if btn and await btn.is_visible():
                    await btn.click()
                    self.log(f"Cookies: {text}")
                    return True
            except:
                continue
        
        return False
    
    async def handle_popups(self):
        await self.accept_cookies()
        await asyncio.sleep(0.3)
        await self.close_popups()
        await self._dismiss_google_promo_dialogs()
        await self.mute_page()
    
    async def _dismiss_google_promo_dialogs(self):
        """
        Close Google promo dialogs like 'Got it', 'OK', 'Dismiss' etc.
        These appear on Google services (Calendar, Drive, etc.) for new features.
        Uses random delay 2-4 seconds with 100ms step before clicking.
        """
        if not self.page:
            return
        
        try:
            # Google promo dialog button selectors
            # Based on classes like UywwFc-vQzf8d and common button texts
            promo_selectors = [
                # By class patterns found in Google services
                'button[jsname="V67aGc"]',  # Got it button jsname
                'span.UywwFc-vQzf8d',  # "Got it" text span
                'button:has(span.UywwFc-vQzf8d)',  # Button containing Got it
                # By role and text
                'button[data-mdc-dialog-action="ok"]',
                'button[data-mdc-dialog-action="accept"]',
                # Material design buttons
                '.mdc-button--raised',
                '.mdc-dialog__button--default',
            ]
            
            # Text patterns for promo buttons
            promo_texts = [
                'Got it', 'OK', 'Okay', 'Dismiss', 'Close', 'Not now', 
                'Skip', 'Maybe later', 'No thanks', 'Continue',
                'Понятно', 'ОК', 'Закрыть', 'Пропустить', 'Не сейчас'
            ]
            
            # First try selectors
            for selector in promo_selectors:
                try:
                    btn = await self.page.query_selector(selector)
                    if btn and await btn.is_visible():
                        # Random delay 2-4 seconds with 0.1s step
                        delay = random.randint(20, 40) / 10  # 2.0 to 4.0
                        await asyncio.sleep(delay)
                        await btn.click()
                        logger.debug(f"Clicked promo button by selector: {selector}")
                        await asyncio.sleep(random.uniform(0.5, 1.0))
                        return
                except:
                    continue
            
            # Then try finding by text
            buttons = await self.page.query_selector_all('button, [role="button"]')
            for btn in buttons:
                try:
                    if not await btn.is_visible():
                        continue
                    
                    text = await btn.inner_text()
                    text_clean = text.strip()
                    
                    for promo_text in promo_texts:
                        if promo_text.lower() == text_clean.lower():
                            # Random delay 2-4 seconds with 0.1s step
                            delay = random.randint(20, 40) / 10
                            await asyncio.sleep(delay)
                            await btn.click()
                            logger.debug(f"Clicked promo button with text: {text_clean}")
                            await asyncio.sleep(random.uniform(0.5, 1.0))
                            return
                except:
                    continue
                    
        except Exception as e:
            logger.debug(f"Dismiss promo error: {e}")
    
    async def visit_site(self, url: str, min_time: int = 30, max_time: int = 120,
                         scroll_enabled: bool = True, click_links: bool = True,
                         human_behavior: bool = True):
        if not self.page:
            return
        
        try:
            self._blocked_count = 0
            self.log(f"Opening {url}")
            await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            await self.mute_page()
            await HumanBehavior.random_delay(1, 2)
            await self.handle_popups()
            
            time_on_site = random.randint(min_time, max_time)
            self.log(f"Time: {time_on_site}s")
            
            start = time.time()
            links_clicked = 0
            last_check = time.time()
            
            while (time.time() - start) < time_on_site:
                if self.should_stop:
                    return
                
                if time.time() - last_check > 5:
                    await self.mute_page()
                    await self.handle_popups()
                    last_check = time.time()
                
                if human_behavior:
                    await HumanBehavior.random_mouse(self.page)
                
                if scroll_enabled:
                    await HumanBehavior.smooth_scroll(self.page, random.choice(["down", "down", "up"]))
                
                if human_behavior:
                    await HumanBehavior.simulate_reading(self.page)
                
                if click_links and random.random() < 0.2 and links_clicked < 2:
                    await self._click_link()
                    links_clicked += 1
                    await self.mute_page()
                    await self.handle_popups()
                
                await HumanBehavior.random_delay(2, 5)
            
            blocked_msg = f" (blocked {self._blocked_count} media)" if self._blocked_count > 0 else ""
            self.log(f"Done: {url} ({int(time.time() - start)}s){blocked_msg}")
            
        except Exception as e:
            self.log(f"Error: {e}")
    
    async def _click_link(self):
        try:
            links = await self.page.query_selector_all("a[href]")
            valid = []
            for link in links[:20]:
                try:
                    href = await link.get_attribute("href")
                    if href and await link.is_visible() and not href.startswith(("#", "javascript:", "mailto:")):
                        valid.append(link)
                except:
                    continue
            
            if valid:
                link = random.choice(valid[:8])
                await link.click()
                await self.page.wait_for_load_state("domcontentloaded", timeout=15000)
                await self.mute_page()
        except:
            pass
    
    async def run_session(self, sites: List[str], settings: dict = None):
        """Cookie mode session with configurable navigation and site limits."""
        self.is_running = True
        self.should_stop = False
        
        # Parse settings (support both old and new style)
        if settings is None:
            settings = {}
        
        min_time = settings.get("min_time_on_site", 30)
        max_time = settings.get("max_time_on_site", 120)
        scroll_enabled = settings.get("scroll_enabled", True)
        scroll_percent = settings.get("scroll_percent", 70)
        scroll_iter_min = settings.get("scroll_iterations_min", 3)
        scroll_iter_max = settings.get("scroll_iterations_max", 6)
        scroll_px_min = settings.get("scroll_pixels_min", 50)
        scroll_px_max = settings.get("scroll_pixels_max", 150)
        scroll_pause_min = settings.get("scroll_pause_min", 0.1)
        scroll_pause_max = settings.get("scroll_pause_max", 0.3)
        scroll_down_percent = settings.get("scroll_down_percent", 66)
        click_links = settings.get("click_links_enabled", True)
        click_percent = settings.get("click_percent", 20)
        max_clicks = settings.get("max_clicks_per_site", 2)
        human_behavior = settings.get("human_behavior_enabled", True)
        google_search_percent = settings.get("google_search_percent", 70)
        sites_per_session_min = settings.get("sites_per_session_min", 1)
        sites_per_session_max = settings.get("sites_per_session_max", 100)
        
        # Base delay settings (from global config)
        base_delay_min = settings.get("base_delay_min", 1)
        base_delay_max = settings.get("base_delay_max", 3)
        
        # Geo-based visiting settings
        geo_enabled = settings.get("geo_visiting_enabled", False)
        geo_percent = settings.get("geo_visiting_percent", 70)
        profile_country = settings.get("profile_country", "")
        
        # Normalize country code for geo matching
        if profile_country:
            profile_country = normalize_country_code(profile_country)
        
        # Apply geo-based site selection if enabled
        if geo_enabled and profile_country:
            local_sites, generic_sites = split_sites_by_geo(sites, profile_country)
            
            if local_sites:
                # Calculate how many sites of each type
                total_to_visit = random.randint(sites_per_session_min, min(sites_per_session_max, len(sites)))
                local_count = max(1, round(total_to_visit * geo_percent / 100))
                generic_count = total_to_visit - local_count
                
                # Ensure we don't exceed available sites
                local_count = min(local_count, len(local_sites))
                generic_count = min(generic_count, len(generic_sites))
                
                # If not enough generic sites, use more local
                if generic_count < (total_to_visit - local_count) and len(local_sites) > local_count:
                    local_count = min(total_to_visit - generic_count, len(local_sites))
                
                # Shuffle and select
                random.shuffle(local_sites)
                random.shuffle(generic_sites)
                
                selected_local = local_sites[:local_count]
                selected_generic = generic_sites[:generic_count]
                
                # Combine and shuffle for natural order
                sites = selected_local + selected_generic
                random.shuffle(sites)
                
                self.log(f"🌍 Geo mode ({profile_country}): {len(selected_local)} local + {len(selected_generic)} generic = {len(sites)} sites")
            else:
                # No local sites - fallback to generic only
                self.log(f"⚠️ No sites for geo {profile_country}, using generic sites")
                random.shuffle(generic_sites)
                sites_to_visit = random.randint(sites_per_session_min, min(sites_per_session_max, len(generic_sites)))
                sites = generic_sites[:sites_to_visit]
        else:
            # No geo filtering - standard behavior
            random.shuffle(sites)
            sites_to_visit = random.randint(sites_per_session_min, min(sites_per_session_max, len(sites)))
            sites = sites[:sites_to_visit]
            self.log(f"Session: {len(sites)} sites (limit: {sites_per_session_min}-{sites_per_session_max})")
        
        # Track geo stats for logging
        local_visited = 0
        generic_visited = 0
        
        for i, site in enumerate(sites, 1):
            if self.should_stop:
                break
            
            # Track geo stats
            if geo_enabled and profile_country:
                if is_site_local_geo(site, profile_country):
                    local_visited += 1
                else:
                    generic_visited += 1
            
            self.log(f"[{i}/{len(sites)}] {site}")
            
            # Decide navigation method based on google_search_percent
            use_google_search = random.randint(1, 100) <= google_search_percent
            
            if use_google_search:
                self.log(f"   🔍 Navigating via Google Search...")
                nav_success = await self._navigate_via_google_search(site)
                if not nav_success:
                    self.log(f"   ⚠️ Google Search failed, trying direct...")
                    await self._navigate_direct_in_new_tab(site)
            else:
                await self._navigate_direct_in_new_tab(site)
            
            # Browse the site
            await self._browse_site(
                site, min_time, max_time, scroll_enabled, click_links, human_behavior,
                scroll_percent, click_percent, max_clicks,
                scroll_iter_min, scroll_iter_max, scroll_px_min, scroll_px_max,
                scroll_pause_min, scroll_pause_max, scroll_down_percent
            )
            
            if i < len(sites):
                # Use base delay from global settings + some variability
                await asyncio.sleep(random.randint(base_delay_min + 1, base_delay_max + 3))
        
        self.is_running = False
        
        # Log geo summary
        if geo_enabled and profile_country:
            self.log(f"✅ Session completed: {local_visited} {profile_country} sites, {generic_visited} generic sites")
        else:
            self.log("✅ Session completed")
    
    async def _browse_site(self, site: str, min_time: int, max_time: int, 
                           scroll_enabled: bool, click_links: bool, human_behavior: bool,
                           scroll_percent: int = 70, click_percent: int = 20, max_clicks: int = 2,
                           scroll_iter_min: int = 3, scroll_iter_max: int = 6,
                           scroll_px_min: int = 50, scroll_px_max: int = 150,
                           scroll_pause_min: float = 0.1, scroll_pause_max: float = 0.3,
                           scroll_down_percent: int = 66):
        """Browse a site with configured behavior."""
        try:
            await self.handle_popups()
            await self.mute_page()
            
            time_on_site = random.randint(min_time, max_time)
            self.log(f"   Browsing for {time_on_site}s...")
            
            start = time.time()
            links_clicked = 0
            
            while (time.time() - start) < time_on_site:
                if self.should_stop:
                    return
                
                if human_behavior:
                    await HumanBehavior.random_mouse(self.page)
                
                # Scroll with configurable probability and parameters
                if scroll_enabled and random.randint(1, 100) <= scroll_percent:
                    direction = "down" if random.randint(1, 100) <= scroll_down_percent else "up"
                    await HumanBehavior.smooth_scroll(
                        self.page, direction,
                        scroll_iter_min, scroll_iter_max,
                        scroll_px_min, scroll_px_max,
                        scroll_pause_min, scroll_pause_max
                    )
                
                await HumanBehavior.random_delay(2, 5)
                
                # Click with configurable probability and max limit
                if click_links and random.randint(1, 100) <= click_percent and links_clicked < max_clicks:
                    await self._click_link()
                    links_clicked += 1
                    await self.handle_popups()
                
                if random.random() < 0.1:
                    await self.handle_popups()
                    await self.mute_page()
        except Exception as e:
            self.log(f"   ⚠️ Browse error: {e}")
    
    # =========================================================================
    # GOOGLE AUTH MANAGER - Uses new modular architecture
    # =========================================================================
    
    async def _init_google_auth_manager(self):
        """Initialize the Google Auth Manager"""
        if self._google_auth_manager is None and self.page and self.context:
            self._google_auth_manager = GoogleAuthManager(
                self.page, 
                self.context, 
                self.log
            )
    
    async def _start_google_watcher(self):
        """Start background task that watches for Google auth popups."""
        await self._init_google_auth_manager()
        if self._google_auth_manager:
            await self._google_auth_manager.start_watcher()
    
    async def _stop_google_watcher(self):
        """Stop the background watcher."""
        if self._google_auth_manager:
            await self._google_auth_manager.stop_watcher()
    
    async def run_google_warmup(self, sites: List[str], settings: dict):
        """
        Google Warm-up mode with mixed activities:
        - Visit sites, authenticate via Google, browse
        - Periodically check Gmail between site visits
        - YouTube activity (if youtube.com in sites list)
        """
        self.is_running = True
        self.should_stop = False
        self.log("🚀 Google Warm-up mode")
        
        read_gmail = settings.get("read_gmail", True)
        auth_on_sites = settings.get("auth_on_sites", True)
        gmail_read_percent = settings.get("gmail_read_percent", 40)
        # Gmail read time: support min/max range or single value for backward compatibility
        gmail_read_time_min = settings.get("gmail_read_time_min", settings.get("gmail_read_time", 15))
        gmail_read_time_max = settings.get("gmail_read_time_max", settings.get("gmail_read_time", 45))
        min_time = settings.get("min_time_on_site", 60)
        max_time = settings.get("max_time_on_site", 180)
        
        # Browsing behavior settings
        scroll_enabled = settings.get("scroll_enabled", True)
        scroll_percent = settings.get("scroll_percent", 70)
        click_links_enabled = settings.get("click_links_enabled", True)
        click_percent = settings.get("click_percent", 20)
        max_clicks_per_site = settings.get("max_clicks_per_site", 2)
        
        # Store for use in browse methods
        self._scroll_enabled = scroll_enabled
        self._scroll_percent = scroll_percent
        self._click_links_enabled = click_links_enabled
        self._click_percent = click_percent
        self._max_clicks_per_site = max_clicks_per_site
        
        # Scroll parameters
        self._scroll_iter_min = settings.get("scroll_iterations_min", 3)
        self._scroll_iter_max = settings.get("scroll_iterations_max", 6)
        self._scroll_px_min = settings.get("scroll_pixels_min", 50)
        self._scroll_px_max = settings.get("scroll_pixels_max", 150)
        self._scroll_pause_min = settings.get("scroll_pause_min", 0.1)
        self._scroll_pause_max = settings.get("scroll_pause_max", 0.3)
        self._scroll_down_percent = settings.get("scroll_down_percent", 66)
        
        # NEW: Gmail settings
        self._gmail_promo_spam_percent = settings.get("gmail_promo_spam_percent", 10)
        self._gmail_click_links = settings.get("gmail_click_links", True)
        
        # NEW: Base action delay (random range from global settings)
        self._base_delay_min = settings.get("base_delay_min", 1)
        self._base_delay_max = settings.get("base_delay_max", 3)
        
        # NEW: Google Search percentage (0-100)
        self._google_search_percent = settings.get("google_search_percent", 70)
        
        # NEW: Sites per session limit (min-max)
        sites_per_session_min = settings.get("sites_per_session_min", 1)
        sites_per_session_max = settings.get("sites_per_session_max", 100)
        
        # NEW: YouTube activity percentage (0-100)
        youtube_activity_percent = settings.get("youtube_activity_percent", 100)
        
        # NEW: YouTube enabled checkbox (include YouTube in session)
        youtube_enabled_setting = settings.get("youtube_enabled", True)
        
        # NEW: YouTube settings (store in instance for perform_youtube_activity)
        self._youtube_videos_min = settings.get("youtube_videos_min", 1)
        self._youtube_videos_max = settings.get("youtube_videos_max", 3)
        self._youtube_watch_min = settings.get("youtube_watch_min", 15)
        self._youtube_watch_max = settings.get("youtube_watch_max", 60)
        self._youtube_like_percent = settings.get("youtube_like_percent", 25)
        self._youtube_watchlater_percent = settings.get("youtube_watchlater_percent", 20)
        
        # NEW: YouTube search queries from settings (comma-separated string)
        youtube_queries_str = settings.get("youtube_queries", "")
        if youtube_queries_str:
            self._youtube_queries = [q.strip() for q in youtube_queries_str.split(",") if q.strip()]
        else:
            self._youtube_queries = YOUTUBE_SEARCH_WORDS  # Fallback to default
        
        # NEW: Get separate site lists from settings (for different handling)
        browse_sites = settings.get("browse_sites", [])  # No auth needed
        onetap_sites = settings.get("onetap_sites", [])  # Auth via One Tap
        google_services = settings.get("services", {})   # Google services checkboxes
        
        # Build Google services URLs from enabled checkboxes
        service_url_map = {
            "drive": "https://drive.google.com/",
            "sheets": "https://docs.google.com/spreadsheets/",
            "docs": "https://docs.google.com/document/",
            "calendar": "https://calendar.google.com/",
            "photos": "https://photos.google.com/",
            "maps": "https://maps.google.com/",
        }
        enabled_services = []
        for service_name, is_enabled in google_services.items():
            if is_enabled and service_name in service_url_map:
                enabled_services.append(service_url_map[service_name])
        
        # Build site queue with type info: (url, needs_auth)
        self._site_auth_map = {}
        for s in browse_sites:
            self._site_auth_map[s.lower().rstrip('/')] = False  # No auth
        for s in onetap_sites:
            self._site_auth_map[s.lower().rstrip('/')] = True   # Need auth
        # Google services - no auth needed (already logged in via Google)
        for s in enabled_services:
            self._site_auth_map[s.lower().rstrip('/')] = False
        
        # Combine all sites: user sites + enabled Google services
        all_sites = sites.copy()  # Start with passed sites (already includes browse + onetap)
        all_sites.extend(enabled_services)  # Add enabled Google services
        
        # === YOUTUBE ACTIVITY SETUP ===
        # YouTube can be enabled via:
        # 1. Checkbox "Include YouTube in session" (youtube_enabled_setting)
        # 2. Manually adding youtube.com to site list
        # Remove youtube.com from regular site processing (will be handled separately)
        self._youtube_activity_done = False
        youtube_enabled = False
        sites_filtered = []
        youtube_in_sites = False
        
        for site in all_sites:
            site_lower = site.lower()
            if 'youtube.com' in site_lower or 'youtu.be' in site_lower:
                youtube_in_sites = True
                # Don't add to filtered sites - YouTube handled separately
            else:
                sites_filtered.append(site)
        
        # Enable YouTube if checkbox is ON or youtube.com was in the site list
        if youtube_enabled_setting or youtube_in_sites:
            # Check if YouTube activity should be enabled based on percentage
            if random.randint(1, 100) <= youtube_activity_percent:
                youtube_enabled = True
                source = "checkbox" if youtube_enabled_setting else "site list"
                self.log(f"📺 YouTube activity enabled via {source} ({youtube_activity_percent}% chance)")
            else:
                self.log(f"📺 YouTube skipped this session ({youtube_activity_percent}% chance)")
        
        # Determine when to run YouTube activity
        # If YouTube is the ONLY site - run before Gmail
        # Otherwise - run after N sites (similar to Gmail check pattern)
        youtube_only = youtube_enabled and len(sites_filtered) == 0
        sites_until_youtube = random.randint(3, 5) if not youtube_only else 0
        
        if not sites_filtered and not youtube_enabled:
            # No sites - just do Gmail
            if read_gmail:
                await self.perform_gmail_activity(gmail_read_percent, gmail_read_time_min, gmail_read_time_max)
            self.is_running = False
            return
        
        # Handle YouTube-only case
        if youtube_only:
            self.log("📺 YouTube-only mode: will run YouTube activity before Gmail")
            
            # Run YouTube activity
            if not self.should_stop:
                await self.perform_youtube_activity()
            
            # Then do Gmail
            if read_gmail and not self.should_stop:
                await self.perform_gmail_activity(gmail_read_percent, gmail_read_time_min, gmail_read_time_max)
            
            self.is_running = False
            self.log("\n✅ Google Warm-up complete!")
            return
        
        # Shuffle sites for randomness
        sites_queue = sites_filtered.copy()
        
        # === GEO-BASED SITE SELECTION ===
        geo_enabled = settings.get("geo_visiting_enabled", False)
        geo_percent = settings.get("geo_visiting_percent", 70)
        profile_country = settings.get("profile_country", "")
        
        # Normalize country code
        if profile_country:
            profile_country = normalize_country_code(profile_country)
        
        # Apply geo-based site selection if enabled
        if geo_enabled and profile_country and sites_queue:
            local_sites, generic_sites = split_sites_by_geo(sites_queue, profile_country)
            
            if local_sites:
                # Calculate counts based on geo_percent
                total_to_visit = min(
                    random.randint(sites_per_session_min, sites_per_session_max),
                    len(sites_queue)
                )
                local_count = max(1, round(total_to_visit * geo_percent / 100))
                generic_count = total_to_visit - local_count
                
                # Ensure we don't exceed available sites
                local_count = min(local_count, len(local_sites))
                generic_count = min(generic_count, len(generic_sites))
                
                # If not enough generic, use more local
                if generic_count < (total_to_visit - local_count) and len(local_sites) > local_count:
                    local_count = min(total_to_visit - generic_count, len(local_sites))
                
                # Shuffle and select
                random.shuffle(local_sites)
                random.shuffle(generic_sites)
                
                sites_queue = local_sites[:local_count] + generic_sites[:generic_count]
                random.shuffle(sites_queue)
                
                self.log(f"🌍 Geo mode ({profile_country}): {local_count} local + {generic_count} generic = {len(sites_queue)} sites")
            else:
                # No local sites - fallback to generic
                self.log(f"⚠️ No sites for geo {profile_country}, using generic sites")
                random.shuffle(generic_sites)
                sites_queue = generic_sites
        else:
            random.shuffle(sites_queue)
        
        # NEW: Limit sites per session
        if sites_per_session_max < len(sites_queue):
            sites_to_visit = random.randint(sites_per_session_min, sites_per_session_max)
            sites_to_visit = min(sites_to_visit, len(sites_queue))
            sites_queue = sites_queue[:sites_to_visit]
            self.log(f"📊 Sites limited to {sites_to_visit} for this session")
        
        total_sites_count = len(sites_queue)
        
        # Track Gmail visits to distribute reading across session
        gmail_visits_done = 0
        max_gmail_visits = 3  # Check Gmail up to 3 times during session
        # Use settings for sites between Gmail checks (default 4-6)
        gmail_check_sites_min = settings.get("gmail_check_sites_min", 4)
        gmail_check_sites_max = settings.get("gmail_check_sites_max", 6)
        sites_until_gmail = random.randint(gmail_check_sites_min, gmail_check_sites_max)
        sites_processed = 0
        
        # Final Gmail check settings
        gmail_final_check = settings.get("gmail_final_check", True)
        gmail_final_check_percent = settings.get("gmail_final_check_percent", 80)
        
        plan_parts = [f"{len(sites_queue)} sites"]
        if youtube_enabled:
            plan_parts.append("YouTube activity")
        plan_parts.append("Gmail checks")
        self.log(f"📋 Plan: {' + '.join(plan_parts)}")
        
        # Set minimize flag for methods that open new tabs
        self._should_minimize = settings.get("start_minimized", True)
        
        # Try to minimize window at start of session
        if self._should_minimize:
            await self.minimize_window()
        
        # Track geo stats for final log
        local_visited = 0
        generic_visited = 0
        
        while sites_queue and not self.should_stop:
            # === PROCESS SITE ===
            site = sites_queue.pop(0)
            sites_processed += 1
            
            # Track geo stats
            if geo_enabled and profile_country:
                if is_site_local_geo(site, profile_country):
                    local_visited += 1
                else:
                    generic_visited += 1
            
            self.log(f"\n[{sites_processed}/{total_sites_count}] {site}")
            
            # Check if this site needs authentication
            site_needs_auth = self._site_auth_map.get(site.lower().rstrip('/'), True)
            
            # Step 1: Authenticate on site (if enabled AND site needs auth)
            if auth_on_sites and site_needs_auth:
                # NOTE: Watcher disabled - using new CDP-based auth instead
                # await self._start_google_watcher()
                
                auth_result = await self._auth_on_single_site(site)
                
                # await self._stop_google_watcher()
                
                # Only skip if actual error occurred
                if auth_result == 'failed':
                    self.log("   Skipping due to page error")
                    await HumanBehavior.random_delay(2, 4)
                    continue
                
                # 'no_onetap', 'success', 'already_logged' - all continue to browse
            else:
                # Just navigate without auth attempt
                self.log("   🌐 Browsing only (no auth)")
                
                # Check if Google service - should go via search
                is_google_service = any(domain in site.lower() for domain in [
                    'drive.google.com', 'docs.google.com', 'calendar.google.com',
                    'photos.google.com', 'maps.google.com', 'sheets.google.com',
                    'slides.google.com', 'meet.google.com', 'chat.google.com'
                ])
                
                if is_google_service:
                    self.log("   🔍 Google service → searching via Google")
                    nav_success = await self._navigate_via_google_search(site)
                    if not nav_success:
                        nav_success = await self._navigate_direct_in_new_tab(site)
                else:
                    nav_success = await self._navigate_direct_in_new_tab(site)
                
                if not nav_success:
                    self.log("   Skipping due to navigation error")
                    await HumanBehavior.random_delay(2, 4)
                    continue
                
                # For Google services - dismiss promo dialogs
                if is_google_service:
                    await self._dismiss_google_promo_dialogs()
            
            # Step 2: Browse the site
            await HumanBehavior.random_delay(1, 2)
            await self._browse_site_after_auth(
                site, min_time, max_time,
                self._scroll_enabled, self._scroll_percent,
                self._click_links_enabled, self._click_percent, self._max_clicks_per_site,
                self._scroll_iter_min, self._scroll_iter_max,
                self._scroll_px_min, self._scroll_px_max,
                self._scroll_pause_min, self._scroll_pause_max,
                self._scroll_down_percent
            )
            
            # Step 3: Close site tab and return to search tab (if using Google search)
            await self._close_site_tab_and_return_to_search()
            
            # === CHECK IF TIME FOR YOUTUBE ===
            if youtube_enabled and not self._youtube_activity_done:
                sites_until_youtube -= 1
                
                if sites_until_youtube <= 0 and not self.should_stop:
                    self.log("\n📺 Time for YouTube activity...")
                    await self.perform_youtube_activity()
                    # Close YouTube tab after activity
                    await self._close_site_tab_and_return_to_search()
            
            # === CHECK IF TIME FOR GMAIL ===
            sites_until_gmail -= 1
            
            if (read_gmail and 
                sites_until_gmail <= 0 and 
                gmail_visits_done < max_gmail_visits and
                not self.should_stop):
                
                # Do a quick Gmail check
                gmail_visits_done += 1
                emails_to_read_now = max(1, gmail_read_percent // max_gmail_visits)
                
                self.log(f"\n📧 Gmail check #{gmail_visits_done}...")
                await self._quick_gmail_check(
                    read_percent=emails_to_read_now,
                    read_time_min=gmail_read_time_min,
                    read_time_max=gmail_read_time_max
                )
                
                # Reset counter for next Gmail visit
                sites_until_gmail = random.randint(gmail_check_sites_min, gmail_check_sites_max)
            
            # Delay between sites (use base delay from settings)
            if sites_queue:
                delay_min = getattr(self, '_base_delay_min', 1)
                delay_max = getattr(self, '_base_delay_max', 3)
                # Add some variability: base + random extra
                await HumanBehavior.random_delay(delay_min + 1, delay_max + 3)
        
        # Run YouTube if not done yet (ran out of sites before trigger)
        if youtube_enabled and not self._youtube_activity_done and not self.should_stop:
            self.log("\n📺 Final YouTube activity (before Gmail)...")
            await self.perform_youtube_activity()
            await self._close_site_tab_and_return_to_search()
        
        # Final Gmail check (based on settings)
        should_do_final_check = (
            read_gmail and 
            gmail_final_check and 
            not self.should_stop and
            random.randint(1, 100) <= gmail_final_check_percent
        )
        
        if should_do_final_check:
            self.log(f"\n📧 Final Gmail check ({gmail_final_check_percent}% chance)...")
            await self.perform_gmail_activity(gmail_read_percent, gmail_read_time_min, gmail_read_time_max)
        elif read_gmail and gmail_visits_done == 0 and not self.should_stop:
            # Fallback: if no Gmail checks happened during session, do one anyway
            self.log(f"\n📧 Gmail check (no checks during session)...")
            await self.perform_gmail_activity(gmail_read_percent, gmail_read_time_min, gmail_read_time_max)
        
        self.is_running = False
        
        # Final log with geo stats if enabled
        if geo_enabled and profile_country:
            self.log(f"\n✅ Google Warm-up complete! ({local_visited} {profile_country} sites, {generic_visited} generic)")
        else:
            self.log("\n✅ Google Warm-up complete!")
    
    async def _browse_site_after_auth(self, url: str, min_time: int, max_time: int,
                                       scroll_enabled: bool = True, scroll_percent: int = 70,
                                       click_links: bool = True, click_percent: int = 20, max_clicks: int = 2,
                                       scroll_iter_min: int = 3, scroll_iter_max: int = 6,
                                       scroll_px_min: int = 50, scroll_px_max: int = 150,
                                       scroll_pause_min: float = 0.1, scroll_pause_max: float = 0.3,
                                       scroll_down_percent: int = 66):
        """Browse a site after authentication - scroll, click, behave humanly."""
        try:
            # Make sure we're on the site
            if 'accounts.google.com' in self.page.url:
                await self.page.goto(url, wait_until="domcontentloaded", timeout=20000)
            
            await self.handle_popups()
            await self.mute_page()
            
            time_on_site = random.randint(min_time, max_time)
            self.log(f"   Browsing for {time_on_site}s...")
            
            start = time.time()
            links_clicked = 0
            
            while (time.time() - start) < time_on_site:
                if self.should_stop:
                    return
                
                # Human behavior - mouse movement
                await HumanBehavior.random_mouse(self.page)
                
                # Scroll with configurable probability and parameters
                if scroll_enabled and random.randint(1, 100) <= scroll_percent:
                    direction = "down" if random.randint(1, 100) <= scroll_down_percent else "up"
                    await HumanBehavior.smooth_scroll(
                        self.page, direction,
                        scroll_iter_min, scroll_iter_max,
                        scroll_px_min, scroll_px_max,
                        scroll_pause_min, scroll_pause_max
                    )
                
                await HumanBehavior.random_delay(2, 5)
                
                # Click with configurable probability and max limit
                if click_links and random.randint(1, 100) <= click_percent and links_clicked < max_clicks:
                    await self._click_link()
                    links_clicked += 1
                    await self.handle_popups()
                
                # Periodic popup/mute check
                if random.random() < 0.1:
                    await self.handle_popups()
                    await self.mute_page()
            
            self.log(f"   ✓ Browsed {int(time.time() - start)}s")
            
        except Exception as e:
            self.log(f"   Browse error: {e}")
    
    # ========================================================================
    # YOUTUBE ACTIVITY MODULE
    # ========================================================================
    
    async def perform_youtube_activity(self) -> bool:
        """
        Perform YouTube activity: search, watch videos, like, save to playlist.
        
        Flow:
        1. Navigate to YouTube (via Google search or direct)
        2. Search for random keyword
        3. Watch 1-3 random videos (15-60 sec each)
        4. 20-30% chance to like
        5. Configurable chance to save to "Watch later"
        
        Returns:
            True if activity completed, False otherwise
        """
        try:
            self.log("📺 Starting YouTube activity...")
            
            # Mark that we're doing YouTube activity
            self._youtube_activity_done = True
            
            # Get YouTube settings (use defaults if not set)
            yt_videos_min = getattr(self, '_youtube_videos_min', 1)
            yt_videos_max = getattr(self, '_youtube_videos_max', 3)
            yt_watch_min = getattr(self, '_youtube_watch_min', 15)
            yt_watch_max = getattr(self, '_youtube_watch_max', 60)
            yt_like_percent = getattr(self, '_youtube_like_percent', 25)
            yt_watchlater_percent = getattr(self, '_youtube_watchlater_percent', 20)
            
            # Step 1: Navigate to YouTube via Google search
            youtube_navigated = await self._navigate_to_youtube()
            if not youtube_navigated:
                self.log("   ⚠️ Could not navigate to YouTube")
                return False
            
            await asyncio.sleep(random.uniform(2, 3))
            
            # Step 2: Search for random keyword from custom queries
            search_word = random.choice(self._youtube_queries)
            search_success = await self._youtube_search(search_word)
            if not search_success:
                self.log("   ⚠️ YouTube search failed")
                return False
            
            await asyncio.sleep(random.uniform(2, 3))
            
            # Step 3: Watch N videos (from settings)
            videos_to_watch = random.randint(yt_videos_min, yt_videos_max)
            self.log(f"   📹 Will watch {videos_to_watch} video(s)")
            
            for i in range(videos_to_watch):
                if self.should_stop:
                    break
                
                self.log(f"   [{i+1}/{videos_to_watch}] Selecting video...")
                
                # Scroll results (human-like)
                await self._youtube_scroll_results()
                
                # Click on a random video
                video_opened = await self._youtube_open_random_video()
                if not video_opened:
                    continue
                
                # Watch video (time from settings)
                watch_time = random.randint(yt_watch_min, yt_watch_max)
                await self._youtube_watch_video(watch_time)
                
                # Like chance (from settings)
                if random.randint(1, 100) <= yt_like_percent:
                    await self._youtube_like_video()
                    # Random delay after like (1-4 seconds)
                    await HumanBehavior.random_delay(1, 4)
                
                # Watch Later chance (from settings)
                if random.randint(1, 100) <= yt_watchlater_percent:
                    await self._youtube_save_to_playlist()
                    # Random delay after save (1-4 seconds)
                    await HumanBehavior.random_delay(1, 4)
                
                # Go back to search results (if not last video)
                if i < videos_to_watch - 1:
                    await self._youtube_go_back_to_results()
                    await asyncio.sleep(random.uniform(1, 2))
            
            self.log("   ✅ YouTube activity complete")
            return True
            
        except Exception as e:
            self.log(f"   ⚠️ YouTube error: {e}")
            return False
    
    async def _navigate_to_youtube(self) -> bool:
        """Navigate to YouTube via Google search or direct."""
        try:
            # Try via Google search first
            search_success = await self._navigate_via_google_search("https://www.youtube.com/")
            
            if search_success:
                return True
            
            # Fallback: direct navigation in new tab
            self.log("   Direct YouTube navigation...")
            nav_success = await self._navigate_direct_in_new_tab("https://www.youtube.com/")
            return nav_success
            
        except Exception as e:
            logger.debug(f"Navigate to YouTube error: {e}")
            return False
    
    async def _youtube_search(self, query: str) -> bool:
        """Search on YouTube for a query."""
        try:
            self.log(f"   🔍 YouTube search: {query}")
            
            # Find search input
            search_input = await self.page.query_selector('input#search, input[name="search_query"], ytd-searchbox input')
            if not search_input:
                # Try clicking search button first
                search_btn = await self.page.query_selector('button#search-icon-legacy, #search-icon-legacy')
                if search_btn:
                    await search_btn.click()
                    await asyncio.sleep(0.5)
                    search_input = await self.page.query_selector('input#search, input[name="search_query"]')
            
            if not search_input:
                self.log("   ⚠️ YouTube search input not found")
                return False
            
            # Click and type (human-like)
            await search_input.click()
            await asyncio.sleep(random.uniform(0.3, 0.6))
            
            # Type character by character (100-250ms delay)
            for char in query:
                await self.page.keyboard.type(char)
                await asyncio.sleep(random.uniform(0.10, 0.25))
            
            await asyncio.sleep(random.uniform(0.5, 1.0))
            
            # Press Enter or click search button
            await self.page.keyboard.press("Enter")
            
            # Wait for results
            try:
                await self.page.wait_for_selector('ytd-video-renderer, ytd-item-section-renderer', timeout=10000)
            except:
                pass
            
            await asyncio.sleep(random.uniform(1.5, 2.5))
            
            return True
            
        except Exception as e:
            logger.debug(f"YouTube search error: {e}")
            return False
    
    async def _youtube_scroll_results(self):
        """Scroll through YouTube search results (human-like)."""
        try:
            # Random scroll behavior
            scroll_actions = random.randint(2, 5)
            
            for _ in range(scroll_actions):
                scroll_amount = random.randint(200, 500)
                await self.page.evaluate(f'window.scrollBy(0, {scroll_amount})')
                await asyncio.sleep(random.uniform(0.5, 1.5))
                
                # Occasionally scroll back a bit
                if random.random() < 0.2:
                    back_scroll = random.randint(50, 150)
                    await self.page.evaluate(f'window.scrollBy(0, -{back_scroll})')
                    await asyncio.sleep(random.uniform(0.3, 0.8))
            
        except Exception as e:
            logger.debug(f"YouTube scroll error: {e}")
    
    async def _youtube_open_random_video(self) -> bool:
        """Open a random video from search results."""
        try:
            # Find video links
            video_selectors = [
                'ytd-video-renderer a#video-title',
                'ytd-video-renderer #video-title',
                'a.yt-simple-endpoint.ytd-video-renderer',
                'ytd-item-section-renderer a#video-title',
            ]
            
            videos = []
            for selector in video_selectors:
                videos = await self.page.query_selector_all(selector)
                if videos:
                    break
            
            if not videos:
                self.log("   ⚠️ No videos found")
                return False
            
            # Select random video from first 10
            video_count = min(len(videos), 10)
            random_index = random.randint(0, video_count - 1)
            video = videos[random_index]
            
            # Get video title for logging
            try:
                title = await video.get_attribute('title') or await video.inner_text()
                title = title[:40] + '...' if len(title) > 40 else title
                self.log(f"   ▶️ Opening: {title}")
            except:
                self.log("   ▶️ Opening video...")
            
            # Scroll video into view
            await video.scroll_into_view_if_needed()
            await asyncio.sleep(random.uniform(0.3, 0.6))
            
            # Move mouse and click (human-like)
            box = await video.bounding_box()
            if box:
                target_x = box['x'] + box['width'] / 2 + random.randint(-10, 10)
                target_y = box['y'] + box['height'] / 2 + random.randint(-5, 5)
                await self.page.mouse.move(target_x, target_y)
                await asyncio.sleep(random.uniform(0.1, 0.3))
            
            await video.click()
            
            # Wait for video page to load
            try:
                await self.page.wait_for_selector('#player, ytd-watch-flexy', timeout=10000)
            except:
                pass
            
            await asyncio.sleep(random.uniform(1, 2))
            
            return True
            
        except Exception as e:
            logger.debug(f"Open video error: {e}")
            return False
    
    async def _youtube_watch_video(self, duration: int):
        """
        Simulate watching a YouTube video.
        
        Args:
            duration: Time to "watch" in seconds
        """
        try:
            self.log(f"   ⏱️ Watching for {duration}s...")
            
            start_time = time.time()
            
            while (time.time() - start_time) < duration:
                if self.should_stop:
                    break
                
                # Random actions while watching - mostly wait, rarely scroll
                action = random.choices(
                    ['wait', 'scroll', 'mouse'],
                    weights=[85, 5, 10]  # 85% wait, 5% scroll, 10% mouse
                )[0]
                
                if action == 'wait':
                    await asyncio.sleep(random.uniform(3, 7))
                    
                elif action == 'scroll':
                    # Very rare scroll (5% chance)
                    scroll_amount = random.randint(50, 150)
                    await self.page.evaluate(f'window.scrollBy(0, {scroll_amount})')
                    await asyncio.sleep(random.uniform(2, 4))
                    
                elif action == 'mouse':
                    # Occasional mouse movement to simulate presence
                    x = random.randint(200, 700)
                    y = random.randint(150, 450)
                    await self.page.mouse.move(x, y, steps=random.randint(3, 8))
                    await asyncio.sleep(random.uniform(1, 3))
            
            actual_time = int(time.time() - start_time)
            self.log(f"   ✓ Watched {actual_time}s")
            
        except Exception as e:
            logger.debug(f"Watch video error: {e}")
    
    async def _youtube_like_video(self) -> bool:
        """Like the current video."""
        try:
            # Multiple selectors for like button (YouTube changes frequently)
            like_selectors = [
                'like-button-view-model button',
                '#top-level-buttons-computed ytd-toggle-button-renderer:first-child button',
                'ytd-menu-renderer #top-level-buttons-computed button[aria-label*="like" i]',
                'button[aria-label*="like this video" i]',
                '#segmented-like-button button',
                'ytd-segmented-like-dislike-button-renderer button:first-child',
            ]
            
            like_btn = None
            for selector in like_selectors:
                like_btn = await self.page.query_selector(selector)
                if like_btn and await like_btn.is_visible():
                    break
                like_btn = None
            
            if not like_btn:
                logger.debug("Like button not found")
                return False
            
            # Check if already liked
            try:
                aria_pressed = await like_btn.get_attribute('aria-pressed')
                if aria_pressed == 'true':
                    self.log("   👍 Already liked")
                    return True
            except:
                pass
            
            # Scroll to like button area
            await like_btn.scroll_into_view_if_needed()
            await asyncio.sleep(random.uniform(0.3, 0.6))
            
            # Click
            await like_btn.click()
            self.log("   👍 Liked video")
            
            await asyncio.sleep(random.uniform(0.5, 1.0))
            
            return True
            
        except Exception as e:
            logger.debug(f"Like video error: {e}")
            return False
    
    async def _youtube_save_to_playlist(self) -> bool:
        """
        Save video to "Watch later" playlist.
        
        Supports two UI variants:
        - Shorts: Three dots menu → "Save to playlist"  
        - Regular videos: "Save" button → "Watch later" row click
        """
        try:
            self.log("   🔖 Saving to Watch later...")
            
            # Check if this is a Shorts video (vertical format)
            is_shorts = 'shorts' in self.page.url.lower()
            
            if is_shorts:
                # === SHORTS UI ===
                self.log("      Shorts detected, using menu...")
                
                # Click three dots menu button
                menu_clicked = await self.page.evaluate('''() => {
                    // Find menu button in Shorts player
                    const menuBtn = document.querySelector(
                        'ytd-menu-renderer yt-button-shape button, ' +
                        'ytd-menu-renderer button[aria-label*="More"], ' +
                        '#menu-button button'
                    );
                    if (menuBtn) {
                        menuBtn.click();
                        return true;
                    }
                    return false;
                }''')
                
                if not menu_clicked:
                    self.log("      ⚠️ Menu button not found")
                    return False
                
                await asyncio.sleep(random.uniform(0.8, 1.2))
                
                # Click "Save to playlist" in dropdown menu
                save_clicked = await self.page.evaluate('''() => {
                    // Look for menu items
                    const items = document.querySelectorAll(
                        'ytd-menu-service-item-renderer, ' +
                        'yt-list-item-view-model, ' +
                        'tp-yt-paper-item'
                    );
                    for (const item of items) {
                        const text = item.innerText || item.textContent || '';
                        const label = item.getAttribute('aria-label') || '';
                        if (text.toLowerCase().includes('save to playlist') ||
                            text.toLowerCase().includes('save') ||
                            label.toLowerCase().includes('save')) {
                            item.click();
                            return true;
                        }
                    }
                    return false;
                }''')
                
                if not save_clicked:
                    self.log("      ⚠️ Save to playlist option not found")
                    await self.page.keyboard.press("Escape")
                    return False
                
                await asyncio.sleep(random.uniform(0.8, 1.2))
            
            else:
                # === REGULAR VIDEO UI ===
                self.log("      Regular video, clicking Save button...")
                
                # Click Save button - exact selector from screenshot
                save_clicked = await self.page.evaluate('''() => {
                    // Method 1: Find by aria-label (most reliable)
                    let btn = document.querySelector('button[aria-label="Save to playlist"]');
                    if (btn) {
                        btn.click();
                        return 'aria-label';
                    }
                    
                    // Method 2: Find button with "Save" text content
                    const buttons = document.querySelectorAll('button.yt-spec-button-shape-next');
                    for (const b of buttons) {
                        const textDiv = b.querySelector('.yt-spec-button-shape-next__button-text-content');
                        if (textDiv && textDiv.textContent.trim().toLowerCase() === 'save') {
                            b.click();
                            return 'text-content';
                        }
                    }
                    
                    // Method 3: Find in top-level buttons
                    const topButtons = document.querySelectorAll('#top-level-buttons-computed button, #actions button');
                    for (const b of topButtons) {
                        const text = b.innerText || b.textContent || '';
                        const label = b.getAttribute('aria-label') || '';
                        if (text.toLowerCase().includes('save') || label.toLowerCase().includes('save')) {
                            b.click();
                            return 'fallback';
                        }
                    }
                    
                    return null;
                }''')
                
                if not save_clicked:
                    # Try through "More actions" menu as last resort
                    self.log("      Trying More actions menu...")
                    more_clicked = await self.page.evaluate('''() => {
                        const moreBtn = document.querySelector('button[aria-label="More actions"]');
                        if (moreBtn) {
                            moreBtn.click();
                            return true;
                        }
                        return false;
                    }''')
                    
                    if more_clicked:
                        await asyncio.sleep(random.uniform(0.8, 1.2))
                        
                        save_in_menu = await self.page.evaluate('''() => {
                            const items = document.querySelectorAll(
                                'ytd-menu-service-item-renderer, tp-yt-paper-item'
                            );
                            for (const item of items) {
                                const text = item.innerText || '';
                                if (text.toLowerCase().includes('save')) {
                                    item.click();
                                    return true;
                                }
                            }
                            return false;
                        }''')
                        
                        if not save_in_menu:
                            self.log("      ⚠️ Save not found in menu")
                            await self.page.keyboard.press("Escape")
                            return False
                    else:
                        self.log("      ⚠️ No Save button found")
                        return False
                else:
                    self.log(f"      Found Save button via {save_clicked}")
                
                await asyncio.sleep(random.uniform(0.8, 1.2))
            
            # === HANDLE "Save to..." POPUP ===
            self.log("      Looking for Watch later option...")
            
            # Wait for popup to appear
            try:
                await self.page.wait_for_selector(
                    'yt-list-item-view-model[aria-label*="Watch later"], ' +
                    'toggleable-list-item-view-model, ' +
                    'ytd-playlist-add-to-option-renderer, ' +
                    'ytd-add-to-playlist-renderer',
                    timeout=3000
                )
            except:
                self.log("      ⚠️ Popup did not appear")
                return False
            
            await asyncio.sleep(random.uniform(0.5, 0.8))
            
            # Click "Watch later" - using exact selectors from screenshot
            watch_later_clicked = await self.page.evaluate('''() => {
                // Method 1: Find by aria-label (most reliable - from screenshot)
                // aria-label="Watch later, Private, Not selected"
                let item = document.querySelector('yt-list-item-view-model[aria-label*="Watch later"]');
                if (item) {
                    item.click();
                    return 'aria-label';
                }
                
                // Method 2: Find toggleable-list-item-view-model containing Watch later
                const toggleables = document.querySelectorAll('toggleable-list-item-view-model');
                for (const t of toggleables) {
                    const text = t.innerText || t.textContent || '';
                    if (text.toLowerCase().includes('watch later')) {
                        t.click();
                        return 'toggleable';
                    }
                }
                
                // Method 3: Find by label class (from screenshot)
                const labels = document.querySelectorAll('.yt-list-item-view-model__label');
                for (const label of labels) {
                    if (label.textContent.toLowerCase().includes('watch later')) {
                        // Click parent container
                        const container = label.closest('yt-list-item-view-model') || 
                                         label.closest('toggleable-list-item-view-model') ||
                                         label.parentElement;
                        if (container) {
                            container.click();
                            return 'label-parent';
                        }
                    }
                }
                
                // Method 4: Find in playlist options (old UI)
                const options = document.querySelectorAll('ytd-playlist-add-to-option-renderer');
                for (const opt of options) {
                    const text = opt.innerText || '';
                    if (text.toLowerCase().includes('watch later')) {
                        const checkbox = opt.querySelector('#checkbox');
                        if (checkbox) {
                            checkbox.click();
                            return 'old-checkbox';
                        }
                        opt.click();
                        return 'old-option';
                    }
                }
                
                // Method 5: First item is usually Watch later
                const firstItem = document.querySelector(
                    'yt-list-item-view-model[role="listitem"], ' +
                    'ytd-playlist-add-to-option-renderer:first-child'
                );
                if (firstItem) {
                    firstItem.click();
                    return 'first-item';
                }
                
                return null;
            }''')
            
            if watch_later_clicked:
                self.log(f"      ✓ Clicked Watch later ({watch_later_clicked})")
                await asyncio.sleep(random.uniform(0.5, 0.8))
                
                # Close popup
                await self.page.keyboard.press("Escape")
                await asyncio.sleep(random.uniform(0.3, 0.5))
                
                self.log("   ✓ Saved to Watch later")
                return True
            else:
                self.log("      ⚠️ Watch later option not found in popup")
                await self.page.keyboard.press("Escape")
                return False
            
        except Exception as e:
            self.log(f"      ⚠️ Error: {e}")
            try:
                await self.page.keyboard.press("Escape")
            except:
                pass
            return False
    
    async def _youtube_go_back_to_results(self):
        """Go back to YouTube search results."""
        try:
            # Try browser back
            await self.page.go_back()
            await asyncio.sleep(random.uniform(1, 2))
            
            # Verify we're on search results
            try:
                await self.page.wait_for_selector('ytd-video-renderer', timeout=5000)
            except:
                # If not, search again might be needed
                pass
            
        except Exception as e:
            logger.debug(f"Go back error: {e}")
    
    async def _quick_gmail_check(self, read_percent: int, read_time_min: int, read_time_max: int):
        """Quick Gmail check - visit inbox and read a few emails."""
        # Calculate random read time from range
        read_time = random.randint(read_time_min, read_time_max)
        
        try:
            await self.page.goto("https://mail.google.com/mail/u/0/#inbox", 
                                 wait_until="domcontentloaded", timeout=30000)
            await HumanBehavior.random_delay(2, 3)
            await self.mute_page()
            
            # Wait for inbox
            try:
                await self.page.wait_for_selector('tr.zA', timeout=10000)
            except:
                self.log("   Gmail not loaded")
                return
            
            # Get settings for promo/spam chance (from settings or default 10%)
            promo_spam_percent = getattr(self, '_gmail_promo_spam_percent', 10)
            
            # Pick folder based on settings
            if random.randint(1, 100) <= promo_spam_percent:
                # Check promotions or spam (pick one)
                folder_choice = random.choice(['promotions', 'spam'])
            else:
                folder_choice = 'inbox'
            
            folders = {
                'inbox': ("https://mail.google.com/mail/u/0/#inbox", "📥 Inbox"),
                'promotions': ("https://mail.google.com/mail/u/0/#category/promotions", "🏷️ Promotions"),
                'spam': ("https://mail.google.com/mail/u/0/#spam", "🚫 Spam"),
            }
            
            folder_url, folder_name = folders[folder_choice]
            
            if folder_choice != 'inbox':
                await self.page.goto(folder_url, wait_until="domcontentloaded", timeout=15000)
                await HumanBehavior.random_delay(1, 2)
            
            self.log(f"   {folder_name} (read time: {read_time}s)")
            
            # Read emails
            read_count = await self._read_emails_in_folder(
                folder_name=folder_name,
                folder_url=folder_url,
                read_percent=read_percent,
                read_time=read_time
            )
            
            self.log(f"   ✓ Read {read_count} emails")
            
        except Exception as e:
            self.log(f"   Gmail error: {e}")
    
    async def perform_gmail_activity(self, read_percent: int = 40, read_time_min: int = 15, read_time_max: int = 45):
        """
        Navigate to Gmail and read a percentage of emails in Inbox, Promotions, and Spam.
        
        Args:
            read_percent: Percentage of visible emails to read (10-100)
            read_time_min: Minimum time to spend on each email in seconds
            read_time_max: Maximum time to spend on each email in seconds
        """
        if not self.page:
            return
        
        # Calculate random read time for this session
        read_time = random.randint(read_time_min, read_time_max)
        self.log(f"📧 Opening Gmail... (read time: {read_time}s per email)")
        
        try:
            # Navigate to Gmail inbox
            await self.page.goto("https://mail.google.com/mail/u/0/#inbox", 
                                 wait_until="domcontentloaded", timeout=30000)
            await HumanBehavior.random_delay(2, 4)
            await self.mute_page()
            
            # Wait for Gmail to fully load
            try:
                await self.page.wait_for_selector('tr.zA', timeout=15000)
                self.log("Gmail inbox loaded")
            except Exception:
                try:
                    await self.page.wait_for_selector('div[role="main"]', timeout=10000)
                    self.log("Gmail loaded (alternative)")
                except Exception:
                    self.log("⚠️ Gmail inbox not detected - may need login")
                    return
            
            total_read = 0
            
            # SAFE FOLDERS ONLY: Inbox, Promotions, Spam
            # We use direct URLs to avoid clicking on any dangerous menu items
            folders = [
                ("inbox", "https://mail.google.com/mail/u/0/#inbox", "📥 Inbox"),
                ("promotions", "https://mail.google.com/mail/u/0/#category/promotions", "🏷️ Promotions"),
                ("spam", "https://mail.google.com/mail/u/0/#spam", "🚫 Spam"),
            ]
            
            # Get promo/spam chance from settings (default 10%)
            promo_spam_percent = getattr(self, '_gmail_promo_spam_percent', 10)
            
            # Always start with inbox, check promotions OR spam based on settings
            folders_to_visit = [folders[0]]  # Always inbox
            if random.randint(1, 100) <= promo_spam_percent:
                # Pick either promotions or spam (not both)
                extra_folder = random.choice([folders[1], folders[2]])
                folders_to_visit.append(extra_folder)
            
            for folder_id, folder_url, folder_name in folders_to_visit:
                if self.should_stop:
                    break
                
                self.log(f"\n{folder_name} - checking...")
                
                # Navigate directly via URL (safe, no menu clicking)
                await self.page.goto(folder_url, wait_until="domcontentloaded", timeout=20000)
                await HumanBehavior.random_delay(1.5, 3)
                await self.mute_page()
                
                # Wait for emails to load
                try:
                    await self.page.wait_for_selector('tr.zA', timeout=10000)
                except:
                    self.log(f"   {folder_name} is empty or not loaded")
                    continue
                
                # Read emails in this folder
                read_count = await self._read_emails_in_folder(
                    folder_name=folder_name,
                    folder_url=folder_url,
                    read_percent=read_percent,
                    read_time=read_time
                )
                total_read += read_count
                
                await HumanBehavior.random_delay(1, 3)
            
            self.log(f"\n📧 Gmail activity complete: read {total_read} emails total")
            
        except Exception as e:
            self.log(f"❌ Gmail error: {e}")
    
    async def _read_emails_in_folder(self, folder_name: str, folder_url: str, 
                                      read_percent: int, read_time: int) -> int:
        """Read a percentage of emails in the current folder."""
        
        # Track if we've clicked a link in any email yet
        link_clicked_this_session = getattr(self, '_gmail_link_clicked', False)
        
        # Find all email rows
        email_rows = await self.page.query_selector_all('tr.zA')
        if not email_rows:
            email_rows = await self.page.query_selector_all('div[role="main"] tr[draggable="true"]')
        
        total_emails = len(email_rows)
        
        if total_emails == 0:
            self.log(f"   📭 {folder_name} is empty")
            return 0
        
        # Calculate how many emails to read
        emails_to_read = max(1, int(total_emails * read_percent / 100))
        self.log(f"   📬 Found {total_emails} emails, will read {emails_to_read} ({read_percent}%)")
        
        # Randomly select which emails to read
        indices_to_read = random.sample(range(total_emails), min(emails_to_read, total_emails))
        indices_to_read.sort()
        
        emails_read = 0
        
        for idx in indices_to_read:
            if self.should_stop:
                self.log("⏹ Stopping Gmail activity")
                break
            
            try:
                # Re-query email rows (DOM changes after navigation)
                email_rows = await self.page.query_selector_all('tr.zA')
                if not email_rows:
                    email_rows = await self.page.query_selector_all('div[role="main"] tr[draggable="true"]')
                
                if idx >= len(email_rows):
                    continue
                
                email_row = email_rows[idx]
                
                # Get email subject for logging
                try:
                    subject_elem = await email_row.query_selector('span.bog, span.y2')
                    subject = await subject_elem.inner_text() if subject_elem else "No subject"
                    subject = subject[:35] + "..." if len(subject) > 35 else subject
                except:
                    subject = "Email"
                
                emails_read += 1
                self.log(f"   📖 [{emails_read}/{emails_to_read}]: {subject}")
                
                # Click to open the email
                await email_row.click()
                await HumanBehavior.random_delay(1.5, 2.5)
                
                # Wait for email content to load
                try:
                    await self.page.wait_for_selector('div.a3s, div.ii.gt', timeout=10000)
                except:
                    pass
                
                await self.mute_page()
                
                # === TRY TO CLICK LINK IN FIRST EMAIL WITH LINKS ===
                # Check if click_links is enabled in settings
                click_links_enabled = getattr(self, '_gmail_click_links', True)
                if click_links_enabled and not link_clicked_this_session:
                    clicked = await self._try_click_email_link()
                    if clicked:
                        link_clicked_this_session = True
                        self._gmail_link_clicked = True
                
                # === SIMULATE READING EMAIL CONTENT ===
                await self._read_email_content(read_time)
                
                # === GO BACK TO FOLDER ===
                await self._go_back_to_folder(folder_url)
                
            except Exception as e:
                self.log(f"      ⚠️ Error: {e}")
                # Safe recovery - go back to folder via URL
                try:
                    await self.page.goto(folder_url, wait_until="domcontentloaded", timeout=15000)
                    await HumanBehavior.random_delay(1, 2)
                except:
                    pass
                continue
        
        return emails_read
    
    async def _try_click_email_link(self) -> bool:
        """
        Try to find and click a link in the email body.
        Opens in new tab, browses briefly, then returns to Gmail.
        
        Returns:
            True if a link was clicked, False otherwise
        """
        try:
            # Find links in email body
            # Gmail email content is in div.a3s or div.ii.gt
            email_body_selectors = ['div.a3s', 'div.ii.gt', 'div[data-message-id]']
            
            links = []
            for selector in email_body_selectors:
                body = await self.page.query_selector(selector)
                if body:
                    links = await body.query_selector_all('a[href]')
                    if links:
                        break
            
            if not links:
                return False
            
            # Filter valid links (skip mailto:, google internal, unsubscribe, etc.)
            valid_link = None
            for link in links:
                try:
                    href = await link.get_attribute('href') or ''
                    href_lower = href.lower()
                    
                    # Skip invalid links
                    if not href.startswith('http'):
                        continue
                    if any(x in href_lower for x in [
                        'mailto:', 'tel:', 'javascript:',
                        'google.com', 'gmail.com', 'goo.gl',
                        'unsubscribe', 'opt-out', 'optout',
                        'manage-preferences', 'email-preferences',
                        'privacy', 'terms', 'policy'
                    ]):
                        continue
                    
                    # Check if link is visible
                    if await link.is_visible():
                        valid_link = link
                        break
                        
                except:
                    continue
            
            if not valid_link:
                return False
            
            # Get href for logging
            href = await valid_link.get_attribute('href') or ''
            href_short = href[:50] + '...' if len(href) > 50 else href
            
            self.log(f"      🔗 Clicking link: {href_short}")
            
            # Store current page count
            pages_before = len(self.context.pages)
            
            # Click the link
            await valid_link.click()
            await asyncio.sleep(2)
            
            # Check if new tab opened
            pages_after = len(self.context.pages)
            
            if pages_after > pages_before:
                # New tab opened - switch to it
                new_tab = self.context.pages[-1]
                await new_tab.bring_to_front()
                
                self.log(f"      🌐 Browsing linked site...")
                
                # Wait for page to load
                try:
                    await new_tab.wait_for_load_state("domcontentloaded", timeout=10000)
                except:
                    pass
                
                await asyncio.sleep(random.uniform(1, 2))
                
                # Random scrolling on the linked page
                browse_time = random.uniform(5, 15)
                start_time = time.time()
                
                while (time.time() - start_time) < browse_time:
                    # Random scroll
                    scroll_amount = random.randint(100, 400)
                    await new_tab.evaluate(f'window.scrollBy(0, {scroll_amount})')
                    await asyncio.sleep(random.uniform(1, 3))
                    
                    # Occasionally scroll back
                    if random.random() < 0.2:
                        await new_tab.evaluate(f'window.scrollBy(0, -{random.randint(50, 150)})')
                        await asyncio.sleep(random.uniform(0.5, 1.5))
                
                self.log(f"      ✓ Browsed {int(time.time() - start_time)}s, closing tab")
                
                # Close the tab and return to Gmail
                await new_tab.close()
                await asyncio.sleep(0.5)
                
                # Bring Gmail tab back to front
                await self.page.bring_to_front()
                
            else:
                # Link opened in same tab - navigate back
                self.log(f"      🌐 Link opened in same tab, browsing...")
                
                browse_time = random.uniform(5, 15)
                start_time = time.time()
                
                while (time.time() - start_time) < browse_time:
                    scroll_amount = random.randint(100, 400)
                    await self.page.evaluate(f'window.scrollBy(0, {scroll_amount})')
                    await asyncio.sleep(random.uniform(1, 3))
                
                self.log(f"      ✓ Browsed {int(time.time() - start_time)}s, going back")
                
                # Go back to Gmail
                await self.page.go_back()
                await asyncio.sleep(1)
            
            return True
            
        except Exception as e:
            logger.debug(f"Click email link error: {e}")
            return False
    
    async def _read_email_content(self, read_time: int):
        """
        Simulate human-like reading of email content with smooth scrolling.
        Gmail has a nested scroll container for email content.
        """
        actual_read_time = random.randint(int(read_time * 0.7), int(read_time * 1.3))
        start_time = time.time()
        
        # Find the scrollable email container
        # Gmail uses different containers - we need to find the right one
        scroll_container_js = """
            (() => {
                // Gmail's main scrollable area for email view
                // Try multiple selectors as Gmail structure varies
                const selectors = [
                    'div.nH.bkK',           // Main email scroll container
                    'div.nH.if',            // Alternative container
                    'div.nH.hx',            // Another variant
                    'div[role="list"]',     // Conversation view
                    'div.AO',               // Outer container
                    'div.Tm.aeJ'            // Message pane
                ];
                
                for (const sel of selectors) {
                    const el = document.querySelector(sel);
                    if (el && el.scrollHeight > el.clientHeight) {
                        return sel;
                    }
                }
                
                // Fallback: find any scrollable div in the main area
                const mainArea = document.querySelector('div[role="main"]');
                if (mainArea) {
                    const divs = mainArea.querySelectorAll('div');
                    for (const div of divs) {
                        if (div.scrollHeight > div.clientHeight + 100 && 
                            div.clientHeight > 200) {
                            return null; // Will use element directly
                        }
                    }
                }
                return null;
            })()
        """
        
        await HumanBehavior.random_delay(0.5, 1.5)
        
        while (time.time() - start_time) < actual_read_time:
            if self.should_stop:
                break
            
            # Random mouse movement
            await HumanBehavior.random_mouse(self.page)
            
            # Varied scroll behavior
            scroll_type = random.choices(
                ['small', 'medium', 'pause', 'back'],
                weights=[40, 30, 20, 10]
            )[0]
            
            if scroll_type == 'small':
                scroll_amount = random.randint(30, 80)
                await self._smooth_email_scroll(scroll_amount)
                await HumanBehavior.random_delay(1.5, 4)
                
            elif scroll_type == 'medium':
                scroll_amount = random.randint(100, 200)
                await self._smooth_email_scroll(scroll_amount)
                await HumanBehavior.random_delay(1, 2.5)
                
            elif scroll_type == 'pause':
                await HumanBehavior.random_delay(2, 5)
                
            elif scroll_type == 'back':
                scroll_amount = random.randint(-100, -30)
                await self._smooth_email_scroll(scroll_amount)
                await HumanBehavior.random_delay(1, 2)
        
        self.log(f"      ✓ Read for {int(time.time() - start_time)}s")
    
    async def _smooth_email_scroll(self, total_amount: int):
        """
        Scroll within Gmail's email view container.
        Uses multiple methods to find and scroll the right element.
        """
        steps = random.randint(4, 8)
        step_amount = total_amount / steps
        
        for _ in range(steps):
            try:
                await self.page.evaluate(f"""
                    (() => {{
                        // Method 1: Find scrollable container in email view
                        const containers = [
                            document.querySelector('div.nH.bkK'),
                            document.querySelector('div.nH.if'), 
                            document.querySelector('div.AO'),
                            document.querySelector('div.Tm.aeJ'),
                            document.querySelector('div[role="main"] div.nH')
                        ];
                        
                        for (const container of containers) {{
                            if (container && container.scrollHeight > container.clientHeight) {{
                                container.scrollBy({{
                                    top: {step_amount},
                                    behavior: 'auto'
                                }});
                                return true;
                            }}
                        }}
                        
                        // Method 2: Find any deeply scrollable div in main area
                        const main = document.querySelector('div[role="main"]');
                        if (main) {{
                            const allDivs = main.querySelectorAll('div');
                            for (const div of allDivs) {{
                                const style = window.getComputedStyle(div);
                                const isScrollable = (style.overflowY === 'auto' || style.overflowY === 'scroll') &&
                                                     div.scrollHeight > div.clientHeight + 50;
                                if (isScrollable && div.clientHeight > 200) {{
                                    div.scrollBy({{
                                        top: {step_amount},
                                        behavior: 'auto'
                                    }});
                                    return true;
                                }}
                            }}
                        }}
                        
                        // Method 3: Scroll the whole page as fallback
                        window.scrollBy(0, {step_amount});
                        return false;
                    }})()
                """)
            except:
                try:
                    await self.page.evaluate(f"window.scrollBy(0, {step_amount})")
                except:
                    pass
            
            await asyncio.sleep(random.uniform(0.05, 0.15))
    
    async def _go_back_to_folder(self, folder_url: str):
        """
        Navigate back to folder after reading an email.
        Uses multiple methods for reliability.
        """
        try:
            # Method 1: Try clicking Gmail's back button/arrow
            back_selectors = [
                'div[act="19"]',
                'div[aria-label="Back to Inbox"]',
                'div[aria-label="Назад"]',
                'div[aria-label="Back"]',
                'div[data-tooltip*="Back"]',
                'div[data-tooltip*="Назад"]',
            ]
            
            for selector in back_selectors:
                try:
                    back_btn = await self.page.query_selector(selector)
                    if back_btn and await back_btn.is_visible():
                        await back_btn.click()
                        await HumanBehavior.random_delay(1, 2)
                        # Check if we're back in the folder
                        try:
                            await self.page.wait_for_selector('tr.zA', timeout=5000)
                            return  # Success
                        except:
                            pass
                except:
                    continue
            
            # Method 2: Keyboard shortcut
            try:
                await self.page.keyboard.press("u")  # Gmail shortcut
                await HumanBehavior.random_delay(1, 1.5)
                await self.page.wait_for_selector('tr.zA', timeout=5000)
                return
            except:
                pass
            
            # Method 3: Direct URL navigation (safest fallback)
            await self.page.goto(folder_url, wait_until="domcontentloaded", timeout=15000)
            await HumanBehavior.random_delay(1, 2)
            
        except:
            # Ultimate fallback
            await self.page.goto(folder_url, wait_until="domcontentloaded", timeout=15000)
    
    def stop(self):
        self.should_stop = True
        self.log("Stopping...")
    
    # ==========================================================================
    # GOOGLE AUTH ON THIRD-PARTY SITES
    # ==========================================================================
    
    # Buttons/links to find login/register in navigation
    # Languages: EN, RU, DE, FR, ES, IT, PT, NL, PL, RO, EL, CS, HU, SV, BG, DA, FI, SK, HR, LT, SL, LV, ET, UK, TR, NO
    AUTH_NAV_TEXTS = {
        'login': [
            # English
            'Sign in', 'Log in', 'Login', 'Log In', 'Sign In',
            # Russian
            'Войти', 'Вход', 'Авторизация', 'Авторизоваться',
            # German
            'Anmelden', 'Einloggen', 'Login',
            # French
            'Connexion', 'Se connecter', 'Connectez-vous',
            # Spanish
            'Iniciar sesión', 'Acceder', 'Entrar', 'Ingresar',
            # Italian
            'Accedi', 'Accesso', 'Entra', 'Login',
            # Portuguese
            'Entrar', 'Iniciar sessão', 'Acessar', 'Login',
            # Dutch
            'Inloggen', 'Aanmelden', 'Log in',
            # Polish
            'Zaloguj się', 'Zaloguj', 'Logowanie',
            # Romanian
            'Conectare', 'Autentificare', 'Intră în cont',
            # Greek
            'Σύνδεση', 'Είσοδος',
            # Czech
            'Přihlásit se', 'Přihlášení',
            # Hungarian
            'Bejelentkezés', 'Belépés',
            # Swedish
            'Logga in', 'Inloggning',
            # Bulgarian
            'Вход', 'Влизане', 'Влез',
            # Danish
            'Log ind', 'Log på',
            # Finnish
            'Kirjaudu sisään', 'Kirjaudu',
            # Slovak
            'Prihlásiť sa', 'Prihlásenie',
            # Croatian
            'Prijava', 'Prijavite se',
            # Lithuanian
            'Prisijungti', 'Prisijungimas',
            # Slovenian
            'Prijava', 'Prijavite se',
            # Latvian
            'Pieslēgties', 'Ieiet',
            # Estonian
            'Logi sisse', 'Sisselogimine',
            # Ukrainian
            'Увійти', 'Вхід',
            # Turkish
            'Giriş yap', 'Oturum aç',
            # Norwegian
            'Logg inn', 'Logg på',
            # Japanese
            'ログイン', 'サインイン',
            # Chinese
            '登录', '登入', '登陆',
            # Korean
            '로그인',
        ],
        'register': [
            # English
            'Sign up', 'Register', 'Create account', 'Join', 'Get started', 'Join now', 'Sign Up',
            # Russian
            'Регистрация', 'Зарегистрироваться', 'Создать аккаунт', 'Создать учётную запись',
            # German
            'Registrieren', 'Konto erstellen', 'Anmelden', 'Jetzt registrieren',
            # French
            "S'inscrire", 'Créer un compte', 'Inscription', 'Rejoindre',
            # Spanish
            'Registrarse', 'Crear cuenta', 'Regístrate', 'Únete',
            # Italian
            'Registrati', 'Crea account', 'Iscriviti', 'Registrazione',
            # Portuguese
            'Cadastrar', 'Criar conta', 'Registrar', 'Registre-se', 'Inscrever-se',
            # Dutch
            'Registreren', 'Account aanmaken', 'Inschrijven', 'Aanmelden',
            # Polish
            'Zarejestruj się', 'Rejestracja', 'Utwórz konto', 'Załóż konto',
            # Romanian
            'Înregistrare', 'Creează cont', 'Înregistrează-te',
            # Greek
            'Εγγραφή', 'Δημιουργία λογαριασμού',
            # Czech
            'Registrace', 'Vytvořit účet', 'Zaregistrovat se',
            # Hungarian
            'Regisztráció', 'Fiók létrehozása', 'Regisztrálj',
            # Swedish
            'Registrera', 'Skapa konto', 'Registrera dig',
            # Bulgarian
            'Регистрация', 'Създаване на акаунт', 'Регистрирай се',
            # Danish
            'Registrer', 'Opret konto', 'Tilmeld dig',
            # Finnish
            'Rekisteröidy', 'Luo tili',
            # Slovak
            'Registrácia', 'Vytvoriť účet', 'Zaregistrovať sa',
            # Croatian
            'Registracija', 'Stvori račun', 'Registriraj se',
            # Lithuanian
            'Registracija', 'Sukurti paskyrą', 'Registruotis',
            # Slovenian
            'Registracija', 'Ustvari račun',
            # Latvian
            'Reģistrēties', 'Izveidot kontu',
            # Estonian
            'Registreeru', 'Loo konto',
            # Ukrainian
            'Реєстрація', 'Зареєструватися', 'Створити акаунт',
            # Turkish
            'Kaydol', 'Kayıt ol', 'Hesap oluştur',
            # Norwegian
            'Registrer deg', 'Opprett konto',
            # Japanese
            '新規登録', 'アカウント作成', '登録',
            # Chinese
            '注册', '创建账户', '立即注册',
            # Korean
            '회원가입', '가입하기',
        ],
        'logged_in': [
            # English
            'Profile', 'My account', 'Account', 'Dashboard', 'Logout', 'Sign out', 'Log out', 'My Profile',
            # Russian
            'Профиль', 'Мой аккаунт', 'Личный кабинет', 'Выйти', 'Выход', 'Мой профиль',
            # German
            'Profil', 'Mein Konto', 'Abmelden', 'Ausloggen', 'Konto',
            # French
            'Profil', 'Mon compte', 'Déconnexion', 'Se déconnecter',
            # Spanish
            'Perfil', 'Mi cuenta', 'Cerrar sesión', 'Salir',
            # Italian
            'Profilo', 'Il mio account', 'Esci', 'Disconnetti',
            # Portuguese
            'Perfil', 'Minha conta', 'Sair', 'Desconectar',
            # Dutch
            'Profiel', 'Mijn account', 'Uitloggen', 'Afmelden',
            # Polish
            'Profil', 'Moje konto', 'Wyloguj', 'Wyloguj się',
            # Romanian
            'Profil', 'Contul meu', 'Deconectare', 'Ieșire',
            # Greek
            'Προφίλ', 'Ο λογαριασμός μου', 'Αποσύνδεση',
            # Czech
            'Profil', 'Můj účet', 'Odhlásit se',
            # Hungarian
            'Profil', 'Fiókom', 'Kijelentkezés',
            # Swedish
            'Profil', 'Mitt konto', 'Logga ut',
            # Bulgarian
            'Профил', 'Моят акаунт', 'Изход',
            # Danish
            'Profil', 'Min konto', 'Log ud',
            # Finnish
            'Profiili', 'Oma tili', 'Kirjaudu ulos',
            # Slovak
            'Profil', 'Môj účet', 'Odhlásiť sa',
            # Croatian
            'Profil', 'Moj račun', 'Odjava',
            # Lithuanian
            'Profilis', 'Mano paskyra', 'Atsijungti',
            # Slovenian
            'Profil', 'Moj račun', 'Odjava',
            # Latvian
            'Profils', 'Mans konts', 'Iziet',
            # Estonian
            'Profiil', 'Minu konto', 'Logi välja',
            # Ukrainian
            'Профіль', 'Мій акаунт', 'Вийти',
            # Turkish
            'Profil', 'Hesabım', 'Çıkış yap',
            # Norwegian
            'Profil', 'Min konto', 'Logg ut',
        ]
    }
    
    # Google auth button patterns - all EU languages + popular
    GOOGLE_AUTH_TEXTS = [
        # English
        'Continue with Google', 'Sign in with Google', 'Log in with Google',
        'Sign up with Google', 'Register with Google', 'Google',
        'Login with Google', 'Connect with Google',
        # Russian
        'Войти через Google', 'Продолжить с Google', 'Зарегистрироваться через Google',
        'Вход через Google', 'Авторизоваться через Google',
        # German
        'Mit Google anmelden', 'Mit Google fortfahren', 'Mit Google registrieren',
        'Weiter mit Google', 'Über Google anmelden',
        # French
        'Continuer avec Google', "S'inscrire avec Google", 'Se connecter avec Google',
        'Connexion avec Google',
        # Spanish
        'Continuar con Google', 'Iniciar sesión con Google', 'Registrarse con Google',
        'Acceder con Google',
        # Italian
        'Continua con Google', 'Accedi con Google', 'Registrati con Google',
        'Iscriviti con Google',
        # Portuguese
        'Continuar com Google', 'Entrar com Google', 'Registrar com Google',
        'Fazer login com Google', 'Cadastrar com Google',
        # Dutch
        'Doorgaan met Google', 'Inloggen met Google', 'Registreren met Google',
        'Aanmelden met Google',
        # Polish
        'Kontynuuj przez Google', 'Zaloguj się przez Google', 'Zarejestruj się przez Google',
        'Zaloguj przez Google',
        # Romanian
        'Continuă cu Google', 'Conectează-te cu Google', 'Înregistrează-te cu Google',
        # Greek
        'Συνέχεια με Google', 'Σύνδεση με Google', 'Εγγραφή με Google',
        # Czech
        'Pokračovat přes Google', 'Přihlásit se přes Google', 'Registrovat přes Google',
        # Hungarian
        'Folytatás Google-fiókkal', 'Bejelentkezés Google-fiókkal', 'Regisztráció Google-fiókkal',
        # Swedish
        'Fortsätt med Google', 'Logga in med Google', 'Registrera med Google',
        # Bulgarian
        'Продължи с Google', 'Вход с Google', 'Регистрация с Google',
        # Danish
        'Fortsæt med Google', 'Log ind med Google', 'Registrer med Google',
        # Finnish
        'Jatka Google-tilillä', 'Kirjaudu Google-tilillä', 'Rekisteröidy Googlella',
        # Slovak
        'Pokračovať cez Google', 'Prihlásiť sa cez Google',
        # Croatian
        'Nastavi s Googleom', 'Prijavi se s Googleom',
        # Lithuanian
        'Tęsti su Google', 'Prisijungti su Google',
        # Slovenian
        'Nadaljuj z Google', 'Prijava z Google',
        # Latvian
        'Turpināt ar Google', 'Pieslēgties ar Google',
        # Estonian
        'Jätka Google\'iga', 'Logi sisse Google\'iga',
        # Ukrainian
        'Продовжити з Google', 'Увійти через Google',
        # Turkish
        'Google ile devam et', 'Google ile giriş yap',
        # Norwegian
        'Fortsett med Google', 'Logg inn med Google',
        # Japanese
        'Googleで続行', 'Googleでログイン', 'Googleで登録',
        # Chinese
        'Google登录', '使用Google登录', '通过Google继续', '使用Google继续',
        # Korean
        'Google로 계속하기', 'Google로 로그인',
    ]
    
    # "Don't have account?" / "Already have account?" switchers
    FORM_SWITCH_TEXTS = {
        'to_register': [
            # English
            "Don't have an account", "Create account", "Sign up", "Register here",
            "New user", "Create new account", "Join now",
            # Russian
            "Нет аккаунта", "Создать аккаунт", "Зарегистрироваться", "Новый пользователь",
            # German
            "Kein Konto", "Registrieren", "Konto erstellen", "Noch kein Konto",
            # French
            "Pas de compte", "Créer un compte", "Pas encore de compte", "Nouveau",
            # Spanish
            "¿No tienes cuenta", "Crear cuenta", "Regístrate", "¿Eres nuevo",
            # Italian
            "Non hai un account", "Crea account", "Registrati", "Nuovo utente",
            # Portuguese
            "Não tem conta", "Criar conta", "Cadastre-se", "Novo usuário",
            # Dutch
            "Geen account", "Account aanmaken", "Registreren",
            # Polish
            "Nie masz konta", "Utwórz konto", "Zarejestruj się",
            # Romanian
            "Nu ai cont", "Creează cont",
            # Greek
            "Δεν έχετε λογαριασμό", "Δημιουργία λογαριασμού",
            # Czech
            "Nemáte účet", "Vytvořit účet",
            # Hungarian
            "Nincs fiókja", "Fiók létrehozása",
            # Swedish
            "Har du inget konto", "Skapa konto",
            # Bulgarian
            "Нямате акаунт", "Създаване на акаунт",
            # Danish
            "Har du ikke en konto", "Opret konto",
            # Finnish
            "Ei tiliä", "Luo tili",
            # Ukrainian
            "Немає акаунту", "Створити акаунт",
            # Turkish
            "Hesabınız yok mu", "Hesap oluştur",
        ],
        'to_login': [
            # English
            "Already have an account", "Sign in", "Log in", "Login here",
            "Existing user", "Already registered",
            # Russian
            "Уже есть аккаунт", "Войти", "Уже зарегистрированы",
            # German
            "Bereits ein Konto", "Anmelden", "Schon registriert",
            # French
            "Déjà un compte", "Se connecter", "Déjà inscrit",
            # Spanish
            "¿Ya tienes cuenta", "Iniciar sesión", "¿Ya estás registrado",
            # Italian
            "Hai già un account", "Accedi", "Già registrato",
            # Portuguese
            "Já tem conta", "Entrar", "Já cadastrado",
            # Dutch
            "Heb je al een account", "Inloggen",
            # Polish
            "Masz już konto", "Zaloguj się",
            # Romanian
            "Ai deja cont", "Conectare",
            # Greek
            "Έχετε ήδη λογαριασμό", "Σύνδεση",
            # Czech
            "Máte již účet", "Přihlásit se",
            # Hungarian
            "Van már fiókja", "Bejelentkezés",
            # Swedish
            "Har du redan ett konto", "Logga in",
            # Bulgarian
            "Вече имате акаунт", "Вход",
            # Danish
            "Har du allerede en konto", "Log ind",
            # Finnish
            "Onko sinulla jo tili", "Kirjaudu",
            # Ukrainian
            "Вже є акаунт", "Увійти",
            # Turkish
            "Zaten hesabınız var mı", "Giriş yap",
        ]
    }
    
    # "Continue as [Name]" - Google One Tap button texts
    CONTINUE_AS_TEXTS = [
        'Continue as',      # English
        'Продолжить как',   # Russian
        'Weiter als',       # German
        'Fortfahren als',   # German alt
        'Continuer en tant que',  # French
        'Continuar como',   # Spanish
        'Continua come',    # Italian
        'Continuar como',   # Portuguese
        'Doorgaan als',     # Dutch
        'Kontynuuj jako',   # Polish
        'Continuă ca',      # Romanian
        'Συνέχεια ως',      # Greek
        'Pokračovat jako',  # Czech
        'Folytatás mint',   # Hungarian
        'Fortsätt som',     # Swedish
        'Продължи като',    # Bulgarian
        'Fortsæt som',      # Danish
        'Jatka käyttäjänä', # Finnish
        'Pokračovať ako',   # Slovak
        'Nastavi kao',      # Croatian
        'Tęsti kaip',       # Lithuanian
        'Nadaljuj kot',     # Slovenian
        'Turpināt kā',      # Latvian
        'Jätka kasutajana', # Estonian
        'Продовжити як',    # Ukrainian
        'Olarak devam et',  # Turkish
        'Fortsett som',     # Norwegian
    ]
    
    # OAuth consent/agreement buttons
    OAUTH_CONSENT_TEXTS = [
        # English
        'Agree and Continue', 'Agree & Continue', 'Agree and Join', 
        'Allow', 'Continue', 'Accept', 'Confirm', 'Approve', 'OK', 'Yes',
        'I agree', 'I accept',
        # Russian
        'Согласиться и продолжить', 'Принять и продолжить', 
        'Разрешить', 'Продолжить', 'Принять', 'Подтвердить', 'Согласен',
        # German
        'Zustimmen und fortfahren', 'Akzeptieren und fortfahren',
        'Zulassen', 'Weiter', 'Akzeptieren', 'Bestätigen', 'Einwilligen',
        # French
        'Accepter et continuer', "J'accepte et je continue",
        'Autoriser', 'Continuer', 'Accepter', 'Confirmer',
        # Spanish
        'Aceptar y continuar', 'Acepto y continúo',
        'Permitir', 'Continuar', 'Aceptar', 'Confirmar',
        # Italian
        'Accetta e continua', 'Accetto e continuo',
        'Consenti', 'Continua', 'Accetta', 'Conferma',
        # Portuguese
        'Concordar e continuar', 'Aceitar e continuar',
        'Permitir', 'Continuar', 'Aceitar', 'Confirmar',
        # Dutch
        'Akkoord en doorgaan', 'Accepteren en doorgaan',
        'Toestaan', 'Doorgaan', 'Accepteren', 'Bevestigen',
        # Polish
        'Zgadzam się i kontynuuj', 'Akceptuję i kontynuuj',
        'Zezwól', 'Kontynuuj', 'Akceptuj', 'Potwierdź',
    ]
    
    async def perform_google_auth_on_sites(self, sites: List[str], settings: dict):
        """
        Visit sites and LOGIN using Google OAuth.
        Assumes accounts are already registered on sites.
        """
        if not sites:
            return
        
        self.log("\n🔐 Google Login on sites...")
        
        success_count = 0
        skip_count = 0
        fail_count = 0
        
        for i, site in enumerate(sites, 1):
            if self.should_stop:
                break
            
            self.log(f"\n[{i}/{len(sites)}] {site}")
            
            result = await self._auth_on_single_site(site)
            
            if result == 'success':
                success_count += 1
            elif result == 'already_logged':
                skip_count += 1
            else:
                fail_count += 1
            
            if i < len(sites):
                await HumanBehavior.random_delay(2, 4)
        
        self.log(f"\n🔐 Login complete: ✓{success_count} ⊘{skip_count} ✗{fail_count}")
    
    # ========================================================================
    # GOOGLE SEARCH NAVIGATION
    # ========================================================================
    
    def _extract_search_query(self, url: str) -> tuple:
        """
        Extract search query and domain from URL.
        
        Examples:
        - https://www.canva.com/ → ("canva", "canva.com")
        - https://subdomain.canva.com/ → ("canva", "canva.com")
        - https://my-site.co.uk/ → ("my-site", "my-site.co.uk")
        - https://drive.google.com/ → ("Google Drive", "drive.google.com")
        
        Returns: (search_query, domain_to_match)
        """
        # Special handling for Google services - use full product names
        google_service_queries = {
            'drive.google.com': ('Google Drive', 'drive.google.com'),
            'docs.google.com/document': ('Google Docs', 'docs.google.com'),
            'docs.google.com/spreadsheets': ('Google Sheets', 'docs.google.com'),
            'docs.google.com/presentation': ('Google Slides', 'docs.google.com'),
            'calendar.google.com': ('Google Calendar', 'calendar.google.com'),
            'photos.google.com': ('Google Photos', 'photos.google.com'),
            'maps.google.com': ('Google Maps', 'maps.google.com'),
            'meet.google.com': ('Google Meet', 'meet.google.com'),
            'chat.google.com': ('Google Chat', 'chat.google.com'),
            'mail.google.com': ('Gmail', 'mail.google.com'),
            'youtube.com': ('YouTube', 'youtube.com'),
            'www.youtube.com': ('YouTube', 'youtube.com'),
        }
        
        # Check if URL matches any Google service
        url_lower = url.lower()
        for service_pattern, (query, domain) in google_service_queries.items():
            if service_pattern in url_lower:
                return query, domain
        
        # Standard extraction for other sites
        if tldextract:
            extracted = tldextract.extract(url)
            search_query = extracted.domain
            domain_to_match = f"{extracted.domain}.{extracted.suffix}"
            return search_query, domain_to_match
        else:
            # Fallback without tldextract
            from urllib.parse import urlparse
            parsed = urlparse(url)
            hostname = parsed.netloc or parsed.path
            hostname = hostname.replace('www.', '')
            
            # Simple extraction: take first part before dot
            parts = hostname.split('.')
            if len(parts) >= 2:
                # Handle cases like "co.uk", "com.br"
                if parts[-2] in ['co', 'com', 'org', 'net', 'gov']:
                    search_query = parts[-3] if len(parts) >= 3 else parts[0]
                    domain_to_match = '.'.join(parts[-3:]) if len(parts) >= 3 else hostname
                else:
                    search_query = parts[-2]
                    domain_to_match = '.'.join(parts[-2:])
            else:
                search_query = parts[0]
                domain_to_match = hostname
            
            return search_query, domain_to_match
    
    async def _navigate_via_google_search(self, target_url: str) -> bool:
        """
        Navigate to a site by searching in Google and clicking organic result.
        Uses TWO TABS architecture:
        - Tab 1 (search_tab): Persistent Google search tab
        - Tab 2 (site_tab): Temporary tab for site work
        
        Args:
            target_url: The URL we want to reach (e.g., "https://canva.com/")
            
        Returns:
            True if successfully navigated via search, False if fallback needed
        """
        search_query, domain_to_match = self._extract_search_query(target_url)
        
        if not search_query:
            return False
        
        self.log(f"   🔍 Searching Google for: {search_query}")
        
        try:
            # Initialize search tab if not exists or closed
            if not hasattr(self, '_search_tab') or self._search_tab.is_closed():
                self._search_tab = self.page
                self._search_tab_initialized = False
            
            # Step 1: Setup Google search tab (first time or if needed)
            if not getattr(self, '_search_tab_initialized', False):
                await self._search_tab.goto("https://www.google.com/", wait_until="domcontentloaded", timeout=15000)
                await asyncio.sleep(random.uniform(1, 2))
                await self._handle_google_consent_on_page(self._search_tab)
                self._search_tab_initialized = True
            else:
                # Return to search tab and clear previous search
                await self._search_tab.bring_to_front()
                await asyncio.sleep(random.uniform(0.3, 0.6))
                
                # Clear search input for new query using TRIPLE CLICK + DELETE
                search_input = await self._search_tab.query_selector('input[name="q"], textarea[name="q"]')
                if search_input:
                    # Triple click to select all text
                    await search_input.click(click_count=3)
                    await asyncio.sleep(0.2)
                    # Delete selected text
                    await self._search_tab.keyboard.press("Backspace")
                    await asyncio.sleep(0.2)
            
            # Step 2: Find and focus search input
            search_input = await self._search_tab.query_selector('input[name="q"], textarea[name="q"]')
            if not search_input:
                self.log("   ⚠️ Google search input not found")
                return False
            
            await search_input.click()
            await asyncio.sleep(random.uniform(0.3, 0.6))
            
            # Step 3: Type search query (human-like, 100-300ms between chars)
            for char in search_query:
                await self._search_tab.keyboard.type(char)
                await asyncio.sleep(random.uniform(0.10, 0.30))
            
            await asyncio.sleep(random.uniform(0.5, 1.0))
            
            # Step 4: Press Enter
            await self._search_tab.keyboard.press("Enter")
            
            # Step 5: Wait for results
            try:
                await self._search_tab.wait_for_selector('div#search, div.g', timeout=10000)
            except:
                self.log("   ⚠️ Search results not loaded")
                return False
            
            await asyncio.sleep(random.uniform(1.5, 2.5))
            
            # Step 6: Random scroll (human-like)
            scroll_amount = random.randint(100, 300)
            await self._search_tab.evaluate(f'window.scrollBy(0, {scroll_amount})')
            await asyncio.sleep(random.uniform(0.5, 1.0))
            
            # Step 7: Find organic result (not ad)
            organic_link = await self._find_organic_search_result_on_page(self._search_tab, domain_to_match)
            
            if not organic_link:
                self.log(f"   ⚠️ {domain_to_match} not found in organic results")
                return False
            
            # Step 8: Get href and open in NEW TAB
            href = await organic_link.get_attribute('href')
            if not href:
                self.log("   ⚠️ Could not get link href")
                return False
            
            self.log(f"   ✓ Found {domain_to_match}, opening in new tab...")
            
            # Create new tab for the site
            site_tab = await self.context.new_page()
            
            # Re-minimize window after opening new tab (browsers often restore on new tab)
            if getattr(self, '_should_minimize', False):
                await self.minimize_window()
            
            # Navigate to site in new tab
            try:
                await site_tab.goto(href, wait_until="domcontentloaded", timeout=30000)
            except Exception as nav_err:
                self.log(f"   ⚠️ Site navigation failed: {str(nav_err)[:30]}")
                await site_tab.close()
                return False
            
            await asyncio.sleep(random.uniform(1, 2))
            
            # Verify we landed on the right site
            current_url = site_tab.url.lower()
            if domain_to_match.lower() not in current_url:
                self.log(f"   ⚠️ Wrong site: {current_url[:50]}")
                await site_tab.close()
                return False
            
            # Store site tab reference and switch working page to it
            self._site_tab = site_tab
            self.page = site_tab  # Now all operations work on site tab
            
            self.log(f"   ✓ Navigated via Google search")
            return True
            
        except Exception as e:
            self.log(f"   ⚠️ Google search failed: {str(e)[:40]}")
            return False
    
    async def _close_site_tab_and_return_to_search(self):
        """
        Close the site tab and return to Google search tab.
        Called after finishing work on a site.
        """
        try:
            # Close site tab if exists
            if hasattr(self, '_site_tab') and self._site_tab and not self._site_tab.is_closed():
                await self._site_tab.close()
                self._site_tab = None
            
            # Return to search tab
            if hasattr(self, '_search_tab') and self._search_tab and not self._search_tab.is_closed():
                self.page = self._search_tab
                await self._search_tab.bring_to_front()
                await asyncio.sleep(random.uniform(0.3, 0.6))
                
        except Exception as e:
            logger.debug(f"Close site tab error: {e}")
    
    async def _navigate_direct_in_new_tab(self, url: str) -> bool:
        """
        Navigate directly to URL but in a NEW TAB.
        Used for direct navigation (30% of time) or fallback.
        
        Args:
            url: Target URL
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Initialize search tab if needed (to have a base tab)
            if not hasattr(self, '_search_tab') or self._search_tab.is_closed():
                self._search_tab = self.page
                self._search_tab_initialized = False
            
            # Create new tab for the site
            site_tab = await self.context.new_page()
            
            # Re-minimize window after opening new tab (browsers often restore on new tab)
            if getattr(self, '_should_minimize', False):
                await self.minimize_window()
            
            # Navigate to site
            try:
                await site_tab.goto(url, wait_until="domcontentloaded", timeout=30000)
            except:
                # Retry with shorter timeout
                try:
                    await site_tab.goto(url, wait_until="commit", timeout=15000)
                except Exception as e:
                    self.log(f"   ❌ Navigation failed: {str(e)[:40]}")
                    await site_tab.close()
                    return False
            
            await asyncio.sleep(random.uniform(1, 2))
            
            # Store site tab reference and switch working page to it
            self._site_tab = site_tab
            self.page = site_tab
            
            return True
            
        except Exception as e:
            self.log(f"   ⚠️ Direct navigation failed: {str(e)[:40]}")
            return False
    
    async def _handle_google_consent_on_page(self, page):
        """Handle Google's own cookie consent popup on specified page."""
        try:
            consent_selectors = [
                'button:has-text("Accept all")',
                'button:has-text("Reject all")',
                'button:has-text("I agree")',
                'button:has-text("Alle akzeptieren")',
                'button:has-text("Tout accepter")',
                'button:has-text("Принять все")',
                '#L2AGLb',
                '[aria-label="Accept all"]',
            ]
            
            for selector in consent_selectors:
                try:
                    btn = await page.query_selector(selector)
                    if btn and await btn.is_visible():
                        await btn.click()
                        await asyncio.sleep(0.5)
                        return
                except:
                    continue
        except:
            pass
    
    async def _find_organic_search_result_on_page(self, page, domain_to_match: str):
        """
        Find organic (non-ad) search result matching the domain on specified page.
        """
        try:
            results = await page.query_selector_all('div.g, div[data-sokoban-container], div.MjjYud')
            
            for result in results:
                try:
                    # Check if this is an ad
                    is_ad = await page.evaluate('''(el) => {
                        if (el.closest('[data-text-ad], [data-rw], .uEierd, .commercial-unit')) return true;
                        if (el.querySelector('[data-text-ad], .uEierd')) return true;
                        
                        const adLabels = el.querySelectorAll('span, div');
                        for (const label of adLabels) {
                            const text = label.innerText || '';
                            if (text === 'Ad' || text === 'Ads' || text === 'Sponsored' || 
                                text === 'Реклама' || text === 'Anzeige' || text === 'Annonce') {
                                return true;
                            }
                        }
                        return false;
                    }''', result)
                    
                    if is_ad:
                        continue
                    
                    links = await result.query_selector_all('a[href]')
                    
                    for link in links:
                        href = await link.get_attribute('href') or ''
                        href_lower = href.lower()
                        
                        if any(x in href_lower for x in [
                            'google.com/aclk', 
                            'googleadservices', 
                            'googlesyndication',
                            'webcache.googleusercontent',
                            'translate.google',
                            '/search?'
                        ]):
                            continue
                        
                        if domain_to_match.lower() in href_lower:
                            h3 = await result.query_selector('h3')
                            if h3:
                                return link
                            
                except Exception as e:
                    logger.debug(f"Result check error: {e}")
                    continue
            
            return None
            
        except Exception as e:
            logger.debug(f"Find organic result error: {e}")
            return None
    
    async def _auth_on_single_site(self, url: str) -> str:
        """
        Login on a single site using Google One Tap.
        CLEAN REWRITE - focuses on what actually works.
        
        Returns: 'success', 'already_logged', 'no_onetap', 'failed'
        """
        try:
            # Step 1: Navigate via Google Search (more natural) or direct
            # For Google services - ALWAYS use Google Search (100%)
            is_google_service = any(domain in url.lower() for domain in [
                'drive.google.com', 'docs.google.com', 'calendar.google.com',
                'photos.google.com', 'maps.google.com', 'sheets.google.com',
                'slides.google.com', 'meet.google.com', 'chat.google.com'
            ])
            
            if is_google_service:
                # Google services ALWAYS via search
                use_google_search = True
                self.log("   🔍 Google service → searching via Google")
            else:
                # Use google_search_percent from settings (default 70%)
                google_search_chance = getattr(self, '_google_search_percent', 70)
                use_google_search = random.randint(1, 100) <= google_search_chance
            
            if use_google_search:
                search_success = await self._navigate_via_google_search(url)
                if not search_success:
                    # Fallback to direct navigation in new tab
                    self.log("   Direct navigation fallback...")
                    nav_success = await self._navigate_direct_in_new_tab(url)
                    if not nav_success:
                        return 'failed'
            else:
                # Direct navigation
                self.log("   Opening site directly...")
                nav_success = await self._navigate_direct_in_new_tab(url)
                if not nav_success:
                    return 'failed'
            
            # Step 2: Handle cookie banners and Google promo dialogs
            await self._handle_cookie_banners_safe()
            await asyncio.sleep(1)
            
            # For Google services - dismiss promo dialogs (Got it, etc.)
            if is_google_service:
                await self._dismiss_google_promo_dialogs()
                await asyncio.sleep(0.5)
            await asyncio.sleep(1)
            
            # Step 3: Check if already logged in
            if await self._is_user_logged_in():
                self.log("   ✓ Already logged in")
                return 'already_logged'
            
            # Step 4: Main scan loop (20 seconds)
            self.log("   Scanning for Google One Tap...")
            start_time = time.time()
            max_duration = 20
            click_attempted = False
            
            while (time.time() - start_time) < max_duration:
                # Try to find and click Google iframe
                click_result = await self._find_and_click_onetap_iframe()
                
                if click_result == 'success':
                    self.log("   ✓ Successfully clicked One Tap!")
                    # Wait and verify
                    await asyncio.sleep(2)
                    
                    for _ in range(3):
                        if await self._is_user_logged_in():
                            self.log("   ✓ Login confirmed!")
                            return 'success'
                        await asyncio.sleep(1)
                    
                    return 'success'
                
                elif click_result == 'clicked_not_confirmed':
                    # We clicked but iframe didn't close - try again
                    click_attempted = True
                    await asyncio.sleep(1)
                    continue
                    
                elif click_result == 'not_found':
                    # No iframe yet, keep scanning
                    await asyncio.sleep(1)
                    continue
                
                await asyncio.sleep(1)
            
            if click_attempted:
                self.log("   ⚠️ Clicked but not confirmed")
                return 'success'  # Optimistic
            else:
                # ============================================================
                # FALLBACK: Try Login button → Continue as flow (Pinterest style)
                # ============================================================
                self.log("   No One Tap found, trying Login button flow...")
                login_flow_result = await self._try_login_button_flow()
                
                if login_flow_result == 'success':
                    return 'success'
                elif login_flow_result == 'already_logged':
                    return 'already_logged'
                
                self.log("   No Google One Tap found")
                return 'no_onetap'
            
        except Exception as e:
            self.log(f"   ❌ Error: {str(e)[:60]}")
            return 'failed'

    async def _try_login_button_flow(self) -> str:
        """
        Fallback flow when One Tap is not found:
        1. Find and click Login/Sign in button
        2. Wait for page/modal to load
        3. Look for "Continue as..." or Google Sign-In buttons
        4. Click and handle popups
        
        Returns: 'success', 'already_logged', 'not_found'
        """
        try:
            # ================================================================
            # STEP 1: Find and click Login button
            # ================================================================
            login_texts = [
                # English
                'Log in', 'Login', 'Sign in', 'Sign In', 'Log In',
                # Russian
                'Войти', 'Вход', 'Авторизация',
                # German
                'Anmelden', 'Einloggen',
                # French
                'Connexion', 'Se connecter',
                # Spanish
                'Iniciar sesión', 'Acceder', 'Entrar',
                # Italian
                'Accedi', 'Accesso',
                # Portuguese
                'Entrar', 'Iniciar sessão', 'Fazer login',
                # Dutch
                'Inloggen', 'Aanmelden',
                # Polish
                'Zaloguj się', 'Zaloguj',
                # Turkish
                'Giriş yap', 'Oturum aç',
                # Ukrainian
                'Увійти', 'Вхід',
            ]
            
            login_clicked = False
            
            for text in login_texts:
                try:
                    # Try button first
                    btn = await self.page.query_selector(f'button:has-text("{text}")')
                    if btn and await btn.is_visible():
                        btn_text = await btn.inner_text() or ""
                        # Skip if it's a Google button
                        if 'google' in btn_text.lower():
                            continue
                        self.log(f"   Found Login button: {text}")
                        await btn.click()
                        login_clicked = True
                        break
                    
                    # Try link
                    link = await self.page.query_selector(f'a:has-text("{text}")')
                    if link and await link.is_visible():
                        link_text = await link.inner_text() or ""
                        if 'google' in link_text.lower():
                            continue
                        self.log(f"   Found Login link: {text}")
                        await link.click()
                        login_clicked = True
                        break
                        
                except:
                    continue
            
            # Also try common selectors
            if not login_clicked:
                login_selectors = [
                    '[data-testid*="login"]',
                    '[data-testid*="signin"]',
                    'a[href*="login"]',
                    'a[href*="signin"]',
                    'a[href*="sign-in"]',
                    '[class*="login-btn"]',
                    '[class*="signin-btn"]',
                ]
                
                for selector in login_selectors:
                    try:
                        elem = await self.page.query_selector(selector)
                        if elem and await elem.is_visible():
                            self.log(f"   Found Login via selector")
                            await elem.click()
                            login_clicked = True
                            break
                    except:
                        continue
            
            if not login_clicked:
                return 'not_found'
            
            # ================================================================
            # STEP 2: Wait for login modal/page to load
            # ================================================================
            await asyncio.sleep(2)
            
            # Handle any popups that appeared
            await self._try_close_overlay()
            
            # ================================================================
            # STEP 3: Look for "Continue as..." or Google buttons
            # ================================================================
            continue_as_texts = [
                # English
                'Continue as',
                # Russian  
                'Продолжить как',
                # German
                'Weiter als', 'Fortfahren als',
                # French
                'Continuer en tant que',
                # Spanish
                'Continuar como',
                # Italian
                'Continua come',
                # Dutch
                'Doorgaan als', 'Ga door als',
                # Polish
                'Kontynuuj jako',
                # Czech
                'Pokračovat jako',
                # Ukrainian
                'Продовжити як',
                # Turkish
                'Olarak devam et',
                # Portuguese
                'Continuar como',
                # Swedish
                'Fortsätt som',
                # Norwegian
                'Fortsett som',
                # Danish
                'Fortsæt som',
                # Finnish
                'Jatka nimellä',
            ]
            
            google_button_texts = [
                'Continue with Google', 'Sign in with Google', 'Log in with Google',
                'Продолжить с Google', 'Войти через Google',
                'Mit Google fortfahren', 'Mit Google anmelden',
                'Continuer avec Google', 'Se connecter avec Google',
                'Continuar con Google', 'Iniciar sesión con Google',
            ]
            
            # ================================================================
            # STEP 3a: Look for "Continue as..." elements (Pinterest style)
            # These can be div, button, or any clickable element
            # ================================================================
            for text in continue_as_texts:
                try:
                    # Try multiple element types
                    for tag in ['div', 'button', 'a', 'span', '[role="button"]']:
                        elem = await self.page.query_selector(f'{tag}:has-text("{text}")')
                        if elem and await elem.is_visible():
                            elem_text = await elem.inner_text() or ""
                            # Verify it contains email (Google account indicator)
                            if '@gmail.com' in elem_text.lower() or '@googlemail.com' in elem_text.lower():
                                self.log(f"   ✓ Found: {text} (with email)")
                                await asyncio.sleep(random.uniform(0.3, 0.8))
                                await elem.click()
                                await asyncio.sleep(2)
                                
                                await self._handle_google_popup_after_click()
                                
                                if await self._is_user_logged_in():
                                    self.log("   ✓ Login confirmed!")
                                    return 'success'
                                return 'success'
                except:
                    continue
            
            # ================================================================
            # STEP 3b: Look for elements containing email (fallback)
            # Pinterest shows: "Continue as Hf\nrandyhart750@gmail.com"
            # ================================================================
            try:
                # Find any clickable element with @gmail.com
                email_selectors = [
                    'div:has-text("@gmail.com")',
                    'button:has-text("@gmail.com")',
                    '[role="button"]:has-text("@gmail.com")',
                ]
                
                for selector in email_selectors:
                    try:
                        elements = await self.page.query_selector_all(selector)
                        for elem in elements[:5]:
                            if await elem.is_visible():
                                text = await elem.inner_text() or ""
                                text_lower = text.lower()
                                
                                # Must have Google indicator (Continue as, Google icon context)
                                has_continue = any(x in text_lower for x in ['continue', 'doorgaan', 'fortfahren', 'continuer', 'continuar', 'продолжить'])
                                has_email = '@gmail.com' in text_lower
                                
                                # Skip if it's a form field or label
                                tag_name = await elem.evaluate('el => el.tagName')
                                if tag_name in ['INPUT', 'LABEL', 'TEXTAREA']:
                                    continue
                                
                                if has_email:
                                    box = await elem.bounding_box()
                                    # Should be a reasonable button size
                                    if box and box['width'] > 100 and box['height'] > 30 and box['height'] < 150:
                                        self.log(f"   ✓ Found Google account element")
                                        await asyncio.sleep(random.uniform(0.3, 0.8))
                                        await elem.click()
                                        await asyncio.sleep(2)
                                        
                                        await self._handle_google_popup_after_click()
                                        
                                        if await self._is_user_logged_in():
                                            self.log("   ✓ Login confirmed!")
                                            return 'success'
                                        return 'success'
                    except:
                        continue
            except:
                pass
            
            # ================================================================
            # STEP 3c: Try "Continue with Google" / "Sign in with Google"
            # ================================================================
            for text in google_button_texts:
                try:
                    btn = await self.page.query_selector(f'button:has-text("{text}")')
                    if not btn:
                        btn = await self.page.query_selector(f'div[role="button"]:has-text("{text}")')
                    if not btn:
                        btn = await self.page.query_selector(f'a:has-text("{text}")')
                    
                    if btn and await btn.is_visible():
                        self.log(f"   ✓ Found: {text}")
                        await asyncio.sleep(random.uniform(0.3, 0.8))
                        await btn.click()
                        await asyncio.sleep(2)
                        
                        # Handle popup window or iframe
                        await self._handle_google_popup_after_click()
                        
                        if await self._is_user_logged_in():
                            self.log("   ✓ Login confirmed!")
                            return 'success'
                        return 'success'
                except:
                    continue
            
            # Try Google button by icon/class
            google_selectors = [
                '[data-provider="google"]',
                '[class*="google-sign"]',
                '[class*="google-login"]',
                '[class*="google-btn"]',
                '[class*="btn-google"]',
                'button[class*="google" i]',
                '[aria-label*="Google" i]',
            ]
            
            for selector in google_selectors:
                try:
                    btn = await self.page.query_selector(selector)
                    if btn and await btn.is_visible():
                        self.log(f"   ✓ Found Google button via selector")
                        await btn.click()
                        await asyncio.sleep(2)
                        await self._handle_google_popup_after_click()
                        return 'success'
                except:
                    continue
            
            # ================================================================
            # STEP 4: Check for Google iframe that might have appeared
            # ================================================================
            click_result = await self._find_and_click_onetap_iframe()
            if click_result in ['success', 'clicked_not_confirmed']:
                return 'success'
            
            return 'not_found'
            
        except Exception as e:
            logger.debug(f"Login button flow error: {e}")
            return 'not_found'
    
    async def _handle_google_popup_after_click(self):
        """
        Handle Google popup/iframe that appears after clicking a Google button.
        Checks for: new popup window, iframe, or redirect to Google.
        """
        try:
            # Check for popup window
            try:
                pages = self.context.pages
                for page in pages:
                    if page == self.page:
                        continue
                    page_url = page.url or ""
                    if 'accounts.google.com' in page_url:
                        self.log("   Found Google popup window")
                        await self._handle_account_chooser_in_page(page)
                        return
            except:
                pass
            
            # Check for Google iframe
            for _ in range(3):
                click_result = await self._find_and_click_onetap_iframe()
                if click_result == 'success':
                    return
                await asyncio.sleep(1)
            
            # Check if redirected to Google
            if 'accounts.google.com' in self.page.url:
                self.log("   Redirected to Google, handling...")
                await self._handle_account_chooser_in_page(self.page)
                
        except Exception as e:
            logger.debug(f"Handle popup error: {e}")
    
    async def _handle_account_chooser_in_page(self, page):
        """
        Handle Google Account Chooser on a page (popup or main).
        Click on the account email to select it.
        """
        try:
            await page.wait_for_load_state('domcontentloaded', timeout=10000)
            await asyncio.sleep(1)
            
            # Look for account email
            email_patterns = ['@gmail.com', '@googlemail.com']
            
            for pattern in email_patterns:
                try:
                    elements = await page.query_selector_all(f'text={pattern}')
                    for elem in elements[:5]:
                        if await elem.is_visible():
                            text = await elem.inner_text() or ""
                            text_lower = text.lower()
                            
                            # Skip "use another account"
                            if 'another' in text_lower or 'другой' in text_lower or 'add' in text_lower:
                                continue
                            
                            self.log(f"   Clicking account: {text[:30]}")
                            await elem.click()
                            await asyncio.sleep(2)
                            return
                except:
                    continue
            
            # Try data-email
            try:
                elem = await page.query_selector('[data-email]')
                if elem:
                    self.log("   Clicking [data-email]")
                    await elem.click()
                    return
            except:
                pass
            
            # Try "Continue" button
            continue_texts = ['Continue', 'Next', 'Продолжить', 'Далее', 'Weiter', 'Continuer']
            for text in continue_texts:
                try:
                    btn = await page.query_selector(f'button:has-text("{text}")')
                    if btn and await btn.is_visible():
                        await btn.click()
                        return
                except:
                    continue
                    
        except Exception as e:
            logger.debug(f"Account chooser error: {e}")

    
    async def _handle_cookie_banners_safe(self):
        """Handle cookie banners - comprehensive approach for different types."""
        try:
            # ================================================================
            # SPECIAL: Handle custom checkboxes (like PicMonkey)
            # These are DIVs styled as checkboxes, not real <input> elements
            # ================================================================
            try:
                checkbox_clicked = await self.page.evaluate('''() => {
                    // Method 1: Find real checkbox inputs
                    const inputs = document.querySelectorAll('input[type="checkbox"]');
                    for (const cb of inputs) {
                        if (cb.checked) continue;
                        const parent = cb.closest('div, label, form, section');
                        if (!parent) continue;
                        const text = parent.innerText?.toLowerCase() || '';
                        if (text.includes('consent') || text.includes('cookie') || 
                            text.includes('agree') || text.includes('accept')) {
                            cb.click();
                            return 'input';
                        }
                    }
                    
                    // Method 2: Find custom checkbox DIVs (PicMonkey style)
                    const customCheckboxes = document.querySelectorAll('[class*="checkbox"], [class*="check-box"], [class*="checkBox"]');
                    for (const cb of customCheckboxes) {
                        // Skip if already checked
                        if (cb.classList.toString().includes('checked') || 
                            cb.classList.toString().includes('active') ||
                            cb.getAttribute('aria-checked') === 'true') {
                            continue;
                        }
                        
                        // Check if near consent text
                        const parent = cb.closest('div, form, section') || cb.parentElement;
                        if (!parent) continue;
                        const text = parent.innerText?.toLowerCase() || '';
                        if (text.includes('consent') || text.includes('cookie') || 
                            text.includes('agree') || text.includes('i consent')) {
                            cb.click();
                            return 'custom';
                        }
                    }
                    
                    // Method 3: Find element next to "I consent" text and click it
                    const allElements = document.querySelectorAll('div, span, label');
                    for (const el of allElements) {
                        const text = el.innerText?.toLowerCase() || '';
                        if (text.includes('i consent') || text.includes('я согласен')) {
                            // Find clickable element before this text (checkbox area)
                            const parent = el.closest('div, label');
                            if (parent) {
                                const checkbox = parent.querySelector('[class*="checkbox"], [class*="check"], input[type="checkbox"]');
                                if (checkbox) {
                                    checkbox.click();
                                    return 'near-text';
                                }
                                // Or click the parent itself
                                const rect = parent.getBoundingClientRect();
                                if (rect.width < 500) {  // Reasonable size for checkbox row
                                    parent.click();
                                    return 'parent';
                                }
                            }
                        }
                    }
                    
                    return null;
                }''')
                
                if checkbox_clicked:
                    self.log(f"   Checked consent checkbox ({checkbox_clicked})")
                    await asyncio.sleep(0.5)
            except:
                pass
            
            # ================================================================
            # TYPE 1: Direct accept buttons (most common)
            # ================================================================
            accept_selectors = [
                # ID-based (most reliable)
                '#onetrust-accept-btn-handler',
                '#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll',
                '#CybotCookiebotDialogBodyButtonAccept',
                '#didomi-notice-agree-button',
                '#cookie-accept',
                '#accept-cookies',
                '#acceptCookies',
                '[data-testid="cookie-policy-dialog-accept-button"]',
                
                # Button text patterns
                'button:has-text("Got it")',
                'button:has-text("Accept")',
                'button:has-text("Accept all")',
                'button:has-text("Accept All")',
                'button:has-text("Agree")',
                'button:has-text("I agree")',
                'button:has-text("Allow")',
                'button:has-text("Allow all")',
                'button:has-text("OK")',
                'button:has-text("Continue")',
                'button:has-text("Yes")',
                'button:has-text("Understood")',
                'button:has-text("I understand")',
                
                # Localized
                'button:has-text("Tout accepter")',
                'button:has-text("Accepter")',
                'button:has-text("J\'accepte")',
                'button:has-text("Alle akzeptieren")',
                'button:has-text("Akzeptieren")',
                'button:has-text("Zustimmen")',
                'button:has-text("Verstanden")',
                'button:has-text("Принять")',
                'button:has-text("Принять все")',
                'button:has-text("Согласен")',
                'button:has-text("Понятно")',
                'button:has-text("Aceptar")',
                'button:has-text("Aceptar todo")',
                'button:has-text("Accetto")',
                'button:has-text("Accetta")',
                'button:has-text("Akkoord")',
                'button:has-text("Alle cookies accepteren")',
                'button:has-text("Begrepen")',
                'button:has-text("Zaakceptuj")',
                'button:has-text("Kabul et")',
            ]
            
            for selector in accept_selectors:
                try:
                    btn = await self.page.query_selector(selector)
                    if btn and await btn.is_visible():
                        text = await btn.inner_text() or ""
                        # Skip Google/login buttons
                        if any(x in text.lower() for x in ['google', 'continue as', 'sign in', 'log in', 'facebook', 'apple']):
                            continue
                        self.log(f"   Closing cookie banner: {text[:25]}")
                        await btn.click()
                        await asyncio.sleep(0.5)
                        return
                except:
                    continue
            
            # ================================================================
            # TYPE 3: Links that look like buttons
            # ================================================================
            link_texts = ['Accept', 'Agree', 'OK', 'Got it', 'I agree', 'Accept all', 'Understood']
            for text in link_texts:
                try:
                    link = await self.page.query_selector(f'a:has-text("{text}")')
                    if link and await link.is_visible():
                        link_text = await link.inner_text() or ""
                        if len(link_text) < 30:  # Should be short
                            self.log(f"   Closing cookie banner (link): {link_text[:20]}")
                            await link.click()
                            await asyncio.sleep(0.5)
                            return
                except:
                    continue
            
            # ================================================================
            # TYPE 4: Close button (X) on cookie banners
            # ================================================================
            close_selectors = [
                '[class*="cookie"] button[aria-label*="close" i]',
                '[class*="cookie"] [class*="close"]',
                '[class*="consent"] button[aria-label*="close" i]',
                '[class*="banner"] button[aria-label*="close" i]',
                '[id*="cookie"] button:has-text("×")',
                '[id*="cookie"] button:has-text("✕")',
            ]
            
            for selector in close_selectors:
                try:
                    btn = await self.page.query_selector(selector)
                    if btn and await btn.is_visible():
                        box = await btn.bounding_box()
                        if box and box['width'] < 60:  # Close button should be small
                            self.log("   Closing cookie banner (X)")
                            await btn.click()
                            await asyncio.sleep(0.5)
                            return
                except:
                    continue
                    
        except Exception as e:
            logger.debug(f"Cookie banner error: {e}")
    
    async def _is_user_logged_in(self) -> bool:
        """
        Simple login check using scoring system.
        +3: logout button, email visible
        +2: avatar
        -3: login button visible
        Returns True if score >= 3
        """
        score = 0
        
        try:
            # Check for Logout button (+3)
            logout_keywords = ['logout', 'log out', 'sign out', 'выйти', 'abmelden', 'déconnexion']
            page_text = await self.page.inner_text('body') or ""
            page_text_lower = page_text.lower()
            
            for keyword in logout_keywords:
                if keyword in page_text_lower:
                    score += 3
                    break
            
            # Check for Login button (-3)
            login_keywords = ['sign in', 'log in', 'login', 'войти', 'anmelden', 'connexion']
            for keyword in login_keywords:
                try:
                    elem = await self.page.query_selector(f'header a:has-text("{keyword}"), nav a:has-text("{keyword}"), header button:has-text("{keyword}")')
                    if elem and await elem.is_visible():
                        score -= 3
                        break
                except:
                    continue
            
            # Check for avatar (+2)
            avatar_selectors = ['img[class*="avatar" i]', 'img[alt*="profile" i]', '[class*="user-avatar" i]']
            for sel in avatar_selectors:
                try:
                    elem = await self.page.query_selector(sel)
                    if elem and await elem.is_visible():
                        box = await elem.bounding_box()
                        if box and box['y'] < 150:  # In header area
                            score += 2
                            break
                except:
                    continue
            
        except Exception as e:
            logger.debug(f"Login check error: {e}")
        
        return score >= 3
    
    async def _find_and_click_onetap_iframe(self) -> str:
        """
        Find Google One Tap iframe and click the button inside.
        Uses CDP (Chrome DevTools Protocol) for real clicks.
        
        Returns: 
        - 'success': Click worked, iframe closed/changed
        - 'clicked_not_confirmed': Click sent but iframe still there
        - 'not_found': No iframe found
        - 'error': Exception occurred
        """
        try:
            # Get viewport dimensions
            viewport = await self.page.evaluate('() => ({ width: window.innerWidth, height: window.innerHeight })')
            viewport_height = viewport.get('height', 900)
            
            # Scroll to top first to ensure correct coordinates
            await self.page.evaluate('window.scrollTo(0, 0)')
            await asyncio.sleep(0.2)
            
            # Find Google iframe
            iframes = await self.page.query_selector_all('iframe')
            google_iframe = None
            box = None
            
            for iframe in iframes:
                try:
                    src = await iframe.get_attribute('src') or ""
                    
                    # Check if Google One Tap iframe
                    if not any(x in src.lower() for x in ['accounts.google.com/gsi', 'google.com/gsi']):
                        continue
                    
                    # Must be visible
                    if not await iframe.is_visible():
                        continue
                    
                    box = await iframe.bounding_box()
                    if not box:
                        continue
                    
                    # Skip small "Sign in with Google" buttons (< 80px height)
                    # We want the One Tap popup (150-400px height)
                    if box['height'] < 80:
                        continue
                    
                    # ================================================================
                    # CRITICAL: Skip iframes outside viewport (Y > viewport height)
                    # These are embedded at bottom of page, not real One Tap popups
                    # ================================================================
                    if box['y'] > viewport_height + 100:
                        logger.debug(f"Skipping iframe at Y={box['y']} (outside viewport {viewport_height})")
                        continue
                    
                    # Also skip iframes with X = 0 that are very tall (embedded widgets)
                    if box['x'] == 0 and box['height'] > 300:
                        logger.debug(f"Skipping embedded widget iframe at x=0")
                        continue
                    
                    google_iframe = iframe
                    self.log(f"   ✓ Found One Tap: {int(box['width'])}x{int(box['height'])} at ({int(box['x'])},{int(box['y'])})")
                    break
                    
                except Exception as e:
                    logger.debug(f"Iframe check error: {e}")
                    continue
            
            if not google_iframe or not box:
                return 'not_found'
            
            # ================================================================
            # CHECK FOR OVERLAPPING ELEMENTS (cookie banners, modals)
            # ================================================================
            overlay_closed = await self._close_overlay_blocking_iframe(box)
            if overlay_closed:
                self.log("   Closed overlay blocking One Tap")
                await asyncio.sleep(0.5)
                # Refresh bounding box after closing overlay
                box = await google_iframe.bounding_box()
                if not box:
                    return 'not_found'
            
            # Human-like delay
            await asyncio.sleep(random.uniform(0.3, 0.8))
            
            # Store original state to detect changes
            original_height = box['height']
            original_y = box['y']
            
            # ================================================================
            # CDP CLICK with multiple attempts
            # ================================================================
            try:
                cdp = await self.page.context.new_cdp_session(self.page)
            except Exception:
                self.log(f"   CDP session failed, using fallback")
                cdp = None
            
            # Calculate click positions (accounting for viewport)
            click_targets = [
                # Center - most common button location
                (box['x'] + box['width'] / 2, box['y'] + box['height'] / 2, "center"),
                # Lower area - "Continue as" button
                (box['x'] + box['width'] / 2, box['y'] + box['height'] - 40, "button"),
                # Upper area - account email/name row
                (box['x'] + box['width'] / 2, box['y'] + 55, "account"),
            ]
            
            click_success = False
            
            for x, y, target_name in click_targets:
                # Before each click, verify nothing is blocking
                is_blocked = await self._is_point_blocked(int(x), int(y), google_iframe)
                if is_blocked:
                    self.log(f"   Point ({int(x)},{int(y)}) blocked, trying to clear...")
                    await self._close_overlay_at_point(int(x), int(y))
                    await asyncio.sleep(0.3)
                
                try:
                    self.log(f"   Click {target_name}: ({int(x)}, {int(y)})")
                    
                    if cdp:
                        # CDP click - works for cross-origin
                        await cdp.send('Input.dispatchMouseEvent', {
                            'type': 'mousePressed',
                            'x': int(x),
                            'y': int(y),
                            'button': 'left',
                            'clickCount': 1
                        })
                        await asyncio.sleep(0.03)
                        await cdp.send('Input.dispatchMouseEvent', {
                            'type': 'mouseReleased',
                            'x': int(x),
                            'y': int(y),
                            'button': 'left',
                            'clickCount': 1
                        })
                    else:
                        # Fallback to Playwright
                        await self.page.mouse.click(int(x), int(y))
                    
                    await asyncio.sleep(0.4)
                    
                    # Check if iframe changed or disappeared
                    try:
                        still_visible = await google_iframe.is_visible()
                        if not still_visible:
                            self.log(f"   ✓ Iframe closed!")
                            click_success = True
                            break
                        
                        new_box = await google_iframe.bounding_box()
                        if new_box:
                            # Check for significant changes
                            height_changed = abs(new_box['height'] - original_height) > 30
                            position_changed = abs(new_box['y'] - original_y) > 30
                            
                            if height_changed or position_changed:
                                self.log(f"   ✓ Iframe changed!")
                                click_success = True
                                break
                    except:
                        # Element gone = success
                        click_success = True
                        break
                    
                except Exception as click_err:
                    logger.debug(f"Click error at {target_name}: {click_err}")
                    continue
            
            if cdp:
                try:
                    await cdp.detach()
                except:
                    pass
            
            if click_success:
                return 'success'
            else:
                # We found and clicked, but iframe didn't change
                return 'clicked_not_confirmed'
            
        except Exception as e:
            logger.debug(f"Find onetap error: {e}")
            return 'error'
    
    async def _close_overlay_blocking_iframe(self, iframe_box: dict) -> bool:
        """
        Check if there's an overlay (cookie banner, modal) blocking the iframe.
        If found, try to close it.
        
        Returns True if an overlay was closed.
        """
        try:
            # Calculate center point of iframe
            center_x = int(iframe_box['x'] + iframe_box['width'] / 2)
            center_y = int(iframe_box['y'] + iframe_box['height'] / 2)
            
            # Use JavaScript to check what element is at that point
            element_at_point = await self.page.evaluate(f'''() => {{
                const el = document.elementFromPoint({center_x}, {center_y});
                if (!el) return null;
                
                // Check if it's an iframe (expected)
                if (el.tagName === 'IFRAME') return null;
                
                // Check if it's inside an iframe container (expected)
                if (el.closest('iframe')) return null;
                
                // Something else is blocking - return info about it
                return {{
                    tag: el.tagName,
                    className: el.className || '',
                    id: el.id || '',
                    text: el.innerText?.substring(0, 100) || ''
                }};
            }}''')
            
            if not element_at_point:
                return False
            
            self.log(f"   ⚠️ Overlay detected: {element_at_point.get('tag', 'unknown')}")
            
            # Try to close the overlay
            # Strategy 1: Find and click accept/close button in the blocking element
            close_clicked = await self._try_close_overlay()
            
            return close_clicked
            
        except Exception as e:
            logger.debug(f"Overlay check error: {e}")
            return False
    
    async def _is_point_blocked(self, x: int, y: int, expected_iframe) -> bool:
        """Check if a specific point is blocked by another element."""
        try:
            element_info = await self.page.evaluate(f'''() => {{
                const el = document.elementFromPoint({x}, {y});
                if (!el) return {{ blocked: false }};
                if (el.tagName === 'IFRAME') return {{ blocked: false }};
                return {{ 
                    blocked: true, 
                    tag: el.tagName,
                    className: el.className || ''
                }};
            }}''')
            
            return element_info.get('blocked', False)
            
        except:
            return False
    
    async def _close_overlay_at_point(self, x: int, y: int):
        """Try to close whatever overlay is at the given point."""
        try:
            # Find the blocking element and its container
            await self.page.evaluate(f'''() => {{
                const el = document.elementFromPoint({x}, {y});
                if (!el) return;
                
                // Find the modal/overlay container
                const modal = el.closest('[role="dialog"], [class*="modal"], [class*="cookie"], [class*="consent"], [class*="overlay"], [class*="banner"]');
                if (!modal) return;
                
                // Try to find and click a close/accept button
                const buttons = modal.querySelectorAll('button, [role="button"], a');
                for (const btn of buttons) {{
                    const text = btn.innerText?.toLowerCase() || '';
                    const label = btn.getAttribute('aria-label')?.toLowerCase() || '';
                    
                    // Accept/close patterns
                    if (text.includes('accept') || text.includes('agree') || text.includes('reject') ||
                        text.includes('save') || text.includes('ok') || text.includes('close') ||
                        text.includes('×') || text.includes('✕') ||
                        text.includes('принять') || text.includes('согласен') ||
                        label.includes('close') || label.includes('dismiss')) {{
                        btn.click();
                        return;
                    }}
                }}
            }}''')
            
            await asyncio.sleep(0.3)
            
        except Exception as e:
            logger.debug(f"Close overlay error: {e}")
    
    async def _try_close_overlay(self) -> bool:
        """Try various methods to close any visible overlay/modal."""
        try:
            # Method 1: Common cookie consent buttons (prioritize accept/reject all)
            consent_selectors = [
                # ID-based selectors (most reliable)
                '#onetrust-accept-btn-handler',
                '#onetrust-reject-all-handler', 
                '#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll',
                '#CybotCookiebotDialogBodyButtonAccept',
                '[data-testid="cookie-policy-dialog-accept-button"]',
                '#didomi-notice-agree-button',
                '.trustarc-agree-btn',
                
                # Class-based
                '[class*="cookie"] button[class*="accept"]',
                '[class*="cookie"] button[class*="agree"]',
                '[class*="consent"] button[class*="accept"]',
                '[class*="consent"] button[class*="agree"]',
                
                # Text-based (will be handled below)
            ]
            
            for selector in consent_selectors:
                try:
                    btn = await self.page.query_selector(selector)
                    if btn and await btn.is_visible():
                        self.log(f"   Closing overlay via selector")
                        await btn.click()
                        await asyncio.sleep(0.5)
                        return True
                except:
                    continue
            
            # Method 2: Find buttons by text
            close_texts = [
                'Accept all', 'Accept', 'Agree', 'Allow all', 'Allow',
                'Reject all', 'Reject', 'Save preferences', 'Save',
                'OK', 'Got it', 'Close', 'Dismiss',
                'Tout accepter', 'Accepter', 'Alle akzeptieren', 'Akzeptieren',
                'Принять', 'Принять все', 'Отклонить все',
            ]
            
            for text in close_texts:
                try:
                    btn = await self.page.query_selector(f'button:has-text("{text}")')
                    if btn and await btn.is_visible():
                        # Make sure it's not the Google button
                        btn_text = await btn.inner_text() or ""
                        if 'google' not in btn_text.lower() and 'continue as' not in btn_text.lower():
                            self.log(f"   Closing overlay: {text}")
                            await btn.click()
                            await asyncio.sleep(0.5)
                            return True
                except:
                    continue
            
            # Method 3: X/close icon buttons
            close_icon_selectors = [
                'button[aria-label*="close" i]',
                'button[aria-label*="dismiss" i]',
                '[class*="close-button"]',
                '[class*="closeButton"]',
                'button:has-text("×")',
                'button:has-text("✕")',
            ]
            
            for selector in close_icon_selectors:
                try:
                    btn = await self.page.query_selector(selector)
                    if btn and await btn.is_visible():
                        box = await btn.bounding_box()
                        # Close buttons are usually small
                        if box and box['width'] < 60 and box['height'] < 60:
                            self.log(f"   Closing overlay via X button")
                            await btn.click()
                            await asyncio.sleep(0.5)
                            return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.debug(f"Try close overlay error: {e}")
            return False
    
    async def _close_blocking_overlays(self):
        """Close any popups/modals that might block the iframe."""
        try:
            # Newsletter/promo popup close buttons
            close_selectors = [
                'button[aria-label*="close" i]',
                'button[aria-label*="dismiss" i]',
                '[class*="modal"] [class*="close" i]',
                '[class*="popup"] [class*="close" i]',
                '[class*="overlay"] button',
            ]
            
            for selector in close_selectors:
                try:
                    elem = await self.page.query_selector(selector)
                    if elem and await elem.is_visible():
                        text = await elem.inner_text() or ""
                        # Don't close Google-related elements
                        if 'google' not in text.lower():
                            box = await elem.bounding_box()
                            if box and box['width'] < 80:  # Small close button
                                await elem.click()
                                await asyncio.sleep(0.3)
                                return
                except:
                    continue
                    
        except Exception as e:
            logger.debug(f"Close overlay error: {e}")
    
    
    async def _handle_cookie_banners_only(self):
        """
        Handle cookie banners - PRIORITY: Accept cookies first, close if no accept button.
        Supports all EU languages.
        """
        try:
            # =================================================================
            # STEP 1: Try to ACCEPT cookies (preferred - stops banner from reappearing)
            # =================================================================
            
            # All EU languages + common variations
            accept_texts = [
                # English
                'Accept all', 'Accept all cookies', 'Accept cookies', 'Accept',
                'Allow all', 'Allow all cookies', 'Allow cookies', 'Allow',
                'I agree', 'Agree', 'Agree to all', 'Agree and continue',
                'Got it', 'OK', 'Okay', 'Yes', 'Continue',
                'Save my preferences', 'Save preferences', 'Save settings',
                'Confirm', 'Confirm all', 'Confirm choices', 'Confirm my choices',
                
                # German (Deutsch)
                'Alle akzeptieren', 'Akzeptieren', 'Alle Cookies akzeptieren',
                'Zustimmen', 'Allen zustimmen', 'Ich stimme zu',
                'Alle erlauben', 'Erlauben', 'Einverstanden',
                'Einstellungen speichern', 'Speichern',
                
                # French (Français)
                'Tout accepter', 'Accepter tout', 'Accepter',
                'Accepter tous les cookies', 'Autoriser tout', 'Autoriser',
                "J'accepte", 'Je suis d\'accord', 'Continuer',
                'Enregistrer mes préférences', 'Enregistrer',
                
                # Spanish (Español)
                'Aceptar todo', 'Aceptar todas', 'Aceptar',
                'Aceptar todas las cookies', 'Permitir todo', 'Permitir',
                'Estoy de acuerdo', 'De acuerdo', 'Continuar',
                'Guardar preferencias', 'Guardar',
                
                # Italian (Italiano)
                'Accetta tutto', 'Accetta tutti', 'Accetta',
                'Accetta tutti i cookie', 'Accetto', 'Consenti tutto',
                'Sono d\'accordo', 'Va bene', 'Continua',
                'Salva le preferenze', 'Salva',
                
                # Portuguese (Português)
                'Aceitar tudo', 'Aceitar todos', 'Aceitar',
                'Aceitar todos os cookies', 'Permitir tudo', 'Permitir',
                'Concordo', 'Concordar', 'Continuar',
                'Guardar preferências', 'Guardar',
                
                # Dutch (Nederlands)
                'Alles accepteren', 'Accepteren', 'Alle cookies accepteren',
                'Alles toestaan', 'Toestaan', 'Akkoord', 'Ik ga akkoord',
                'Voorkeuren opslaan', 'Opslaan',
                
                # Polish (Polski)
                'Zaakceptuj wszystkie', 'Zaakceptuj wszystko', 'Akceptuję',
                'Akceptuj wszystkie pliki cookie', 'Zgadzam się',
                'Zezwól na wszystkie', 'Zezwól', 'OK', 'Kontynuuj',
                'Zapisz preferencje', 'Zapisz',
                
                # Romanian (Română)
                'Acceptă tot', 'Acceptă toate', 'Accept',
                'Sunt de acord', 'De acord', 'Continuă',
                'Salvează preferințele', 'Salvează',
                
                # Czech (Čeština)
                'Přijmout vše', 'Přijmout všechny', 'Přijmout',
                'Souhlasím', 'Souhlasím se vším', 'Povolit vše',
                'Uložit předvolby', 'Uložit',
                
                # Hungarian (Magyar)
                'Összes elfogadása', 'Elfogadom', 'Elfogadás',
                'Mindet engedélyez', 'Egyetértek', 'Rendben',
                'Beállítások mentése', 'Mentés',
                
                # Swedish (Svenska)
                'Acceptera alla', 'Acceptera', 'Godkänn alla',
                'Jag godkänner', 'Tillåt alla', 'OK', 'Fortsätt',
                'Spara inställningar', 'Spara',
                
                # Danish (Dansk)
                'Accepter alle', 'Accepter', 'Tillad alle',
                'Jeg accepterer', 'OK', 'Fortsæt',
                'Gem indstillinger', 'Gem',
                
                # Finnish (Suomi)
                'Hyväksy kaikki', 'Hyväksy', 'Salli kaikki',
                'Hyväksyn', 'OK', 'Jatka',
                'Tallenna asetukset', 'Tallenna',
                
                # Greek (Ελληνικά)
                'Αποδοχή όλων', 'Αποδοχή', 'Συμφωνώ',
                'Επιτρέπονται όλα', 'OK', 'Συνέχεια',
                'Αποθήκευση', 'Αποθήκευση προτιμήσεων',
                
                # Bulgarian (Български)
                'Приемам всички', 'Приемам', 'Съгласен съм',
                'Разреши всички', 'OK', 'Продължи',
                'Запази настройките', 'Запази',
                
                # Slovak (Slovenčina)
                'Prijať všetky', 'Prijať', 'Súhlasím',
                'Povoliť všetky', 'OK', 'Pokračovať',
                'Uložiť nastavenia', 'Uložiť',
                
                # Slovenian (Slovenščina)
                'Sprejmi vse', 'Sprejmi', 'Strinjam se',
                'Dovoli vse', 'V redu', 'Nadaljuj',
                'Shrani nastavitve', 'Shrani',
                
                # Croatian (Hrvatski)
                'Prihvati sve', 'Prihvati', 'Slažem se',
                'Dopusti sve', 'U redu', 'Nastavi',
                'Spremi postavke', 'Spremi',
                
                # Lithuanian (Lietuvių)
                'Priimti visus', 'Priimti', 'Sutinku',
                'Leisti visus', 'Gerai', 'Tęsti',
                'Išsaugoti nustatymus', 'Išsaugoti',
                
                # Latvian (Latviešu)
                'Pieņemt visus', 'Pieņemt', 'Piekrītu',
                'Atļaut visus', 'Labi', 'Turpināt',
                'Saglabāt iestatījumus', 'Saglabāt',
                
                # Estonian (Eesti)
                'Nõustu kõigiga', 'Nõustun', 'Luba kõik',
                'OK', 'Jätka', 'Salvesta seaded', 'Salvesta',
                
                # Russian (for non-EU but common)
                'Принять все', 'Принять', 'Согласен', 'Согласиться',
                'Разрешить все', 'Хорошо', 'ОК', 'Продолжить',
                'Сохранить настройки', 'Сохранить',
                
                # Ukrainian
                'Прийняти всі', 'Прийняти', 'Погоджуюсь',
                'Дозволити всі', 'Добре', 'Продовжити',
                'Зберегти налаштування', 'Зберегти',
            ]
            
            for text in accept_texts:
                try:
                    # Try button first
                    btn = await self.page.query_selector(f'button:has-text("{text}")')
                    if btn and await btn.is_visible():
                        btn_text = await btn.inner_text() or ""
                        # Skip Google buttons
                        if 'google' not in btn_text.lower() and 'continue as' not in btn_text.lower():
                            self.log(f"   Closing cookie banner: {text}")
                            await btn.click()
                            await asyncio.sleep(0.5)
                            return
                    
                    # Try link or div button
                    elem = await self.page.query_selector(f'a:has-text("{text}"), div[role="button"]:has-text("{text}"), span[role="button"]:has-text("{text}")')
                    if elem and await elem.is_visible():
                        elem_text = await elem.inner_text() or ""
                        if 'google' not in elem_text.lower() and 'continue as' not in elem_text.lower():
                            self.log(f"   Closing cookie banner: {text}")
                            await elem.click()
                            await asyncio.sleep(0.5)
                            return
                except:
                    continue
            
            # === Try common ID/class selectors for accept buttons ===
            accept_selectors = [
                '#onetrust-accept-btn-handler',
                '#accept-cookies', '#acceptCookies', '#accept_cookies',
                '#cookie-accept', '#cookieAccept', '#cookie_accept',
                '#gdpr-accept', '#gdprAccept',
                '#consent-accept', '#consentAccept',
                '#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll',
                '[data-testid="cookie-accept"]',
                '[data-testid="accept-cookies"]',
                '[data-action="accept"]',
                '.accept-cookies', '.acceptCookies',
                '.cookie-accept', '.cookieAccept',
                '.consent-accept', '.consentAccept',
                '[class*="accept"][class*="cookie" i]',
                '[class*="accept"][class*="all" i]',
                '[id*="accept"][id*="cookie" i]',
            ]
            
            for selector in accept_selectors:
                try:
                    elem = await self.page.query_selector(selector)
                    if elem and await elem.is_visible():
                        self.log(f"   Closing cookie banner via selector")
                        await elem.click()
                        await asyncio.sleep(0.5)
                        return
                except:
                    continue
            
            # =================================================================
            # STEP 2: No accept button found - try to CLOSE the banner
            # =================================================================
            
            close_selectors = [
                'button[aria-label*="close" i]',
                'button[aria-label*="dismiss" i]',
                'button[aria-label*="schließen" i]',
                'button[aria-label*="fermer" i]',
                'button[aria-label*="cerrar" i]',
                'button[aria-label*="chiudi" i]',
                'button[aria-label*="закрыть" i]',
                '[aria-label="Close"]',
                '[aria-label="Dismiss"]',
                '[aria-label="×"]',
                '[class*="close-button" i]',
                '[class*="closeButton" i]',
                '[class*="dismiss" i]',
                '[data-testid*="close"]',
                '[data-testid*="dismiss"]',
                '.cookie-close', '.cookieClose',
                '#cookie-close', '#cookieClose',
            ]
            
            for selector in close_selectors:
                try:
                    elems = await self.page.query_selector_all(selector)
                    for elem in elems[:5]:
                        try:
                            if await elem.is_visible():
                                box = await elem.bounding_box()
                                # Close buttons are usually small (under 60px)
                                if box and box['width'] < 70 and box['height'] < 70:
                                    self.log(f"   Closing cookie banner via close button")
                                    await elem.click()
                                    await asyncio.sleep(0.5)
                                    return
                        except:
                            continue
                except:
                    continue
            
            # === Last resort: find any X button in cookie/consent dialogs ===
            try:
                # Find modal/dialog containers
                containers = await self.page.query_selector_all('[class*="cookie" i], [class*="consent" i], [class*="gdpr" i], [id*="cookie" i], [id*="consent" i]')
                for container in containers[:3]:
                    try:
                        # Find close button inside
                        close_btn = await container.query_selector('button, [role="button"]')
                        if close_btn:
                            text = await close_btn.inner_text() or ""
                            # Check if it's an X or close icon (short text or empty)
                            if len(text.strip()) <= 2:
                                self.log(f"   Closing cookie banner via X button")
                                await close_btn.click()
                                await asyncio.sleep(0.5)
                                return
                    except:
                        continue
            except:
                pass
                    
        except Exception as e:
            logger.debug(f"Cookie banner error: {e}")
    
    async def _scan_for_google_auth(self, max_seconds: int = 10) -> bool:
        """
        Dedicated scan for Google One Tap.
        Uses: coordinates, keyboard, CDP, frames.
        """
        start_time = time.time()
        attempts = 0
        
        # Get viewport size
        viewport = self.page.viewport_size or {'width': 1920, 'height': 1080}
        vw = viewport['width']
        vh = viewport['height']
        
        self.log(f"   Viewport: {vw}x{vh}")
        
        # ============================================================
        # DIAGNOSTIC: Check if FedCM is disabled (Google iframe should exist)
        # ============================================================
        try:
            all_frames = self.page.frames
            self.log(f"   Total frames: {len(all_frames)}")
            
            google_frames_found = []
            for i, frame in enumerate(all_frames):
                frame_url = frame.url or "(empty)"
                # Log ALL frames for debugging
                self.log(f"   Frame {i}: {frame_url[:100]}")
                
                if 'google' in frame_url.lower() or 'gsi' in frame_url.lower() or 'accounts' in frame_url.lower():
                    google_frames_found.append(frame_url)
            
            if google_frames_found:
                self.log(f"   ✓ FedCM DISABLED - Found {len(google_frames_found)} Google iframe(s)!")
            else:
                self.log(f"   ⚠️ No Google iframes found - FedCM might still be active")
            
            # Also check iframes via querySelectorAll
            iframes = await self.page.query_selector_all('iframe')
            self.log(f"   Total <iframe> elements: {len(iframes)}")
            for iframe in iframes:
                try:
                    src = await iframe.get_attribute('src') or ""
                    if src and ('google' in src.lower() or 'gsi' in src.lower()):
                        self.log(f"   ✓ Google iframe src: {src[:80]}")
                except:
                    pass
        except Exception as e:
            self.log(f"   Frame check error: {e}")
        
        while (time.time() - start_time) < max_seconds:
            attempts += 1
            
            # ============================================================
            # METHOD 1: KEYBOARD NAVIGATION - Tab through and Enter
            # ============================================================
            if attempts == 2:
                try:
                    self.log("   Trying keyboard navigation...")
                    # Press Tab multiple times to reach the button
                    for _ in range(5):
                        await self.page.keyboard.press('Tab')
                        await asyncio.sleep(0.1)
                    # Press Enter to click
                    await self.page.keyboard.press('Enter')
                    await asyncio.sleep(0.5)
                    self.log("   Pressed Tab+Enter")
                except Exception as e:
                    logger.debug(f"Keyboard error: {e}")
            
            # ============================================================
            # METHOD 2: COORDINATE CLICKS - RIGHT-TOP side of screen
            # Google One Tap appears in TOP-RIGHT corner
            # ============================================================
            if attempts in [1, 3, 5]:
                try:
                    # Google One Tap appears TOP-RIGHT area
                    # Button "Continue as X" is at bottom of popup (~200px height popup)
                    click_positions = [
                        # Right-top area - relative to viewport
                        (int(vw - 150), 350),   # Right side, button area
                        (int(vw - 200), 350),
                        (int(vw - 250), 350),
                        (int(vw - 150), 300),
                        (int(vw - 200), 300),
                        (int(vw - 150), 400),
                        # Percentage-based positions
                        (int(vw * 0.85), int(vh * 0.35)),  # 85% from left, 35% from top
                        (int(vw * 0.80), int(vh * 0.35)),
                        (int(vw * 0.90), int(vh * 0.35)),
                        (int(vw * 0.85), int(vh * 0.30)),
                        (int(vw * 0.85), int(vh * 0.40)),
                    ]
                    
                    self.log(f"   Clicking coordinates (attempt {attempts})...")
                    for x, y in click_positions:
                        if x > vw or y > vh or x < 0 or y < 0:
                            continue
                        try:
                            await self.page.mouse.click(x, y)
                            await asyncio.sleep(0.2)
                        except:
                            pass
                except Exception as e:
                    logger.debug(f"Coordinate click error: {e}")
            
            # ============================================================
            # METHOD 3: CDP - Chrome DevTools Protocol
            # ============================================================
            if attempts == 4 and self.cdp:
                try:
                    self.log("   Trying CDP...")
                    # Get frame tree
                    result = await self.cdp.send('Page.getFrameTree')
                    if result:
                        await self._log_cdp_frames(result.get('frameTree', {}))
                    
                    # Try to get all targets
                    targets = await self.cdp.send('Target.getTargets')
                    if targets:
                        for target in targets.get('targetInfos', []):
                            url = target.get('url', '')
                            if 'google' in url.lower() or 'gsi' in url.lower():
                                self.log(f"   CDP target: {url[:60]}")
                except Exception as e:
                    logger.debug(f"CDP error: {e}")
            
            # ============================================================
            # METHOD 4: Search frames for buttons
            # ============================================================
            try:
                for frame in self.page.frames:
                    if frame == self.page.main_frame:
                        continue
                    
                    # Try to find and click button
                    try:
                        buttons = await frame.query_selector_all('button')
                        for btn in buttons:
                            try:
                                text = await btn.inner_text() or ""
                                if 'continue' in text.lower():
                                    box = await btn.bounding_box()
                                    if box:
                                        self.log(f"   ✓ Found button: '{text}' at ({int(box['x'])},{int(box['y'])})")
                                        await btn.click()
                                        return True
                            except:
                                continue
                    except:
                        pass
            except:
                pass
            
            # ============================================================
            # METHOD 5: Find iframes and click inside them
            # ============================================================
            try:
                iframes = await self.page.query_selector_all('iframe')
                for iframe in iframes:
                    try:
                        src = await iframe.get_attribute('src') or ""
                        
                        if 'google' in src.lower() or 'gsi' in src.lower():
                            box = await iframe.bounding_box()
                            if box:
                                # Click at bottom center of iframe (where button is)
                                btn_x = int(box['x'] + box['width'] / 2)
                                btn_y = int(box['y'] + box['height'] - 50)  # 50px from bottom
                                
                                self.log(f"   Found Google iframe, clicking at ({btn_x},{btn_y})")
                                await self.page.mouse.click(btn_x, btn_y)
                                await asyncio.sleep(0.3)
                                return True
                    except:
                        continue
            except:
                pass
            
            # ============================================================
            # METHOD 6: Direct text/element search
            # ============================================================
            try:
                # Try to find "Continue as" text
                elem = await self.page.query_selector('text=Continue as')
                if elem:
                    box = await elem.bounding_box()
                    if box:
                        self.log(f"   ✓ Found 'Continue as' at ({int(box['x'])},{int(box['y'])})")
                        await elem.click()
                        return True
            except:
                pass
            
            # ============================================================
            # METHOD 7: JavaScript click in all frames
            # ============================================================
            if attempts == 6:
                try:
                    result = await self.page.evaluate('''
                        () => {
                            // Check main document
                            const buttons = document.querySelectorAll('button');
                            for (const btn of buttons) {
                                if (btn.innerText && btn.innerText.toLowerCase().includes('continue')) {
                                    btn.click();
                                    return 'clicked: ' + btn.innerText;
                                }
                            }
                            
                            // Check iframes
                            const iframes = document.querySelectorAll('iframe');
                            for (const iframe of iframes) {
                                try {
                                    const doc = iframe.contentDocument || iframe.contentWindow.document;
                                    const btns = doc.querySelectorAll('button');
                                    for (const btn of btns) {
                                        if (btn.innerText && btn.innerText.toLowerCase().includes('continue')) {
                                            btn.click();
                                            return 'iframe clicked: ' + btn.innerText;
                                        }
                                    }
                                } catch(e) {}
                            }
                            return 'not found';
                        }
                    ''')
                    if result and 'clicked' in result:
                        self.log(f"   ✓ JS {result}")
                        return True
                except:
                    pass
            
            # Log progress
            if attempts % 4 == 0:
                elapsed = int(time.time() - start_time)
                self.log(f"   Scanning... ({elapsed}s)")
            
            await asyncio.sleep(0.4)
        
        self.log("   No Google One Tap found")
        return False
    
    async def _log_cdp_frames(self, frame_tree: dict, depth: int = 0):
        """Log CDP frame tree"""
        try:
            frame = frame_tree.get('frame', {})
            url = frame.get('url', '')
            
            if 'google' in url.lower() or 'gsi' in url.lower():
                self.log(f"   {'  '*depth}CDP Frame: {url[:60]}")
            
            for child in frame_tree.get('childFrames', []):
                await self._log_cdp_frames(child, depth + 1)
        except:
            pass
    
    async def _find_and_click_login_nav(self) -> bool:
        """Find and click LOGIN button in navigation (not register)."""
        return await find_login_button_and_click(self.page, self.log)
    
    async def _is_already_logged_in(self) -> bool:
        """Check if user is already logged in on the site."""
        return await google_is_logged_in(self.page)
    
    async def _find_and_click_auth_nav(self) -> Optional[str]:
        """Find and click login button in navigation."""
        result = await find_login_button_and_click(self.page, self.log)
        return 'login' if result else None
    
    async def _find_and_click_google_button(self) -> bool:
        """Find and click Google login button."""
        return await find_google_button_and_click(self.page, self.log)
    
    async def _switch_to_register_form(self) -> bool:
        """Try to switch from login to register form."""
        for text in self.FORM_SWITCH_TEXTS['to_register']:
            try:
                elem = await self.page.query_selector(f'a:has-text("{text}"), button:has-text("{text}"), span:has-text("{text}")')
                if elem and await elem.is_visible():
                    await elem.click()
                    self.log(f"   Switched to register")
                    await HumanBehavior.random_delay(1, 2)
                    return True
            except:
                continue
        return False
    
    async def _handle_google_one_tap(self) -> bool:
        """
        Handle Google One Tap / Account Chooser - can be iframe, popup, or modal.
        This is the MAIN method to detect and interact with Google auth popups.
        """
        # Wait for Google popup to fully render
        await HumanBehavior.random_delay(1.5, 2.5)
        
        # === STRATEGY 1: Find Google iframes and interact with them ===
        google_iframe_handled = await self._handle_google_iframe()
        if google_iframe_handled:
            return True
        
        # === STRATEGY 2: Find One Tap / Account Chooser elements on main page ===
        main_page_handled = await self._handle_google_on_main_page()
        if main_page_handled:
            return True
        
        # === STRATEGY 3: Check for new popup windows ===
        popup_handled = await self._handle_google_popup_window()
        if popup_handled:
            return True
        
        return False
    
    async def _handle_google_iframe(self) -> bool:
        """Find and interact with Google Sign-In iframes."""
        try:
            frames = self.page.frames
            
            for frame in frames:
                try:
                    frame_url = frame.url.lower() if frame.url else ""
                    
                    # Check if this is a Google auth frame
                    if not any(x in frame_url for x in ['accounts.google.com', 'gsi.', 'google.com/gsi', 'google.com/o/oauth']):
                        continue
                    
                    self.log("   Found Google iframe")
                    
                    # Wait a bit for iframe content to load
                    await HumanBehavior.random_delay(0.5, 1)
                    
                    # === PRIORITY 1: Click on account row with email ===
                    # The account row is usually a div containing the email
                    account_clicked = await self._click_account_in_frame(frame)
                    if account_clicked:
                        return True
                    
                    # === PRIORITY 2: Click "Continue as X" button ===
                    continue_clicked = await self._click_continue_in_frame(frame)
                    if continue_clicked:
                        return True
                    
                except Exception as e:
                    self.log(f"   Frame error: {e}")
                    continue
                    
        except Exception as e:
            self.log(f"   Iframe search error: {e}")
        
        return False
    
    async def _click_account_in_frame(self, frame) -> bool:
        """Click on account row inside Google iframe or modal."""
        return await self._click_google_account_on_page(frame)
    
    async def _click_continue_in_frame(self, frame) -> bool:
        """Click Continue/Confirm button inside Google iframe."""
        
        # Build list of button texts to search
        button_texts = list(self.CONTINUE_AS_TEXTS) + list(self.OAUTH_CONSENT_TEXTS)
        
        for txt in button_texts:
            try:
                selectors = [
                    f'button:has-text("{txt}")',
                    f'div[role="button"]:has-text("{txt}")',
                    f'span:has-text("{txt}")',
                ]
                for sel in selectors:
                    elem = await frame.query_selector(sel)
                    if elem and await elem.is_visible():
                        box = await elem.bounding_box()
                        if box and box['height'] > 20:
                            self.log(f"   Button: {txt[:25]}")
                            await elem.click()
                            await HumanBehavior.random_delay(2, 4)
                            return True
            except:
                continue
        
        # Fallback: any visible button
        try:
            buttons = await frame.query_selector_all('button, div[role="button"]')
            for btn in buttons[:10]:
                try:
                    if not await btn.is_visible():
                        continue
                    text = await btn.inner_text() or ""
                    # Skip cancel/close buttons
                    text_lower = text.lower()
                    if any(x in text_lower for x in ['cancel', 'close', 'отмена', 'annuler', 'abbrechen']):
                        continue
                    if text and len(text) > 2:
                        box = await btn.bounding_box()
                        if box and box['height'] > 25:
                            self.log(f"   Fallback button: {text[:20]}")
                            await btn.click()
                            await HumanBehavior.random_delay(2, 4)
                            return True
                except:
                    continue
        except:
            pass
        
        return False
    
    async def _handle_google_on_main_page(self) -> bool:
        """Find Google One Tap or Account Chooser elements on the main page."""
        
        # === First try the universal method ===
        try:
            clicked = await self._click_google_account_on_page(self.page)
            if clicked:
                return True
        except:
            pass
        
        # === Look for "Continue as X" buttons ===
        for txt in self.CONTINUE_AS_TEXTS:
            try:
                selectors = [
                    f'button:has-text("{txt}")',
                    f'div[role="button"]:has-text("{txt}")',
                    f'span:has-text("{txt}")',
                    f'a:has-text("{txt}")',
                ]
                for sel in selectors:
                    elems = await self.page.query_selector_all(sel)
                    for elem in elems:
                        if elem and await elem.is_visible():
                            box = await elem.bounding_box()
                            if box and box['height'] > 25 and box['width'] > 50:
                                text = await elem.inner_text() or ""
                                self.log(f"   One Tap: {text[:30]}")
                                await elem.click()
                                await HumanBehavior.random_delay(2, 4)
                                return True
            except:
                continue
        
        # === Look for OAuth consent buttons (Agree and Continue, etc.) ===
        for txt in self.OAUTH_CONSENT_TEXTS:
            try:
                selectors = [
                    f'button:has-text("{txt}")',
                    f'a:has-text("{txt}")',
                    f'div[role="button"]:has-text("{txt}")',
                ]
                for sel in selectors:
                    elem = await self.page.query_selector(sel)
                    if elem and await elem.is_visible():
                        box = await elem.bounding_box()
                        if box and box['height'] > 20:
                            self.log(f"   Consent: {txt[:25]}")
                            await elem.click()
                            await HumanBehavior.random_delay(2, 4)
                            return True
            except:
                continue
        
        # === Look for account rows with email ===
        account_selectors = [
            'div[data-email]',
            'div[data-identifier]', 
            'div:has(> img):has-text("@")',
            'li:has-text("@gmail.com")',
            'div[role="listitem"]:has-text("@")',
            'div[role="option"]:has-text("@")',
        ]
        
        for sel in account_selectors:
            try:
                elems = await self.page.query_selector_all(sel)
                for elem in elems:
                    if elem and await elem.is_visible():
                        text = await elem.inner_text() or ""
                        if '@' in text and 'another' not in text.lower() and 'другой' not in text.lower():
                            self.log(f"   Account row: {text[:30]}")
                            await elem.click()
                            await HumanBehavior.random_delay(2, 4)
                            return True
            except:
                continue
        
        # === Aggressive search: any visible element with email-like text ===
        try:
            all_elements = await self.page.query_selector_all('div, span, li, button')
            for elem in all_elements[:100]:  # Check first 100
                try:
                    if not await elem.is_visible():
                        continue
                    text = await elem.inner_text() or ""
                    # Look for email pattern
                    if '@gmail.com' in text.lower() or '@googlemail.com' in text.lower():
                        box = await elem.bounding_box()
                        if box and 50 < box['height'] < 150 and 100 < box['width'] < 500:
                            if 'another' not in text.lower():
                                self.log(f"   Found email element: {text[:25]}")
                                await elem.click()
                                await HumanBehavior.random_delay(2, 4)
                                return True
                except:
                    continue
        except:
            pass
        
        # === Look for credential picker containers ===
        picker_selectors = [
            '#credential_picker_container',
            'div[id*="g_id_"]',
            'div[class*="g_id_"]',
            'div[class*="google-one-tap"]',
        ]
        
        for sel in picker_selectors:
            try:
                container = await self.page.query_selector(sel)
                if container and await container.is_visible():
                    btn = await container.query_selector('button, div[role="button"]')
                    if btn:
                        await btn.click()
                        self.log("   Picker container clicked")
                        await HumanBehavior.random_delay(2, 4)
                        return True
            except:
                continue
        
        return False
    
    async def _handle_google_popup_window(self) -> bool:
        """Handle Google auth in a separate popup window."""
        try:
            pages = self.context.pages
            
            for popup_page in pages:
                if popup_page == self.page:
                    continue
                    
                try:
                    popup_url = popup_page.url.lower()
                    if 'accounts.google.com' not in popup_url:
                        continue
                    
                    self.log("   Found Google popup window")
                    
                    # Wait for it to load
                    await popup_page.wait_for_load_state('domcontentloaded', timeout=10000)
                    await HumanBehavior.random_delay(1, 2)
                    
                    # Try to click account row
                    account_selectors = [
                        'div[data-email]',
                        'div[data-identifier]',
                        'li[data-email]',
                        'div[role="link"]',
                    ]
                    
                    for sel in account_selectors:
                        try:
                            elem = await popup_page.query_selector(sel)
                            if elem and await elem.is_visible():
                                email = await elem.get_attribute('data-email') or ""
                                self.log(f"   Selecting: {email[:25]}")
                                await elem.click()
                                await HumanBehavior.random_delay(2, 4)
                                return True
                        except:
                            continue
                    
                    # Try Continue/Allow buttons
                    for txt in ['Continue', 'Allow', 'Продолжить', 'Разрешить', 'Weiter', 'Continuer']:
                        try:
                            btn = await popup_page.query_selector(f'button:has-text("{txt}")')
                            if btn and await btn.is_visible():
                                await btn.click()
                                await HumanBehavior.random_delay(2, 4)
                                return True
                        except:
                            continue
                except:
                    continue
        except:
            pass
        
        return False
    
    async def _handle_oauth_flow(self) -> bool:
        """Handle Google OAuth popup, redirect, One Tap, or Account Chooser."""
        
        # === Multiple attempts to catch the Google popup ===
        for attempt in range(5):
            self.log(f"   OAuth check #{attempt + 1}...")
            
            await HumanBehavior.random_delay(1.5, 2.5)
            
            # === Check ALL browser contexts for Google popup windows ===
            try:
                browser = self.context.browser
                if browser:
                    all_contexts = browser.contexts
                    for ctx in all_contexts:
                        for p in ctx.pages:
                            try:
                                page_url = p.url.lower() if p.url else ""
                                if 'accounts.google.com' in page_url or 'gsi/select' in page_url:
                                    self.log(f"   Found Google window in context!")
                                    handled = await self._handle_account_chooser_popup(p)
                                    if handled:
                                        await HumanBehavior.random_delay(2, 3)
                                        return True
                            except:
                                continue
            except:
                pass
            
            # === Check current context pages ===
            try:
                pages = self.context.pages
                for p in pages:
                    try:
                        if p == self.page:
                            continue
                        page_url = p.url.lower() if p.url else ""
                        if 'accounts.google.com' in page_url or 'gsi/select' in page_url:
                            self.log("   Found Google popup in current context!")
                            handled = await self._handle_account_chooser_popup(p)
                            if handled:
                                await HumanBehavior.random_delay(2, 3)
                                return True
                    except:
                        continue
            except:
                pass
            
            # === Try One Tap / Account Chooser detection (iframes, modals) ===
            if await self._handle_google_one_tap():
                await HumanBehavior.random_delay(2, 3)
                await self._handle_google_one_tap()  # Try again for 2-step
                return True
            
            # === Check for redirect to Google ===
            try:
                if 'accounts.google.com' in self.page.url:
                    self.log("   OAuth redirect detected")
                    result = await self._complete_oauth_on_page(self.page, is_popup=False)
                    if result:
                        return True
            except:
                pass
            
            # === Check if auth completed (back on site) ===
            try:
                if attempt > 1 and 'accounts.google.com' not in self.page.url:
                    return True
            except:
                pass
        
        self.log("   ⚠️ OAuth check complete")
        return True
    
    async def _complete_oauth_on_page(self, oauth_page: Page, is_popup: bool) -> bool:
        """Complete OAuth flow on Google's page."""
        try:
            self.log("   Completing OAuth...")
            
            # Wait for page to load
            await oauth_page.wait_for_load_state('domcontentloaded', timeout=15000)
            await HumanBehavior.random_delay(1, 2)
            
            # Step 1: Select account (if account chooser is shown)
            account_selected = await self._select_google_account(oauth_page)
            
            if account_selected:
                await HumanBehavior.random_delay(2, 4)
            
            # Step 2: Click "Continue" / "Allow" if permission screen
            await self._confirm_oauth_permissions(oauth_page)
            
            await HumanBehavior.random_delay(2, 3)
            
            # If popup, it should close automatically or we wait
            if is_popup:
                # Wait for popup to close
                try:
                    await oauth_page.wait_for_event('close', timeout=10000)
                    self.log("   OAuth popup closed")
                except:
                    # Try to close manually if stuck
                    try:
                        await oauth_page.close()
                    except:
                        pass
            else:
                # Wait for redirect back
                try:
                    await self.page.wait_for_url(lambda url: 'accounts.google.com' not in url, timeout=15000)
                    self.log("   Redirected back")
                except:
                    pass
            
            return True
            
        except Exception as e:
            self.log(f"   OAuth error: {e}")
            return False
    
    async def _select_google_account(self, page: Page) -> bool:
        """Select Google account from the chooser."""
        try:
            # Wait for account list
            await page.wait_for_selector('div[data-email], div[data-identifier]', timeout=8000)
            
            # Click first account
            account = await page.query_selector('div[data-email], div[data-identifier]')
            if account:
                email = await account.get_attribute('data-email') or await account.get_attribute('data-identifier')
                self.log(f"   Selecting: {email[:20] if email else 'account'}...")
                await account.click()
                return True
        except:
            pass
        
        # Alternative: click on account item
        try:
            items = await page.query_selector_all('li[data-email], div[role="link"][data-email]')
            if items:
                await items[0].click()
                return True
        except:
            pass
        
        # Try clicking any visible account-like element
        try:
            account_selectors = [
                'div[class*="account"]', 'div[jsname="yd9FGc"]',
                'ul li', 'div[role="listitem"]'
            ]
            for sel in account_selectors:
                elem = await page.query_selector(sel)
                if elem and await elem.is_visible():
                    await elem.click()
                    return True
        except:
            pass
        
        return False
    
    async def _confirm_oauth_permissions(self, page: Page):
        """Confirm OAuth permissions if asked - all EU languages."""
        # Use OAUTH_CONSENT_TEXTS + additional permission texts
        all_buttons = list(self.OAUTH_CONSENT_TEXTS) + [
            # Additional permission-specific texts
            'Grant access', 'Give access', 'Share', 
            'Предоставить доступ', 'Дать доступ', 'Поделиться',
            'Zugriff gewähren', 'Accorder l\'accès', 'Conceder acceso',
        ]
        
        for text in all_buttons:
            try:
                btn = await page.query_selector(f'button:has-text("{text}"), div[role="button"]:has-text("{text}"), a:has-text("{text}")')
                if btn and await btn.is_visible():
                    self.log(f"   Clicking: {text[:20]}")
                    await btn.click()
                    await HumanBehavior.random_delay(1, 2)
                    return
            except:
                continue
    
    async def _handle_post_oauth_steps(self):
        """Handle any post-OAuth steps like accepting terms, setting username, birthday, etc."""
        await HumanBehavior.random_delay(1, 2)
        
        # Sometimes after OAuth, site asks for additional info
        # Try multiple rounds of form handling
        for round_num in range(3):
            form_found = False
            
            # === Check for checkboxes (terms, newsletter, etc.) ===
            try:
                checkboxes = await self.page.query_selector_all('input[type="checkbox"]')
                for cb in checkboxes[:5]:
                    try:
                        if await cb.is_visible() and not await cb.is_checked():
                            # Check if it's a terms/agree checkbox
                            parent_text = await cb.evaluate('el => el.closest("label, div")?.innerText || ""')
                            parent_lower = parent_text.lower()
                            # Only check boxes that look like consent
                            if any(x in parent_lower for x in ['agree', 'accept', 'terms', 'согласен', 'принимаю', 'условия', 'akzept', 'accepter']):
                                await cb.click()
                                await HumanBehavior.random_delay(0.3, 0.6)
                                form_found = True
                    except:
                        continue
            except:
                pass
            
            # === Check for name input fields ===
            try:
                name_selectors = [
                    'input[name*="name" i]',
                    'input[placeholder*="name" i]',
                    'input[aria-label*="name" i]',
                    'input[id*="name" i]',
                    'input[name*="username" i]',
                    'input[placeholder*="имя" i]',
                    'input[name*="firstName" i]',
                    'input[name*="lastName" i]',
                ]
                for sel in name_selectors:
                    inputs = await self.page.query_selector_all(sel)
                    for inp in inputs[:3]:
                        try:
                            if await inp.is_visible():
                                current_val = await inp.input_value()
                                if not current_val:  # Empty field
                                    # Generate a simple name
                                    import random
                                    names = ['Alex', 'Sam', 'Jordan', 'Casey', 'Riley', 'Morgan', 'Taylor']
                                    name = random.choice(names)
                                    await inp.fill(name)
                                    self.log(f"   Filled name: {name}")
                                    form_found = True
                        except:
                            continue
            except:
                pass
            
            # === Check for birthday/age selectors ===
            try:
                # Day/Month/Year dropdowns
                select_selectors = [
                    'select[name*="day" i]', 'select[name*="month" i]', 'select[name*="year" i]',
                    'select[name*="birth" i]', 'select[id*="day" i]', 'select[id*="month" i]',
                    'select[id*="year" i]', 'select[aria-label*="day" i]', 'select[aria-label*="month" i]',
                ]
                for sel in select_selectors:
                    selects = await self.page.query_selector_all(sel)
                    for select in selects[:3]:
                        try:
                            if await select.is_visible():
                                # Get available options
                                options = await select.query_selector_all('option')
                                if len(options) > 2:
                                    # Select a middle option (avoid first/last which are often placeholders)
                                    import random
                                    idx = random.randint(1, min(len(options) - 1, 20))
                                    option_value = await options[idx].get_attribute('value')
                                    if option_value:
                                        await select.select_option(value=option_value)
                                        self.log(f"   Selected dropdown option")
                                        form_found = True
                        except:
                            continue
            except:
                pass
            
            # === Check for date input fields ===
            try:
                date_inputs = await self.page.query_selector_all('input[type="date"], input[name*="birth" i], input[placeholder*="birth" i]')
                for inp in date_inputs[:2]:
                    try:
                        if await inp.is_visible():
                            current_val = await inp.input_value()
                            if not current_val:
                                # Fill with a valid adult birthdate
                                import random
                                year = random.randint(1980, 2000)
                                month = random.randint(1, 12)
                                day = random.randint(1, 28)
                                date_str = f"{year:04d}-{month:02d}-{day:02d}"
                                await inp.fill(date_str)
                                self.log(f"   Filled birthdate")
                                form_found = True
                    except:
                        continue
            except:
                pass
            
            # === Look for submit/continue button ===
            submit_texts = [
                # English
                'Submit', 'Continue', 'Complete', 'Finish', 'Done', 'Create', 'Save', 'Next', 'Sign up', 'Join',
                # Russian
                'Отправить', 'Продолжить', 'Завершить', 'Готово', 'Создать', 'Далее', 'Сохранить', 'Зарегистрироваться',
                # German
                'Absenden', 'Weiter', 'Fertig', 'Erstellen', 'Speichern', 'Registrieren',
                # French
                'Envoyer', 'Continuer', 'Terminer', 'Créer', 'Suivant', "S'inscrire",
                # Spanish
                'Enviar', 'Continuar', 'Completar', 'Crear', 'Siguiente', 'Registrarse',
                # Italian
                'Invia', 'Continua', 'Completa', 'Crea', 'Avanti', 'Iscriviti',
                # Portuguese
                'Enviar', 'Continuar', 'Concluir', 'Criar', 'Próximo', 'Cadastrar',
                # Dutch
                'Verzenden', 'Doorgaan', 'Voltooien', 'Aanmaken', 'Volgende',
                # Polish
                'Wyślij', 'Kontynuuj', 'Zakończ', 'Utwórz', 'Dalej',
            ]
            
            for text in submit_texts:
                try:
                    btn = await self.page.query_selector(f'button:has-text("{text}"), input[type="submit"][value*="{text}" i]')
                    if btn and await btn.is_visible():
                        await btn.click()
                        self.log(f"   Post-OAuth: {text}")
                        await HumanBehavior.random_delay(2, 3)
                        form_found = True
                        break
                except:
                    continue
            
            if not form_found:
                break  # No more forms to fill
            
            await HumanBehavior.random_delay(1, 2)
