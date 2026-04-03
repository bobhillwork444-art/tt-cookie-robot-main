"""
Gmail Activity Mixin for BrowserAutomation
Contains all Gmail-related methods.
"""
import asyncio
import random
import time
import logging
from typing import TYPE_CHECKING

from core.automation.helpers import HumanBehavior

if TYPE_CHECKING:
    from playwright.async_api import Page, BrowserContext

logger = logging.getLogger(__name__)


class GmailMixin:
    """Mixin class providing Gmail activity functionality."""
    
    # Type hints for attributes from BrowserAutomation
    page: "Page"
    context: "BrowserContext"
    should_stop: bool
    _gmail_promo_spam_percent: int
    _gmail_click_links: bool
    _gmail_link_clicked: bool
    
    def log(self, message: str) -> None:
        """Log method - to be overridden by BrowserAutomation."""
        pass
    
    async def mute_page(self) -> None:
        """Mute page audio - implemented in BrowserAutomation."""
        pass
    
    async def _quick_gmail_check(self, read_percent: int, read_time_min: int, read_time_max: int):
        """Quick Gmail check - visit inbox and read a few emails."""
        # Calculate random read time from range
        read_time = random.randint(read_time_min, read_time_max)
        
        try:
            try:
                await self.page.goto("https://mail.google.com/mail/u/0/#inbox", 
                                     wait_until="domcontentloaded", timeout=30000)
            except Exception as nav_err:
                self.log(f"   ⚠️ Gmail navigation error: {str(nav_err)[:40]}")
                return
            
            await HumanBehavior.random_delay(2, 3)
            await self.mute_page()
            
            # Wait for inbox
            try:
                await self.page.wait_for_selector('tr.zA', timeout=10000)
            except:
                self.log("   Gmail not loaded")
                return
            
            # Read a few emails
            email_rows = await self.page.query_selector_all('tr.zA')
            if email_rows:
                # Read 1-2 random emails
                emails_to_read = min(random.randint(1, 2), len(email_rows))
                for i in range(emails_to_read):
                    try:
                        await email_rows[i].click()
                        await HumanBehavior.random_delay(read_time * 0.3, read_time * 0.5)
                        await HumanBehavior.smooth_scroll(self.page)
                        await HumanBehavior.random_delay(read_time * 0.3, read_time * 0.5)
                        # Go back
                        await self.page.keyboard.press("u")
                        await HumanBehavior.random_delay(1, 2)
                        email_rows = await self.page.query_selector_all('tr.zA')
                    except:
                        break
            
            self.log(f"   ✓ Quick Gmail check done")
            
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
            try:
                await self.page.goto("https://mail.google.com/mail/u/0/#inbox", 
                                     wait_until="domcontentloaded", timeout=30000)
            except Exception as nav_err:
                self.log(f"   ⚠️ Gmail navigation error: {str(nav_err)[:40]}")
                return
            
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
                extra_folder = random.choice([folders[1], folders[2]])
                folders_to_visit.append(extra_folder)
            
            for folder_id, folder_url, folder_name in folders_to_visit:
                if self.should_stop:
                    break
                
                self.log(f"\n{folder_name} - checking...")
                
                # Navigate directly via URL
                try:
                    await self.page.goto(folder_url, wait_until="domcontentloaded", timeout=20000)
                except Exception as nav_err:
                    self.log(f"   ⚠️ Folder navigation error: {str(nav_err)[:40]}")
                    continue
                    
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
        """
        try:
            # Find links in email body
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
            
            # Filter valid links
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
                    scroll_amount = random.randint(100, 400)
                    await new_tab.evaluate(f'window.scrollBy(0, {scroll_amount})')
                    await asyncio.sleep(random.uniform(1, 3))
                    
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
                
                await self.page.go_back()
                await asyncio.sleep(1)
            
            return True
            
        except Exception as e:
            logger.debug(f"Click email link error: {e}")
            return False
    
    async def _read_email_content(self, read_time: int):
        """
        Simulate human-like reading of email content with smooth scrolling.
        """
        actual_read_time = random.randint(int(read_time * 0.7), int(read_time * 1.3))
        start_time = time.time()
        
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
        """
        steps = random.randint(4, 8)
        step_amount = total_amount / steps
        
        for _ in range(steps):
            try:
                await self.page.evaluate(f"""
                    (() => {{
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
        """
        try:
            # Method 1: Try clicking Gmail's back button
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
                        try:
                            await self.page.wait_for_selector('tr.zA', timeout=5000)
                            return
                        except:
                            pass
                except:
                    continue
            
            # Method 2: Keyboard shortcut
            try:
                await self.page.keyboard.press("u")
                await HumanBehavior.random_delay(1, 1.5)
                await self.page.wait_for_selector('tr.zA', timeout=5000)
                return
            except:
                pass
            
            # Method 3: Direct URL navigation
            await self.page.goto(folder_url, wait_until="domcontentloaded", timeout=15000)
            await HumanBehavior.random_delay(1, 2)
            
        except:
            await self.page.goto(folder_url, wait_until="domcontentloaded", timeout=15000)
