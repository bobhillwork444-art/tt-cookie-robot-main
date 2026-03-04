"""
Google OAuth Authentication Module for Cookie Robot
Universal handler for Google Sign-In across any website.

Architecture:
- GoogleAuthManager: Main orchestrator that coordinates all auth detection and handling
- WindowMonitor: Detects and handles popup windows
- IframeMonitor: Detects and handles Google auth iframes
- AccountChooserHandler: Handles account selection UI
- ConsentHandler: Handles OAuth consent screens

This module provides a unified, robust approach to handling Google OAuth
across different websites and scenarios (popups, iframes, redirects, modals).
"""
import asyncio
import logging
import time
import re
from typing import Optional, List, Dict, Callable, Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION - All patterns and selectors in one place
# =============================================================================

class GoogleAuthConfig:
    """All configuration for Google Auth detection and handling"""
    
    # URL patterns that indicate Google Auth
    GOOGLE_AUTH_URLS = [
        'accounts.google.com',
        'accounts.youtube.com',
        '/o/oauth2/',
        '/signin/oauth/',
        '/gsi/select',
        '/gsi/iframe',
        '/gsi/button',
        '/AccountChooser',
        '/ServiceLogin',
        'google.com/gsi',
    ]
    
    # Selectors for Google Sign-In buttons on websites
    GOOGLE_BUTTON_SELECTORS = [
        '[data-provider="google"]',
        '[data-social="google"]',
        '[data-oauthserver*="google"]',
        '[aria-label*="Google" i]',
        '[class*="google-sign" i]',
        '[class*="google_sign" i]',
        '[class*="google-login" i]',
        '[class*="g-signin"]',
        '[class*="gsi-material-button"]',
        '#credential_picker_container',
        '[id^="g_id_"]',
        'button[class*="google" i]',
        'a[class*="google" i]',
        '[class*="social-google"]',
        '[class*="btn-google"]',
        '[class*="google-btn"]',
    ]
    
    # Button texts for Google Sign-In (multi-language)
    GOOGLE_BUTTON_TEXTS = [
        # English
        'Sign in with Google', 'Continue with Google', 'Log in with Google',
        'Login with Google', 'Google', 'Connect with Google',
        # Russian
        'Войти через Google', 'Продолжить с Google', 'Вход через Google',
        'Авторизоваться через Google',
        # German
        'Mit Google anmelden', 'Weiter mit Google', 'Mit Google fortfahren',
        'Über Google anmelden',
        # French
        'Se connecter avec Google', 'Continuer avec Google', 
        'Connexion avec Google', "S'inscrire avec Google",
        # Spanish
        'Iniciar sesión con Google', 'Continuar con Google',
        'Acceder con Google',
        # Italian
        'Accedi con Google', 'Continua con Google', 'Iscriviti con Google',
        # Portuguese
        'Entrar com Google', 'Continuar com Google', 'Fazer login com Google',
        # Dutch
        'Inloggen met Google', 'Doorgaan met Google', 'Aanmelden met Google',
        # Polish
        'Zaloguj się przez Google', 'Kontynuuj przez Google',
        # Romanian
        'Continuă cu Google', 'Conectează-te cu Google',
        # Czech
        'Pokračovat přes Google', 'Přihlásit se přes Google',
        # Turkish
        'Google ile giriş yap', 'Google ile devam et',
        # Ukrainian
        'Увійти через Google', 'Продовжити з Google',
    ]
    
    # Account chooser indicators
    ACCOUNT_CHOOSER_TEXTS = [
        'Choose an account', 'Select account', 'Sign in',
        'Выберите аккаунт', 'Вход',
        'Konto auswählen', 'Anmelden',
        'Choisir un compte', 'Se connecter', 'Choisissez un compte',
        'Elige una cuenta', 'Iniciar sesión',
        'Scegli un account', 'Accedi',
        'Kies een account', 'Inloggen',
        'Wybierz konto',
        'to continue to', 'pour continuer',
    ]
    
    # Texts to skip (not accounts)
    SKIP_TEXTS = [
        'use another account', 'add account', 'use a different account',
        'другой аккаунт', 'добавить аккаунт', 'другим аккаунтом',
        'anderes konto', 'konto hinzufügen', 'anderen konto',
        'utiliser un autre compte', 'ajouter un compte', 'autre compte',
        'usar otra cuenta', 'añadir cuenta', 'otra cuenta',
        'cancel', 'отмена', 'abbrechen', 'annuler', 'cancelar',
        'use a different account', 'different account',
        'create account', 'создать аккаунт',
    ]
    
    # Consent/Allow button texts
    CONSENT_BUTTON_TEXTS = [
        # English
        'Allow', 'Continue', 'Accept', 'Confirm', 'Agree', 'OK', 'Yes',
        'Agree and Continue', 'Allow access', 'I agree', 'Approve',
        # Russian
        'Разрешить', 'Продолжить', 'Принять', 'Подтвердить', 'Согласен', 'Да',
        'Согласиться и продолжить',
        # German
        'Zulassen', 'Weiter', 'Akzeptieren', 'Bestätigen', 'Zustimmen',
        'Einwilligen',
        # French
        'Autoriser', 'Continuer', 'Accepter', 'Confirmer', "J'accepte",
        # Spanish
        'Permitir', 'Continuar', 'Aceptar', 'Confirmar', 'Acepto',
        # Italian
        'Consenti', 'Continua', 'Accetta', 'Conferma', 'Accetto',
        # Dutch
        'Toestaan', 'Doorgaan', 'Accepteren', 'Bevestigen', 'Akkoord',
        # Polish
        'Zezwól', 'Kontynuuj', 'Akceptuj', 'Potwierdź', 'Zgadzam się',
    ]
    
    # "Continue as [Name]" patterns for One Tap
    CONTINUE_AS_PATTERNS = [
        'Continue as', 'Продолжить как', 'Weiter als', 'Fortfahren als',
        'Continuer en tant que', 'Continuar como', 'Continua come',
        'Doorgaan als', 'Kontynuuj jako', 'Pokračovat jako',
        'Продовжити як', 'Olarak devam et', 'Fortsätt som',
    ]
    
    # Login navigation texts (to find login button on site)
    LOGIN_NAV_TEXTS = [
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
        # Portuguese
        'Entrar', 'Iniciar sessão',
        # Dutch
        'Inloggen', 'Aanmelden',
        # Polish
        'Zaloguj się', 'Zaloguj',
        # Turkish
        'Giriş yap', 'Oturum aç',
        # Ukrainian
        'Увійти', 'Вхід',
    ]
    
    # Logged in indicators
    LOGGED_IN_TEXTS = [
        # English
        'Profile', 'My account', 'Account', 'Dashboard', 'Logout', 'Sign out',
        'Log out', 'My Profile', 'Settings',
        # Russian
        'Профиль', 'Мой аккаунт', 'Личный кабинет', 'Выйти', 'Выход',
        # German
        'Profil', 'Mein Konto', 'Abmelden', 'Konto',
        # French
        'Profil', 'Mon compte', 'Déconnexion', 'Se déconnecter',
        # Spanish
        'Perfil', 'Mi cuenta', 'Cerrar sesión',
        # Italian
        'Profilo', 'Il mio account', 'Esci',
        # Dutch
        'Profiel', 'Mijn account', 'Uitloggen',
        # Polish
        'Profil', 'Moje konto', 'Wyloguj',
    ]
    
    # Timeouts
    POPUP_TIMEOUT = 15000
    ELEMENT_TIMEOUT = 5000
    AUTH_TOTAL_TIMEOUT = 60000
    WATCHER_INTERVAL = 0.5  # seconds
    
    # Account row size constraints (to filter out wrong elements)
    ACCOUNT_ROW_MIN_HEIGHT = 35
    ACCOUNT_ROW_MAX_HEIGHT = 150
    ACCOUNT_ROW_MIN_WIDTH = 100
    ACCOUNT_ROW_MAX_WIDTH = 500


