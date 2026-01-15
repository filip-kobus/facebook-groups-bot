import asyncio
import os
import json
import time
import random
from datetime import datetime, timedelta
from playwright.async_api import async_playwright, Page
from typing import Dict, List, Tuple, Optional
from dotenv import load_dotenv
from config import DAYS_BACK, MAX_SCROLLS, THINKING_TIME_SCALE

load_dotenv()

COOKIES_FILE = "cookies.json"


class FacebookScraper:
    """Handles Facebook authentication and post scraping with human-like behavior."""
    
    def __init__(self, days_back: int = DAYS_BACK, max_scrolls: int = MAX_SCROLLS, 
                 thinking_time_scale: int = THINKING_TIME_SCALE):
        """
        Initialize Facebook scraper.
        
        Args:
            days_back: Number of days to look back for posts
            max_scrolls: Maximum number of scrolls per group
            thinking_time_scale: 0-10 scale for thinking time (10=5s, 1=0.5s, 0=0s)
        """
        self.days_back = days_back
        self.max_scrolls = max_scrolls
        self.thinking_time_scale = max(0, min(10, thinking_time_scale))  # Clamp to 0-10
        self.thinking_time = self.thinking_time_scale * 0.5  # Convert scale to seconds
        
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        
    async def _get_thinking_delay(self) -> float:
        """Get thinking time with small random variation."""
        if self.thinking_time == 0:
            return 0
        variation = self.thinking_time * 0.2  # ±20% variation
        return random.uniform(
            max(0, self.thinking_time - variation),
            self.thinking_time + variation
        )
    
    async def thinking_pause(self):
        """Pause for thinking time if scale > 0."""
        delay = await self._get_thinking_delay()
        if delay > 0:
            print(f"⏱️  Thinking... ({delay:.2f}s)")
            await asyncio.sleep(delay)

    async def thinking_pause(self):
        """Pause for thinking time if scale > 0."""
        delay = await self._get_thinking_delay()
        if delay > 0:
            print(f"⏱️  Thinking... ({delay:.2f}s)")
            await asyncio.sleep(delay)

    @staticmethod
    def parse_facebook_date(date_str: str) -> Optional[datetime]:
        """Parse Facebook date string to datetime object."""
        try:
            if "," in date_str:
                date_str = date_str.split(" o ")[0]
            
            months = {
                "stycznia": 1, "lutego": 2, "marca": 3, "kwietnia": 4,
                "maja": 5, "czerwca": 6, "lipca": 7, "sierpnia": 8,
                "września": 9, "października": 10, "listopada": 11, "grudnia": 12,
                "January": 1, "February": 2, "March": 3, "April": 4,
                "May": 5, "June": 6, "July": 7, "August": 8,
                "September": 9, "October": 10, "November": 11, "December": 12
            }
            
            parts = date_str.split()
            day = int(parts[-3])
            month_name = parts[-2]
            year = int(parts[-1])
            
            month = months.get(month_name)
            if month:
                return datetime(year, month, day)
        except:
            pass
        
        return None
    
    def is_post_recent(self, post_date_str: str) -> bool:
        """Check if post is within the specified days_back range."""
        if not post_date_str:
            return True
        
        post_date = self.parse_facebook_date(post_date_str)
        if not post_date:
            return True
        
        cutoff_date = datetime.now() - timedelta(days=self.days_back)
        return post_date >= cutoff_date

        cutoff_date = datetime.now() - timedelta(days=self.days_back)
        return post_date >= cutoff_date

    @staticmethod
    async def random_delay(min_seconds: float = 1.5, max_seconds: float = 4.0):
        """Random delay between actions."""
        await asyncio.sleep(random.uniform(min_seconds, max_seconds))
    
    async def human_like_scroll(self):
        """Perform human-like scrolling on the page."""
        viewport_height = self.page.viewport_size["height"] if self.page.viewport_size else 800
        scroll_amount = random.randint(int(viewport_height * 0.3), int(viewport_height * 0.7))
        
        await self.page.evaluate(f"""
            window.scrollBy({{
                top: {scroll_amount},
                behavior: 'smooth'
            }});
        """)
        await self.random_delay(0.5, 1.5)
    
    async def random_mouse_movement(self):
        """Perform random mouse movements."""
        viewport = self.page.viewport_size
        if viewport:
            x = random.randint(100, viewport["width"] - 100)
            y = random.randint(100, viewport["height"] - 100)
            await self.page.mouse.move(x, y)
            await asyncio.sleep(random.uniform(0.1, 0.3))

            await asyncio.sleep(random.uniform(0.1, 0.3))
    
    async def login(self):
        """Login to Facebook with human-like behavior."""
        await self.page.goto("https://www.facebook.com/login")
        await self.random_delay(2, 4)
        
        try:
            await self.page.get_by_role("button", name="Allow all cookies").click()
            await self.random_delay(1, 2)
        except:
            pass
        
        email_field = self.page.get_by_label("Email or phone number")
        await email_field.click()
        await self.random_delay(0.5, 1)
        
        for char in os.getenv("EMAIL"):
            await email_field.type(char, delay=random.randint(50, 150))
        
        await self.random_delay(0.8, 1.5)
        
        password_field = self.page.get_by_label("Password")
        await password_field.click()
        await self.random_delay(0.5, 1)
        
        for char in os.getenv("PASSWORD"):
            await password_field.type(char, delay=random.randint(50, 150))
        
        await self.random_delay(1, 2)
        await self.page.get_by_role("button", name="Log In").click()
        await self.random_delay(3, 5)
    
    @staticmethod
    def is_authenticated() -> bool:
        """Check if user is already authenticated via cookies."""
        if not os.path.exists(COOKIES_FILE):
            return False
        
        try:
            with open(COOKIES_FILE, "r") as f:
                context = json.load(f)
            
            cookies = context.get("cookies", [])
            c_user = None
            xs = None
            
            for cookie in cookies:
                if cookie["name"] == "c_user":
                    c_user = cookie
                elif cookie["name"] == "xs":
                    xs = cookie
            
            if not c_user or not xs:
                return False
            
            current_time = time.time()
            if c_user["expires"] < current_time or xs["expires"] < current_time:
                return False
            
            return True
        except Exception:
            return False
    
    async def confirm_cookies(self):
        """Confirm cookies if popup appears."""
        try:
            await self.page.get_by_role("button", name="Allow all cookies").click(timeout=5000)
        except:
            pass
    
    async def close_notification_popup(self):
        """Close notification popup if it appears."""
        try:
            close_button = self.page.get_by_role("button", name="Close")
            await close_button.wait_for(state="visible", timeout=10000)
            await self.random_delay(0.5, 1.5)
            await close_button.click()
            await self.random_delay(1, 2)
        except:
            pass

            pass

    async def init_browser(self) -> Tuple:
        """Initialize browser and authenticate."""
        self.playwright = await async_playwright().start()
        viewport_width = random.randint(1366, 1920)
        viewport_height = random.randint(768, 1080)
        
        self.browser = await self.playwright.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process'
            ]
        )
        
        is_auth = self.is_authenticated()
        
        context_options = {
            "viewport": {"width": viewport_width, "height": viewport_height},
            "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "locale": "en-US",
            "timezone_id": "Europe/Warsaw",
            "permissions": ["geolocation"],
            "geolocation": {"latitude": 52.2297, "longitude": 21.0122},
        }
        
        if is_auth:
            context_options["storage_state"] = COOKIES_FILE
        
        self.context = await self.browser.new_context(**context_options)
        
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            window.chrome = {
                runtime: {}
            };
        """)
        
        self.page = await self.context.new_page()
        
        if not is_auth:
            await self.login()
            await self.confirm_cookies()
        
        return self.playwright, self.browser, self.context, self.page

        return self.playwright, self.browser, self.context, self.page

    async def scrape_posts(self, group_id: str) -> List[Dict]:
        """Scrape posts from a Facebook group."""
        await self.page.goto(f"https://www.facebook.com/groups/{group_id}/?sorting_setting=CHRONOLOGICAL")
        await self.random_delay(3, 5)
        await self.close_notification_popup()
        
        await self.random_mouse_movement()
        await self.human_like_scroll()
        
        posts_data = []
        seen_ids = set()
        should_continue = True
        scroll_count = 0
        
        await self.page.wait_for_selector('[role="feed"] [aria-posinset]', timeout=15000)
        await self.random_delay(2, 3)
        
        while should_continue and scroll_count < self.max_scrolls:
            posts = await self.page.locator('[role="feed"] [aria-posinset]').all()
            
            new_posts_found = False
        
            for i, post in enumerate(posts):
                await self.random_delay(0.3, 0.8)
                
                # Add thinking pause when configured
                await self.thinking_pause()
                    
                try:
                    author_locator = post.locator('h2').first
                    await author_locator.scroll_into_view_if_needed(timeout=5000)
                    await self.random_delay(0.2, 0.5)
                    author_name = await author_locator.inner_text()
                except:
                    continue
                
                if "Anonymous" in author_name or "Anonimowy" in author_name:
                    continue
                
                text_locator = post.locator('[data-ad-rendering-role="story_message"]')
                if not await text_locator.count():
                    continue
                
                post_text = await text_locator.inner_text()
                if "See More" in post_text or "See more" in post_text:
                    try:
                        see_more = post.locator('[role="button"]:has-text("See more")')
                        await see_more.scroll_into_view_if_needed(timeout=3000)
                        await self.random_delay(0.5, 1.2)
                        await see_more.click(timeout=3000)
                        await self.random_delay(0.8, 1.5)
                        post_text = await text_locator.inner_text()
                    except:
                        pass
                
                try:
                    links = await post.locator('a[attributionsrc^="/privacy_sandbox/"]').all()
                    participant_anchor_link = await links[0].get_attribute("href", timeout=5000)
                    participant_id = participant_anchor_link.split("user/")[1].split("/")[0]
                except:
                    participant_id = "unknown"
                
                post_id = f"{group_id}_{participant_id}_{i}"
                if post_id in seen_ids:
                    continue
                
                post_date = None
                try:
                    candidates = links[3:5]
                    for date_link in candidates:
                        await self.random_delay(0.3, 0.7)
                        await date_link.hover()
                        tooltip = self.page.locator('[role="tooltip"]')
                        try:
                            await tooltip.wait_for(state="visible", timeout=2000)
                            post_date = await tooltip.inner_text()
                            await self.random_delay(0.2, 0.5)
                            break
                        except:
                            continue
                except:
                    pass
                
                if not self.is_post_recent(post_date):
                    print(f"\n⏹️  Reached posts older than {self.days_back} days, stopping...")
                    should_continue = False
                    break
                
                seen_ids.add(post_id)
                new_posts_found = True
                
                print(f"\n{'─'*80}")
                print(f"📝 POST #{len(posts_data) + 1}")
                print(f"👤 Author: {author_name}")
                print(f"📅 Date: {post_date or 'N/A'}")
                print(f"💬 Content:\n{post_text[:300]}{'...' if len(post_text) > 300 else ''}")
                print(f"{'─'*80}")
                
                posts_data.append({
                    "id": post_id,
                    "author": author_name,
                    "user_id": participant_id,
                    "content": post_text,
                    "date": post_date,
                    "group_id": group_id
                })
            
            if not should_continue:
                break
            
            if new_posts_found:
                await self.human_like_scroll()
                await self.random_delay(2, 4)
                scroll_count += 1
            else:
                await self.human_like_scroll()
                await self.random_delay(2, 4)
                scroll_count += 1
        
        return posts_data
    
    async def save_cookies(self):
        """Save authentication cookies."""
        if self.context:
            await self.context.storage_state(path=COOKIES_FILE)
    
    async def cleanup(self):
        """Cleanup browser resources."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

