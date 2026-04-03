"""Browser Automation modules for Cookie Robot

Helpers are in core/automation/helpers.py
Main BrowserAutomation class is in core/automation.py (legacy location)
"""
from core.automation.helpers import (
    HumanBehavior,
    COOKIE_SELECTORS, COOKIE_BUTTON_TEXTS,
    CLOSE_SELECTORS, CLOSE_TEXTS,
    BLOCKED_MEDIA_PATTERNS, BLOCKED_AD_DOMAINS,
    YOUTUBE_SEARCH_WORDS,
    EU_TLDS, GENERIC_TLDS, COUNTRY_TO_TLD, COUNTRY_NAME_TO_CODE,
    normalize_country_code, get_site_tld, is_site_local_geo,
    is_site_generic, split_sites_by_geo
)

__all__ = [
    'HumanBehavior',
    'COOKIE_SELECTORS', 'COOKIE_BUTTON_TEXTS',
    'CLOSE_SELECTORS', 'CLOSE_TEXTS',
    'BLOCKED_MEDIA_PATTERNS', 'BLOCKED_AD_DOMAINS',
    'YOUTUBE_SEARCH_WORDS',
    'normalize_country_code', 'get_site_tld',
    'is_site_local_geo', 'is_site_generic', 'split_sites_by_geo'
]