def is_google_auth_url(url: str) -> bool:
    """Check if URL is a Google auth URL"""
    if not url:
        return False
    url_lower = url.lower()
    return any(pattern in url_lower for pattern in GoogleAuthConfig.GOOGLE_AUTH_URLS)


def should_skip_element(text: str) -> bool:
    """Check if element should be skipped (cancel, another account, etc.)"""
    text_lower = text.lower()
    return any(skip in text_lower for skip in GoogleAuthConfig.SKIP_TEXTS)


# =============================================================================
# GOOGLE AUTH MANAGER - Main orchestrator
# =============================================================================

class GoogleAuthManager:
    """
    Universal Google OAuth handler.
    Detects and handles Google auth in popups, iframes, and redirects.
    
    Usage:
        manager = GoogleAuthManager(page, context, log_callback)
        await manager.start_watcher()  # Start background monitoring
        
        # Do your auth flow...
        await manager.click_google_button()  # Click site's Google button
        
        # Watcher handles popup automatically, or call manually:
        await manager.handle_auth_popup()
        
        await manager.stop_watcher()
    """
    
    def __init__(self, page, context, log_callback=None):
        self.page = page
        self.context = context
        self.log = log_callback or (lambda x: logger.info(x))
        
        # State
        self.is_active = False
        self.watcher_task = None
        self.original_url = None
        self.auth_success = False
        self._handled_popups = set()  # Track handled popup URLs to avoid duplicates
        
    async def start_watcher(self):
        """Start background watcher for Google auth popups"""
        self.is_active = True
        self.original_url = self.page.url
        self.auth_success = False
        self._handled_popups.clear()
        self.watcher_task = asyncio.create_task(self._watcher_loop())
        self.log("   👁 Auth watcher started")
    
    async def stop_watcher(self):
        """Stop the background watcher"""
        self.is_active = False
        if self.watcher_task:
            self.watcher_task.cancel()
            try:
                await self.watcher_task
            except asyncio.CancelledError:
                pass
            self.watcher_task = None
    
    async def _watcher_loop(self):
        """Main watcher loop - runs every 0.5 seconds"""
        while self.is_active:
            try:
                # Check all possible locations for Google auth
                handled = await self._scan_and_handle()
                if handled:
                    self.auth_success = True
                    self.log("   🔔 Auth popup handled!")
                    await asyncio.sleep(2)  # Brief pause after handling
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"Watcher error: {e}")
            
            await asyncio.sleep(GoogleAuthConfig.WATCHER_INTERVAL)
    
    async def _scan_and_handle(self) -> bool:
        """Scan for Google auth and handle if found"""
        
        # Priority 1: Check main page for modals/overlays (most common for 20minutes.fr style)
        handled = await self._check_main_page()
        if handled:
            return True
        
        # Priority 2: Check popup windows
        handled = await self._check_popup_windows()
        if handled:
            return True
        
        # Priority 3: Check iframes (Google One Tap, embedded chooser)
        # Note: _check_iframes now only handles if iframe has content
        handled = await self._check_iframes()
        if handled:
            return True
        
        # Priority 4: Check if redirected to Google
        handled = await self._check_redirect()
        if handled:
            return True
        
        return False
    
    # =========================================================================
    # POPUP WINDOW HANDLING
    # =========================================================================
    
    async def _check_popup_windows(self) -> bool:
        """Check all browser windows for Google auth"""
        try:
            # Log all pages we can see
            all_pages_found = []
            
            # Check all contexts (Octo Browser might use multiple)
            browser = self.context.browser
            if browser:
                for ctx in browser.contexts:
                    for page in ctx.pages:
                        page_url = page.url or ""
                        all_pages_found.append(page_url[:50])
                        
                        if page == self.page:
                            continue
                            
                        if is_google_auth_url(page_url):
                            # Avoid handling same popup twice
                            if page_url in self._handled_popups:
                                continue
                            self._handled_popups.add(page_url)
                            self.log(f"   Found Google popup window!")
                            result = await self._handle_auth_page(page)
                            if result:
                                return True
            
            # Also check current context
            for page in self.context.pages:
                page_url = page.url or ""
                if page == self.page:
                    continue
                if is_google_auth_url(page_url):
                    if page_url in self._handled_popups:
                        continue
                    self._handled_popups.add(page_url)
                    self.log(f"   Found Google popup in context!")
                    result = await self._handle_auth_page(page)
                    if result:
                        return True
            
            # Debug: log what pages we found (only once per 10 scans)
            if not hasattr(self, '_popup_log_counter'):
                self._popup_log_counter = 0
            self._popup_log_counter += 1
            if self._popup_log_counter % 20 == 1 and len(all_pages_found) > 1:
                self.log(f"   Pages in browser: {len(all_pages_found)}")
                    
        except Exception as e:
            logger.debug(f"Popup check error: {e}")
        
        return False
    
    # =========================================================================
    # IFRAME HANDLING
    # =========================================================================
    
    async def _check_iframes(self) -> bool:
        """Check iframes for Google auth content"""
        try:
            # Method 1: Use frame_locator (more reliable for cross-origin)
            google_iframe_selectors = [
                'iframe[src*="accounts.google.com"]',
                'iframe[src*="gsi"]',
                'iframe[src*="google.com/gsi"]',
            ]
            
            for selector in google_iframe_selectors:
                try:
                    frame_loc = self.page.frame_locator(selector)
                    
                    # Try to click email in this iframe
                    try:
                        email_loc = frame_loc.locator('text=@gmail.com').first
                        if await email_loc.count() > 0:
                            text = await email_loc.inner_text()
                            self.log(f"   ✓ Found email in iframe: {text[:30]}")
                            await email_loc.click(timeout=3000)
                            return True
                    except:
                        pass
                    
                    # Try data-email
                    try:
                        data_email_loc = frame_loc.locator('[data-email]').first
                        if await data_email_loc.count() > 0:
                            self.log("   ✓ Clicking [data-email] in iframe")
                            await data_email_loc.click(timeout=3000)
                            return True
                    except:
                        pass
                    
                    # Try Continue as button
                    try:
                        continue_loc = frame_loc.locator('button:has-text("Continue as")').first
                        if await continue_loc.count() > 0:
                            self.log("   ✓ Clicking 'Continue as' in iframe")
                            await continue_loc.click(timeout=3000)
                            return True
                    except:
                        pass
                        
                except:
                    continue
            
            # Method 2: Check frames list
            for frame in self.page.frames:
                if frame == self.page.main_frame:
                    continue
                
                frame_url = frame.url or ""
                if is_google_auth_url(frame_url):
                    short_url = frame_url.split('?')[0][-40:] if '?' in frame_url else frame_url[-40:]
                    self.log(f"   Found Google iframe: ...{short_url}")
                    
                    result = await self._handle_auth_frame(frame)
                    if result:
                        return True
                    
        except Exception as e:
            logger.debug(f"Iframe check error: {e}")
        
        return False
    
    async def _handle_auth_frame(self, frame) -> bool:
        """Handle Google auth inside an iframe or page"""
        
        # Method 1: Use locator with direct text click (works better for cross-origin)
        try:
            # Try clicking on email text directly
            locator = frame.locator('text=@gmail.com').first
            if await locator.count() > 0:
                text = await locator.inner_text()
                self.log(f"   ✓ Found email via locator: {text[:30]}")
                await locator.click(timeout=3000)
                return True
        except Exception as e:
            logger.debug(f"Locator @gmail.com failed: {e}")
        
        # Method 2: Try data-email with locator
        try:
            locator = frame.locator('[data-email]').first
            if await locator.count() > 0:
                await locator.click(timeout=3000)
                self.log("   ✓ Clicked [data-email] via locator")
                return True
        except Exception as e:
            logger.debug(f"Locator data-email failed: {e}")
        
        # Method 3: Try data-identifier with locator
        try:
            locator = frame.locator('[data-identifier]').first
            if await locator.count() > 0:
                await locator.click(timeout=3000)
                self.log("   ✓ Clicked [data-identifier] via locator")
                return True
        except Exception as e:
            logger.debug(f"Locator data-identifier failed: {e}")
        
        # Method 4: Try role=link with locator
        try:
            locator = frame.locator('[role="link"]').first
            if await locator.count() > 0:
                text = await locator.inner_text()
                if '@' in text or 'gmail' in text.lower():
                    self.log(f"   ✓ Clicked role=link: {text[:30]}")
                    await locator.click(timeout=3000)
                    return True
        except Exception as e:
            logger.debug(f"Locator role=link failed: {e}")
        
        # Method 5: Try li elements with locator
        try:
            locators = frame.locator('li')
            count = await locators.count()
            for i in range(min(count, 10)):
                try:
                    loc = locators.nth(i)
                    text = await loc.inner_text()
                    if '@gmail' in text.lower() and 'another' not in text.lower():
                        self.log(f"   ✓ Clicked li: {text[:30]}")
                        await loc.click(timeout=3000)
                        return True
                except:
                    continue
        except Exception as e:
            logger.debug(f"Locator li failed: {e}")
        
        # Method 6: Try divs with tabindex
        try:
            locators = frame.locator('div[tabindex="0"]')
            count = await locators.count()
            for i in range(min(count, 10)):
                try:
                    loc = locators.nth(i)
                    text = await loc.inner_text()
                    if '@gmail' in text.lower() or '@googlemail' in text.lower():
                        if 'another' not in text.lower() and 'different' not in text.lower():
                            self.log(f"   ✓ Clicked div[tabindex]: {text[:30]}")
                            await loc.click(timeout=3000)
                            return True
                except:
                    continue
        except Exception as e:
            logger.debug(f"Locator div[tabindex] failed: {e}")
        
        # Method 7: Try "Continue as" buttons
        for pattern in GoogleAuthConfig.CONTINUE_AS_PATTERNS:
            try:
                locator = frame.locator(f'button:has-text("{pattern}")').first
                if await locator.count() > 0:
                    self.log(f"   ✓ Clicked: {pattern}")
                    await locator.click(timeout=3000)
                    return True
            except:
                continue
        
        self.log("   ⚠️ No clickable element found in iframe")
        return False
    
    # =========================================================================
    # MAIN PAGE HANDLING (for modals/overlays)
    # =========================================================================
    
    async def _check_main_page(self) -> bool:
        """Check main page for Google auth modals/overlays"""
        try:
            # First, try direct click on email text (most reliable for modals)
            email_patterns = ['@gmail.com', '@googlemail.com']
            for pattern in email_patterns:
                try:
                    # Try clicking element with email directly
                    elems = await self.page.query_selector_all(f'text={pattern}')
                    for elem in elems[:5]:
                        if elem and await elem.is_visible():
                            text = await elem.inner_text() or ""
                            if not should_skip_element(text):
                                self.log(f"   ✓ Found email on page: {text[:30]}")
                                await elem.click()
                                return True
                except Exception as e:
                    logger.debug(f"Email pattern {pattern} failed: {e}")
            
            # Try specific selectors for Google modal
            modal_selectors = [
                '[data-email]',
                '[data-identifier]', 
                'div[data-authuser]',
                '[role="option"]',
                '[role="link"][tabindex]',
            ]
            
            for selector in modal_selectors:
                try:
                    elems = await self.page.query_selector_all(selector)
                    for elem in elems[:5]:
                        if await elem.is_visible():
                            text = await elem.inner_text() or ""
                            if '@' in text and not should_skip_element(text):
                                self.log(f"   ✓ Found modal element ({selector}): {text[:30]}")
                                await elem.click()
                                return True
                except:
                    continue
            
            # Look for Google modal indicators and search inside
            indicators = [
                ('Choose an account', 'en'),
                ('Выберите аккаунт', 'ru'),
                ('Choisissez un compte', 'fr'),
                ('Sign in to', 'en'),
                ('with google.com', 'en'),
                ('to continue', 'en'),
            ]
            
            for indicator_text, lang in indicators:
                try:
                    elem = await self.page.query_selector(f'text={indicator_text}')
                    if elem and await elem.is_visible():
                        self.log(f"   Found Google modal ({lang}), searching...")
                        
                        # Find all elements and look for email
                        all_elements = await self.page.query_selector_all('div, li, span, button')
                        for el in all_elements[:300]:
                            try:
                                text = await el.inner_text() or ""
                                text_lower = text.lower()
                                
                                if '@gmail.com' in text_lower or '@googlemail.com' in text_lower:
                                    if should_skip_element(text):
                                        continue
                                    
                                    box = await el.bounding_box()
                                    if box and box['height'] > 20 and box['width'] > 50:
                                        self.log(f"   ✓ Clicking account: {text[:40]}")
                                        await el.click()
                                        return True
                            except:
                                continue
                        
                        # If we found modal but no email, try clicking any account-like row
                        self.log("   No email found, trying account rows...")
                        rows = await self.page.query_selector_all('[tabindex="0"], [role="button"], [role="option"]')
                        for row in rows[:20]:
                            try:
                                if await row.is_visible():
                                    text = await row.inner_text() or ""
                                    if not should_skip_element(text) and len(text) > 3:
                                        box = await row.bounding_box()
                                        if box and 40 < box['height'] < 150 and box['width'] > 100:
                                            self.log(f"   ✓ Clicking row: {text[:40]}")
                                            await row.click()
                                            return True
                            except:
                                continue
                        break
                except:
                    continue
                    
        except Exception as e:
            logger.debug(f"Main page check error: {e}")
        
        return False
    
    # =========================================================================
    # REDIRECT HANDLING
    # =========================================================================
    
    async def _check_redirect(self) -> bool:
        """Check if page redirected to Google"""
        try:
            if is_google_auth_url(self.page.url):
                self.log("   Redirected to Google")
                return await self._handle_auth_page(self.page)
        except:
            pass
        return False
    
    # =========================================================================
    # AUTH PAGE HANDLER (for popup or redirect)
    # =========================================================================
    
    async def _handle_auth_page(self, page) -> bool:
        """Handle a full Google auth page (popup or redirect)"""
        try:
            await page.wait_for_load_state('domcontentloaded', timeout=10000)
            await asyncio.sleep(1)  # Wait for JS
            
            # Try clicking account
            result = await self._handle_auth_frame(page)
            
            if result:
                # Wait for page to close or redirect
                await asyncio.sleep(2)
                return True
                
        except Exception as e:
            logger.debug(f"Auth page error: {e}")
        
        return False
    
    # =========================================================================
    # CLICK STRATEGIES - Multiple methods to click the right element
    # =========================================================================
    
    async def _click_data_email(self, target) -> bool:
        """Click element with data-email attribute (most reliable)"""
        try:
            elem = await target.query_selector('[data-email]')
            if elem:
                # Verify it's not "another account"
                text = await elem.inner_text() or ""
                if not should_skip_element(text):
                    await elem.click()
                    return True
        except:
            pass
        return False
    
    async def _click_data_identifier(self, target) -> bool:
        """Click element with data-identifier attribute"""
        try:
            elem = await target.query_selector('[data-identifier]')
            if elem:
                text = await elem.inner_text() or ""
                if not should_skip_element(text):
                    await elem.click()
                    return True
        except:
            pass
        return False
    
    async def _click_by_email_text(self, target) -> bool:
        """Click element containing email address"""
        try:
            # Find all elements and check for email
            elements = await target.query_selector_all('div, li, span, a')
            
            for elem in elements[:150]:  # Limit search
                try:
                    text = await elem.inner_text()
                    if not text:
                        continue
                    
                    text_lower = text.lower()
                    
                    # Check for email patterns
                    if '@gmail.com' in text_lower or '@googlemail.com' in text_lower:
                        # Skip unwanted elements
                        if should_skip_element(text):
                            continue
                        
                        # Check element size (should be account row sized)
                        box = await elem.bounding_box()
                        if box:
                            height_ok = GoogleAuthConfig.ACCOUNT_ROW_MIN_HEIGHT < box['height'] < GoogleAuthConfig.ACCOUNT_ROW_MAX_HEIGHT
                            width_ok = GoogleAuthConfig.ACCOUNT_ROW_MIN_WIDTH < box['width'] < GoogleAuthConfig.ACCOUNT_ROW_MAX_WIDTH
                            if height_ok and width_ok:
                                await elem.click()
                                return True
                            
                            # Also try clicking if it's a small element (might be email text)
                            if box['height'] < 50 and box['width'] > 50:
                                # Try clicking parent
                                try:
                                    parent = await elem.evaluate_handle('el => el.closest("div[tabindex], li, [role=option], [role=link]")')
                                    if parent:
                                        parent_elem = parent.as_element()
                                        if parent_elem:
                                            await parent_elem.click()
                                            return True
                                except:
                                    pass
                            
                except:
                    continue
                    
        except:
            pass
        
        return False
    
    async def _click_continue_as(self, target) -> bool:
        """Click 'Continue as [Name]' button"""
        for pattern in GoogleAuthConfig.CONTINUE_AS_PATTERNS:
            try:
                selectors = [
                    f'button:has-text("{pattern}")',
                    f'div[role="button"]:has-text("{pattern}")',
                    f'span:has-text("{pattern}")',
                ]
                for selector in selectors:
                    elem = await target.query_selector(selector)
                    if elem and await elem.is_visible():
                        await elem.click()
                        return True
            except:
                continue
        
        return False
    
    async def _click_account_row(self, target) -> bool:
        """Click on account row element by role"""
        selectors = [
            '[role="link"]',
            '[role="option"]',
            '[role="listitem"]',
            'li[tabindex]',
            'div[tabindex="0"]',
        ]
        
        for selector in selectors:
            try:
                elements = await target.query_selector_all(selector)
                
                for elem in elements[:10]:  # Check first 10
                    try:
                        text = await elem.inner_text() or ""
                        
                        # Must have email-like content, must not be skip element
                        if '@' in text and not should_skip_element(text):
                            box = await elem.bounding_box()
                            if box and box['height'] > GoogleAuthConfig.ACCOUNT_ROW_MIN_HEIGHT:
                                await elem.click()
                                return True
                    except:
                        continue
            except:
                continue
        
        return False
    
    async def _click_consent_button(self, target) -> bool:
        """Click consent/allow button"""
        for text in GoogleAuthConfig.CONSENT_BUTTON_TEXTS:
            try:
                selectors = [
                    f'button:has-text("{text}")',
                    f'div[role="button"]:has-text("{text}")',
                    f'input[value="{text}"]',
                ]
                
                for selector in selectors:
                    try:
                        elem = await target.query_selector(selector)
                        if elem and await elem.is_visible():
                            # Make sure it's not a cancel button
                            elem_text = await elem.inner_text() or ""
                            if 'cancel' not in elem_text.lower() and 'отмена' not in elem_text.lower():
                                await elem.click()
                                return True
                    except:
                        continue
            except:
                continue
        
        return False
    
    # =========================================================================
    # PUBLIC METHODS - For external use
    # =========================================================================
    
    async def find_and_click_google_button(self) -> bool:
        """Find and click Google Sign-In button on current page"""
        return await find_google_button_and_click(self.page, self.log)
    
    async def find_and_click_login_button(self) -> bool:
        """Find and click Login button in site navigation"""
        return await find_login_button_and_click(self.page, self.log)
    
    async def is_logged_in(self) -> bool:
        """Check if user appears to be logged in on current site"""
        return await is_logged_in(self.page)
    
    async def handle_auth_manually(self) -> bool:
        """Manually trigger auth handling (when watcher might have missed it)"""
        return await self._scan_and_handle()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

