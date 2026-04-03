"""
Browser Automation Helpers - Constants and utility functions
"""
import asyncio
import random
from typing import List
from playwright.async_api import Page


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

# === GEO DOMAIN CONSTANTS ===
EU_TLDS = {
    'at', 'be', 'bg', 'hr', 'cy', 'cz', 'dk', 'ee', 'fi', 'fr',
    'de', 'gr', 'hu', 'ie', 'it', 'lv', 'lt', 'lu', 'mt', 'nl',
    'pl', 'pt', 'ro', 'sk', 'si', 'es', 'se'
}

GENERIC_TLDS = {
    'com', 'org', 'net', 'io', 'xyz', 'info', 'biz', 'co', 'app',
    'dev', 'ai', 'tech', 'online', 'site', 'website', 'blog', 'shop',
    'store', 'cloud', 'digital', 'media', 'news', 'tv', 'fm', 'me'
}

COUNTRY_TO_TLD = {
    'US': ['us', 'com'],
    'GB': ['uk', 'co.uk'],
    'CA': ['ca'],
    'AU': ['au', 'com.au'],
    'NZ': ['nz', 'co.nz'],
    'DE': ['de'], 'FR': ['fr'], 'IT': ['it'], 'ES': ['es'],
    'NL': ['nl'], 'PL': ['pl'], 'PT': ['pt'], 'AT': ['at'],
    'BE': ['be'], 'SE': ['se'], 'FI': ['fi'], 'DK': ['dk'],
    'CZ': ['cz'], 'GR': ['gr'], 'RO': ['ro'], 'HU': ['hu'],
    'SK': ['sk'], 'BG': ['bg'], 'HR': ['hr'], 'SI': ['si'],
    'LT': ['lt'], 'LV': ['lv'], 'EE': ['ee'], 'IE': ['ie'],
    'CY': ['cy'], 'MT': ['mt'], 'LU': ['lu'],
    'CH': ['ch'], 'NO': ['no'], 'IS': ['is'],
    'RU': ['ru'], 'UA': ['ua'], 'BY': ['by'], 'MD': ['md'],
    'RS': ['rs'], 'ME': ['me'], 'MK': ['mk'], 'AL': ['al'], 'BA': ['ba'],
    'TR': ['tr'], 'IL': ['il'], 'AE': ['ae'], 'SA': ['sa'], 'QA': ['qa'],
    'JP': ['jp'], 'KR': ['kr'], 'CN': ['cn'], 'IN': ['in'],
    'TH': ['th'], 'VN': ['vn'], 'ID': ['id'], 'MY': ['my'], 'PH': ['ph'],
    'SG': ['sg'], 'HK': ['hk'], 'TW': ['tw'],
    'BR': ['br', 'com.br'], 'MX': ['mx'], 'AR': ['ar'],
    'CL': ['cl'], 'CO': ['co'], 'PE': ['pe'], 'VE': ['ve'],
    'ZA': ['za', 'co.za'], 'EG': ['eg'], 'NG': ['ng'], 'KE': ['ke'],
    'MA': ['ma'], 'DZ': ['dz'], 'TN': ['tn'],
}

