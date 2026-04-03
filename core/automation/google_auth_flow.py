"""
Google Auth Flow Mixin for BrowserAutomation
Contains all Google authentication related methods for third-party sites.

This is a REFERENCE file - actual implementation remains in browser.py
to maintain stability. This file can be used for future migration to
mixin-based architecture.

Key methods:
- perform_google_auth_on_sites() - Main entry point
- _auth_on_single_site() - Auth on one site
- _perform_oauth_flow() - Handle OAuth popups
- _handle_post_oauth_steps() - Post-auth forms

Constants:
- AUTH_NAV_TEXTS - Login/register button texts in 20+ languages
- GOOGLE_BUTTON_TEXTS - Google sign-in button texts
- GOOGLE_BUTTON_SELECTORS - CSS selectors for Google buttons
"""
import asyncio
import random
import time
import re
import logging
from typing import List, Optional, TYPE_CHECKING
from urllib.parse import urlparse

from core.automation.helpers import HumanBehavior

if TYPE_CHECKING:
    from playwright.async_api import Page, BrowserContext

logger = logging.getLogger(__name__)


# ==========================================================================
# CONSTANTS - Multilingual button texts for Google Auth detection
# ==========================================================================

AUTH_NAV_TEXTS = {
    'login': [
        # English
        'Sign in', 'Log in', 'Login', 'Log In', 'Sign In',
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
        # More languages...
    ],
    'register': [
        # English
        'Sign up', 'Register', 'Create account', 'Join',
        # Russian
        'Регистрация', 'Зарегистрироваться',
        # German
        'Registrieren', 'Konto erstellen',
        # French
        "S'inscrire", 'Créer un compte',
        # More languages...
    ],
}

GOOGLE_BUTTON_TEXTS = [
    # English
    'Sign in with Google', 'Continue with Google', 'Log in with Google',
    'Sign up with Google', 'Google', 'Use Google Account',
    # Russian
    'Войти через Google', 'Продолжить с Google', 'Вход через Google',
    # German
    'Mit Google anmelden', 'Mit Google fortfahren', 'Google-Konto verwenden',
    # French
    'Se connecter avec Google', 'Continuer avec Google',
    # Spanish
    'Iniciar sesión con Google', 'Continuar con Google',
    # More languages...
]

GOOGLE_BUTTON_SELECTORS = [
    # Data attributes
    '[data-provider="google"]',
    '[data-social="google"]',
    '[data-auth="google"]',
    '[data-method="google"]',
    # Classes
    '.google-login', '.google-signin', '.google-button',
    '.btn-google', '.social-google', '.oauth-google',
    # IDs
    '#google-login', '#google-signin', '#googleSignIn',
    # Images/icons
    'button:has(img[src*="google"])',
    'a:has(img[src*="google"])',
    # SVG icons
    'button:has(svg[class*="google"])',
]


class GoogleAuthMixin:
    """
    Mixin class providing Google authentication on third-party sites.
    
    This is a complex flow that handles:
    1. Finding login/register buttons on sites
    2. Detecting Google OAuth buttons
    3. Handling OAuth popup windows
    4. Completing post-OAuth registration forms
    """
    
    # Type hints for attributes from BrowserAutomation
    page: "Page"
    context: "BrowserContext"
    should_stop: bool
    _google_auth_delay_min: int
    _google_auth_delay_max: int
    _skip_failed_sites: bool
    
    def log(self, message: str) -> None:
        """Log method - to be overridden by BrowserAutomation."""
        pass
    
    async def mute_page(self) -> None:
        """Mute page audio - implemented in BrowserAutomation."""
        pass
    
    async def perform_google_auth_on_sites(self, sites: List[str], settings: dict):
        """
        Perform Google authentication on multiple third-party sites.
        
        This is the main entry point for Google OAuth flow.
        
        Args:
            sites: List of site URLs to authenticate on
            settings: Dict with auth settings (delays, skip_failed, etc.)
        """
        # Implementation in browser.py
        pass
    
    async def _auth_on_single_site(self, url: str) -> str:
        """
        Attempt Google authentication on a single site.
        
        Flow:
        1. Navigate to site
        2. Look for login/register buttons
        3. Find Google OAuth button
        4. Handle OAuth popup
        5. Complete post-OAuth forms
        
        Returns:
            'success', 'skipped', 'failed', or 'already_logged'
        """
        # Implementation in browser.py
        pass
    
    async def _find_and_click_login_button(self) -> bool:
        """Find and click login/register button on site navigation."""
        # Implementation in browser.py
        pass
    
    async def _find_and_click_google_button(self) -> bool:
        """Find and click Google OAuth button."""
        # Implementation in browser.py
        pass
    
    async def _handle_oauth_popup(self) -> bool:
        """
        Handle Google OAuth popup window.
        
        Flow:
        1. Wait for popup to open
        2. Select Google account
        3. Confirm permissions
        4. Wait for popup to close
        """
        # Implementation in browser.py
        pass
    
    async def _confirm_oauth_permissions(self, page: "Page"):
        """Click Allow/Continue on OAuth permission screens."""
        # Implementation in browser.py
        pass
    
    async def _handle_post_oauth_steps(self):
        """
        Handle post-OAuth registration forms.
        
        Some sites require additional steps after Google OAuth:
        - Username selection
        - Terms acceptance
        - Profile completion
        """
        # Implementation in browser.py
        pass
    
    async def _check_if_logged_in(self) -> bool:
        """Check if user is already logged in on the site."""
        # Implementation in browser.py
        pass


# ==========================================================================
# HELPER FUNCTIONS
# ==========================================================================

def is_google_auth_url(url: str) -> bool:
    """Check if URL is part of Google OAuth flow."""
    google_patterns = [
        'accounts.google.com',
        'myaccount.google.com',
        'oauth2.googleapis.com',
    ]
    return any(pattern in url.lower() for pattern in google_patterns)


def extract_domain(url: str) -> str:
    """Extract domain from URL for logging."""
    try:
        parsed = urlparse(url)
        return parsed.netloc or url[:30]
    except:
        return url[:30]