async def find_google_button_and_click(page, log_callback=None) -> bool:
    """Find and click Google Sign-In button on page"""
    log = log_callback or (lambda x: logger.info(x))
    
    # Method 1: By selector
    for selector in GoogleAuthConfig.GOOGLE_BUTTON_SELECTORS:
        try:
            elem = await page.query_selector(selector)
            if elem and await elem.is_visible():
                box = await elem.bounding_box()
                if box and 20 < box['height'] < 100:
                    log(f"   Google button: {selector[:30]}")
                    await elem.click()
                    return True
        except:
            continue
    
    # Method 2: By text
    for text in GoogleAuthConfig.GOOGLE_BUTTON_TEXTS:
        try:
            selectors = [
                f'button:has-text("{text}")',
                f'a:has-text("{text}")',
                f'div[role="button"]:has-text("{text}")',
            ]
            for selector in selectors:
                elem = await page.query_selector(selector)
                if elem and await elem.is_visible():
                    box = await elem.bounding_box()
                    if box and 20 < box['height'] < 100 and 30 < box['width'] < 500:
                        log(f"   Google: {text[:25]}")
                        await elem.click()
                        return True
        except:
            continue
    
    # Method 3: By Google icon
    icon_selectors = [
        'img[src*="google" i]',
        'img[alt*="google" i]',
        'svg[class*="google" i]',
        '[class*="google-icon"]',
    ]
    
    for selector in icon_selectors:
        try:
            icon = await page.query_selector(selector)
            if icon and await icon.is_visible():
                # Click parent button
                try:
                    parent = await icon.evaluate_handle('el => el.closest("button, a, div[role=button]")')
                    if parent:
                        elem = parent.as_element()
                        if elem:
                            log("   Google icon clicked")
                            await elem.click()
                            return True
                except:
                    pass
        except:
            continue
    
    # Method 4: Aggressive search - any button with "google" text
    try:
        buttons = await page.query_selector_all('button, a, div[role="button"]')
        for btn in buttons[:30]:
            try:
                if not await btn.is_visible():
                    continue
                text = await btn.inner_text()
                if text and 'google' in text.lower():
                    box = await btn.bounding_box()
                    if box and box['height'] > 20:
                        log(f"   Found: {text[:25]}")
                        await btn.click()
                        return True
            except:
                continue
    except:
        pass
    
    return False