COUNTRY_NAME_TO_CODE = {
    "UNITED STATES": "US", "USA": "US", "UNITED STATES OF AMERICA": "US",
    "UNITED KINGDOM": "GB", "UK": "GB", "GREAT BRITAIN": "GB", "ENGLAND": "GB",
    "GERMANY": "DE", "DEUTSCHLAND": "DE",
    "FRANCE": "FR", "ITALY": "IT", "ITALIA": "IT",
    "SPAIN": "ES", "ESPANA": "ES",
    "NETHERLANDS": "NL", "THE NETHERLANDS": "NL", "HOLLAND": "NL",
    "POLAND": "PL", "POLSKA": "PL",
    "RUSSIA": "RU", "RUSSIAN FEDERATION": "RU",
    "UKRAINE": "UA", "CANADA": "CA", "AUSTRALIA": "AU",
    "JAPAN": "JP", "SOUTH KOREA": "KR", "KOREA": "KR", "CHINA": "CN",
    "BRAZIL": "BR", "BRASIL": "BR", "MEXICO": "MX", "ARGENTINA": "AR",
    "INDIA": "IN", "SINGAPORE": "SG",
    "SWEDEN": "SE", "NORWAY": "NO", "FINLAND": "FI", "DENMARK": "DK",
    "SWITZERLAND": "CH", "AUSTRIA": "AT", "BELGIUM": "BE", "PORTUGAL": "PT",
    "CZECH REPUBLIC": "CZ", "CZECHIA": "CZ", "GREECE": "GR",
    "TURKEY": "TR", "ISRAEL": "IL",
    "UNITED ARAB EMIRATES": "AE", "UAE": "AE",
    "SOUTH AFRICA": "ZA", "THAILAND": "TH", "VIETNAM": "VN",
    "INDONESIA": "ID", "MALAYSIA": "MY", "PHILIPPINES": "PH",
    "HONG KONG": "HK", "TAIWAN": "TW", "NEW ZEALAND": "NZ",
    "IRELAND": "IE", "ROMANIA": "RO", "HUNGARY": "HU",
    "SLOVAKIA": "SK", "BULGARIA": "BG", "CROATIA": "HR",
    "SERBIA": "RS", "LITHUANIA": "LT", "LATVIA": "LV", "ESTONIA": "EE",
    "CHILE": "CL", "COLOMBIA": "CO", "PERU": "PE",
    "SLOVENIA": "SI", "CYPRUS": "CY", "MALTA": "MT", "LUXEMBOURG": "LU",
    "ICELAND": "IS", "MONACO": "MC", "ANDORRA": "AD", "LIECHTENSTEIN": "LI",
    "SAN MARINO": "SM", "MONTENEGRO": "ME",
    "NORTH MACEDONIA": "MK", "MACEDONIA": "MK",
    "ALBANIA": "AL", "BOSNIA AND HERZEGOVINA": "BA", "BOSNIA": "BA",
    "KOSOVO": "XK", "MOLDOVA": "MD", "BELARUS": "BY",
    "GEORGIA": "GE", "ARMENIA": "AM", "AZERBAIJAN": "AZ",
    "KAZAKHSTAN": "KZ", "UZBEKISTAN": "UZ",
    "PAKISTAN": "PK", "BANGLADESH": "BD", "SRI LANKA": "LK", "NEPAL": "NP",
    "CAMBODIA": "KH", "MYANMAR": "MM", "BURMA": "MM", "LAOS": "LA",
    "MONGOLIA": "MN", "NORTH KOREA": "KP",
    "SAUDI ARABIA": "SA", "QATAR": "QA", "KUWAIT": "KW", "BAHRAIN": "BH",
    "OMAN": "OM", "JORDAN": "JO", "LEBANON": "LB", "IRAQ": "IQ", "IRAN": "IR",
    "EGYPT": "EG", "MOROCCO": "MA", "ALGERIA": "DZ", "TUNISIA": "TN",
    "LIBYA": "LY", "NIGERIA": "NG", "KENYA": "KE", "GHANA": "GH",
    "ETHIOPIA": "ET", "TANZANIA": "TZ", "UGANDA": "UG",
    "VENEZUELA": "VE", "ECUADOR": "EC", "BOLIVIA": "BO",
    "PARAGUAY": "PY", "URUGUAY": "UY",
    "COSTA RICA": "CR", "PANAMA": "PA", "GUATEMALA": "GT",
    "CUBA": "CU", "DOMINICAN REPUBLIC": "DO", "PUERTO RICO": "PR", "JAMAICA": "JM",
}


# === HELPER FUNCTIONS ===

def normalize_country_code(country: str) -> str:
    """Normalize country name to 2-letter code."""
    if not country:
        return ""
    country_upper = country.upper().strip()
    if len(country_upper) == 2:
        return country_upper
    return COUNTRY_NAME_TO_CODE.get(country_upper, country_upper)


def get_site_tld(url: str) -> str:
    """Extract TLD from URL."""
    try:
        domain = url.lower().replace('https://', '').replace('http://', '')
        domain = domain.split('/')[0].split(':')[0]
        parts = domain.split('.')
        if len(parts) >= 2:
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
    normalized_code = normalize_country_code(country_code)
    tld = get_site_tld(url)
    local_tlds = COUNTRY_TO_TLD.get(normalized_code.upper(), [normalized_code.lower()])
    return tld in local_tlds


def is_site_generic(url: str) -> bool:
    """Check if site has a generic (non-country) TLD."""
    tld = get_site_tld(url)
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
            generic_sites.append(site)
    
    return local_sites, generic_sites


# === HUMAN BEHAVIOR SIMULATION ===

class HumanBehavior:
    """Simulates human-like browser interactions."""
    
    @staticmethod
    async def random_delay(min_sec: float = 0.5, max_sec: float = 3.0):
        """Wait for a random time to simulate human reading/thinking."""
        await asyncio.sleep(random.uniform(min_sec, max_sec))
    
    @staticmethod
    async def smooth_scroll(page: Page, direction: str = "down", 
                            iterations_min: int = 3, iterations_max: int = 6,
                            pixels_min: int = 50, pixels_max: int = 150,
                            pause_min: float = 0.1, pause_max: float = 0.3):
        """Perform smooth scrolling like a human would."""
        try:
            for _ in range(random.randint(iterations_min, iterations_max)):
                scroll = random.randint(pixels_min, pixels_max) * (1 if direction == "down" else -1)
                await page.evaluate(f"window.scrollBy(0, {scroll})")
                await asyncio.sleep(random.uniform(pause_min, pause_max))
        except:
            pass
    
    @staticmethod
    async def random_mouse(page: Page):
        """Move mouse to a random position on the page."""
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
        """Simulate a user reading content on a page."""
        for _ in range(random.randint(2, 4)):
            await HumanBehavior.smooth_scroll(page, "down")
            await HumanBehavior.random_delay(1, 3)
