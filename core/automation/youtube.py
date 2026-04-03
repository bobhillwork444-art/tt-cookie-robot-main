"""
YouTube Activity Mixin for BrowserAutomation
Contains all YouTube-related methods.
"""
import asyncio
import random
import time
import logging
from typing import TYPE_CHECKING

from core.automation.helpers import HumanBehavior, YOUTUBE_SEARCH_WORDS

if TYPE_CHECKING:
    from playwright.async_api import Page

logger = logging.getLogger(__name__)


class YouTubeMixin:
    """Mixin class providing YouTube activity functionality."""
    
    # Type hints for attributes from BrowserAutomation
    page: "Page"
    should_stop: bool
    _youtube_activity_done: bool
    _youtube_queries: list
    _youtube_videos_min: int
    _youtube_videos_max: int
    _youtube_watch_min: int
    _youtube_watch_max: int
    _youtube_like_percent: int
    _youtube_watchlater_percent: int
    
    def log(self, message: str) -> None:
        """Log method - to be overridden by BrowserAutomation."""
        pass
    
    async def _navigate_via_google_search(self, url: str) -> bool:
        """Navigate via Google search - implemented in BrowserAutomation."""
        return False
    
    async def _navigate_direct_in_new_tab(self, url: str) -> bool:
        """Navigate directly in new tab - implemented in BrowserAutomation."""
        return False
    
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
                
                # Click Save button
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
            
            # Click "Watch later"
            watch_later_clicked = await self.page.evaluate('''() => {
                // Method 1: Find by aria-label
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
                
                // Method 3: Find by label class
                const labels = document.querySelectorAll('.yt-list-item-view-model__label');
                for (const label of labels) {
                    if (label.textContent.toLowerCase().includes('watch later')) {
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