async def find_login_button_and_click(page, log_callback=None) -> bool:
    """Find and click Login/Sign-in button in navigation"""
    log = log_callback or (lambda x: logger.info(x))
    
    # Method 1: By text
    for text in GoogleAuthConfig.LOGIN_NAV_TEXTS:
        try:
            selectors = [
                f'a:has-text("{text}")',
                f'button:has-text("{text}")',
            ]
            for selector in selectors:
                elem = await page.query_selector(selector)
                if elem and await elem.is_visible():
                    box = await elem.bounding_box()
                    if box and box['height'] > 15:
                        log(f"   Found: {text}")
                        await elem.click()
                        return True
        except:
            continue
    
    # Method 2: By href patterns
    href_selectors = [
        'a[href*="login"]',
        'a[href*="signin"]',
        'a[href*="sign-in"]',
        'a[href*="auth"]',
        'a[href*="account"]',
        '[data-testid*="login"]',
        '[data-testid*="signin"]',
        'button[class*="login" i]',
        'a[class*="login" i]',
    ]
    
    for selector in href_selectors:
        try:
            elem = await page.query_selector(selector)
            if elem and await elem.is_visible():
                log(f"   Found login link")
                await elem.click()
                return True
        except:
            continue
    
    return False


async def is_logged_in(page) -> bool:
    """Check if user appears to be logged in"""
    
    # Check by text indicators
    for text in GoogleAuthConfig.LOGGED_IN_TEXTS:
        try:
            elem = await page.query_selector(f'text="{text}"')
            if elem and await elem.is_visible():
                return True
        except:
            continue
    
    # Check for avatar/profile image patterns
    avatar_selectors = [
        'img[alt*="avatar" i]',
        'img[alt*="profile" i]',
        'img[class*="avatar" i]',
        '[class*="user-avatar"]',
        '[class*="profile-pic"]',
        '[class*="account-icon"]',
        '[class*="user-menu"]',
        '[class*="profile-image"]',
    ]
    
    for selector in avatar_selectors:
        try:
            elem = await page.query_selector(selector)
            if elem and await elem.is_visible():
                return True
        except:
            continue
    
    return False


async def find_google_button(page) -> Optional[Any]:
    """Find Google Sign-In button on page (returns element)"""
    
    # By selector
    for selector in GoogleAuthConfig.GOOGLE_BUTTON_SELECTORS:
        try:
            elem = await page.query_selector(selector)
            if elem and await elem.is_visible():
                return elem
        except:
            continue
    
    # By text
    for text in GoogleAuthConfig.GOOGLE_BUTTON_TEXTS:
        try:
            selector = f'button:has-text("{text}"), a:has-text("{text}"), div[role="button"]:has-text("{text}")'
            elem = await page.query_selector(selector)
            if elem and await elem.is_visible():
                box = await elem.bounding_box()
                if box and 20 < box['height'] < 100:
                    return elem
        except:
            continue
    
    # By Google icon
    icon_selectors = [
        'img[src*="google" i]',
        'img[alt*="google" i]',
        'svg[class*="google" i]',
    ]
    
    for selector in icon_selectors:
        try:
            icon = await page.query_selector(selector)
            if icon and await icon.is_visible():
                # Click parent button
                parent = await icon.evaluate_handle('el => el.closest("button, a, div[role=button]")')
                if parent:
                    elem = parent.as_element()
                    if elem:
                        return elem
        except:
            continue
    
    return None


async def find_login_button(page) -> Optional[Any]:
    """Find Login/Sign-in button in navigation"""
    
    for text in GoogleAuthConfig.LOGIN_NAV_TEXTS:
        try:
            selector = f'a:has-text("{text}"), button:has-text("{text}")'
            elem = await page.query_selector(selector)
            if elem and await elem.is_visible():
                return elem
        except:
            continue
    
    # By href
    href_selectors = [
        'a[href*="login"]',
        'a[href*="signin"]',
        'a[href*="sign-in"]',
        'a[href*="auth"]',
    ]
    
    for selector in href_selectors:
        try:
            elem = await page.query_selector(selector)
            if elem and await elem.is_visible():
                return elem
        except:
            continue
    
    return None
