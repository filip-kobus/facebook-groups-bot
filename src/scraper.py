import asyncio
import os
import json
import time
import random
from datetime import datetime, timedelta
from playwright.async_api import async_playwright, Page
import re
from typing import Dict, List, Tuple, Optional
from dotenv import load_dotenv
from loguru import logger
from config import HOURS_BACK, MAX_POSTS_TO_SCAN, THINKING_TIME_SCALE

load_dotenv()

COOKIES_FILE = "cookies.json"


class FacebookScraper:
    """Handles Facebook authentication and post scraping with human-like behavior."""
    
    def __init__(self):
        """
        Initialize Facebook scraper.
        """
        self.max_posts_to_scan = MAX_POSTS_TO_SCAN
        self.thinking_time_scale = max(0, min(10, THINKING_TIME_SCALE))
        self.hours_back = HOURS_BACK
        
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

    @staticmethod
    def parse_facebook_date(date_str: str) -> Optional[datetime]:
        """Parse Facebook date string to datetime object."""
        try:
            time_str = None
            if " at " in date_str:
                date_part, time_str = date_str.split(" at ")
                date_str = date_part
            elif " o " in date_str:
                date_part, time_str = date_str.split(" o ")
                date_str = date_part
            
            if "," in date_str:
                date_str = ",".join(date_str.split(",")[1:]).strip()
            
            months = {
                "stycznia": 1, "lutego": 2, "marca": 3, "kwietnia": 4,
                "maja": 5, "czerwca": 6, "lipca": 7, "sierpnia": 8,
                "września": 9, "października": 10, "listopada": 11, "grudnia": 12,
                "January": 1, "February": 2, "March": 3, "April": 4,
                "May": 5, "June": 6, "July": 7, "August": 8,
                "September": 9, "October": 10, "November": 11, "December": 12
            }
            
            parts = date_str.replace(",", "").split()
            
            if len(parts) < 3:
                return None
            
            first_part = parts[0]
            if first_part in months:
                month_name = parts[0]
                day = int(parts[1])
                year = int(parts[2])
            else:
                day = int(parts[0])
                month_name = parts[1]
                year = int(parts[2])
            
            month = months.get(month_name)
            if not month:
                return None
            
            hour, minute = 0, 0
            if time_str:
                time_match = re.search(r'(\d{1,2}):(\d{2})\s*(AM|PM)?', time_str, re.IGNORECASE)
                if time_match:
                    hour = int(time_match.group(1))
                    minute = int(time_match.group(2))
                    am_pm = time_match.group(3)
                    
                    if am_pm:
                        if am_pm.upper() == 'PM' and hour != 12:
                            hour += 12
                        elif am_pm.upper() == 'AM' and hour == 12:
                            hour = 0
            
            return datetime(year, month, day, hour, minute)
        except Exception as e:
            logger.debug(f"Failed to parse Facebook date '{date_str}': {e}")
        
        return None
    
    def is_post_recent(self, post_date_str: str) -> bool:
        """Check if post is within the specified hours_back range."""
        if not post_date_str:
            return True
        
        post_date = self.parse_facebook_date(post_date_str)
        if not post_date:
            return True
        
        cutoff_time = datetime.now() - timedelta(hours=self.hours_back)
        return post_date >= cutoff_time

    async def random_delay(self, min_seconds: float = 1.5, max_seconds: float = 4.0):
        """Random delay between actions, scaled by thinking_time_scale."""       
        scaled_min = min_seconds * self.thinking_time_scale
        scaled_max = max_seconds * self.thinking_time_scale
        await asyncio.sleep(random.uniform(scaled_min, scaled_max))
    
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
            await self.random_delay(0.1, 0.3)
    
    async def login(self):
        """Login to Facebook with human-like behavior."""
        await self.page.goto("https://www.facebook.com/login")
        await self.random_delay(2, 4)
        
        try:
            await self.page.get_by_role("button", name="Allow all cookies").click()
            await self.random_delay(1, 2)
        except Exception as e:
            logger.debug(f"No cookie consent button found or failed to click: {e}")
        
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
        except Exception as e:
            logger.warning(f"Failed to validate authentication cookies: {e}")
            return False
    
    async def confirm_cookies(self):
        """Confirm cookies if popup appears."""
        try:
            await self.page.get_by_role("button", name="Allow all cookies").click(timeout=5000)
        except Exception as e:
            logger.debug(f"No cookie popup to confirm: {e}")
    
    async def close_notification_popup(self):
        """Close notification popup if it appears."""
        try:
            close_button = self.page.get_by_role("button", name="Close")
            await close_button.wait_for(state="visible", timeout=2000)
            await self.random_delay(0.5, 1.5)
            await close_button.click()
            await self.random_delay(1, 2)
        except Exception as e:
            logger.debug(f"No notification popup to close: {e}")

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
            await self.save_cookies()
            logger.info("Cookies saved after login")
        
        return self.playwright, self.browser, self.context, self.page

    async def get_message_box(self, user_id: str):
        """Open Facebook Messenger."""
        await self.page.goto(f"https://www.facebook.com//{user_id}")
        await self.random_delay(2, 4)

        # Delikatny scroll i ruch myszką do przycisku "Message"
        try:
            await self.page.get_by_label("Close").click()
            await self.random_delay(1, 2)
        except Exception as e:
            pass
        await self.page.mouse.move(200, 300)
        await self.random_delay(0.2, 0.5)
        await self.page.mouse.move(400, 350)
        await self.random_delay(0.2, 0.5)
        await self.page.mouse.wheel(0, 150)
        await self.random_delay(0.2, 0.5)

        await self.page.get_by_text("Message", exact=True).scroll_into_view_if_needed(timeout=2000)
        await self.random_delay(0.2, 0.5)
        await self.page.get_by_text("Message", exact=True).hover()
        await self.random_delay(0.2, 0.5)
        await self.page.get_by_text("Message", exact=True).click()
        
        await self.random_delay(1, 2)

        # Delikatny scroll i ruch myszką do pola tekstowego
        message_box = self.page.locator('div[role="textbox"][aria-label="Message"]')
        await message_box.scroll_into_view_if_needed(timeout=2000)
        await self.random_delay(0.2, 0.5)
        box_rect = await message_box.bounding_box()
        if box_rect:
            await self.page.mouse.move(box_rect["x"] + 10, box_rect["y"] + 10)
            await self.random_delay(0.2, 0.5)
        await message_box.click()
        
        await self.random_delay(1, 2)
        
        return message_box

    async def send_messages(self, user_id: str, messages: List[str]) -> bool:
        """Send multiple messages to a user."""
        message_box = await self.get_message_box(user_id)
        for message in messages:
            success = await self.send_message(message_box, message)
            if not success:
                return False
            await self.random_delay(1, 3)
        return True

    async def send_message(self, message_box, message: str) -> bool:
        """Send a message to a user."""
        for char in message:
            if char == "\n":
                await message_box.press("Shift+Enter")
                await self.random_delay(0.1, 0.3)
            else:
                await message_box.type(char, delay=random.randint(50, 150))

        
        await self.random_delay(1, 2)
        await message_box.press("Enter")
        await self.random_delay(2, 3)
        
        return True

    async def is_x_hours_older(self, post_date_str: str, hours: int) -> bool:
        """Check if post is older than specified hours."""
        if not post_date_str:
            return False
        
        post_date = self.parse_facebook_date(post_date_str)
        if not post_date:
            return False
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return post_date < cutoff_time

    async def scrape_posts(self, group_id: str) -> List[Dict]:
        """Test scraping with dynamic list growth using while loop."""
        await self.page.goto(f"https://www.facebook.com/groups/{group_id}/?sorting_setting=CHRONOLOGICAL")
        await self.random_delay(1, 2)
        await self.close_notification_popup()

        try:
            await self.page.wait_for_selector('[role="feed"] [aria-posinset]', timeout=3000)
        except Exception as e:
            logger.debug(f"Timeout waiting for posts to load: {e}")
        
        await self.human_like_scroll()
        await self.random_delay(2, 3)
        posts = await self.page.locator('[role="feed"] [aria-posinset]').all()
        number_of_posts = len(posts)
        logger.debug(f"Found {number_of_posts} total posts in DOM")
        current_index = 0
        scraped_posts = 0
        data_postu = None
        dane_z_postu = []
        old_posts_streak = 0

        is_recent = self.is_post_recent(data_postu)
        while is_recent or old_posts_streak < 3:
            if current_index >= number_of_posts - 2:
                await self.human_like_scroll()
                await self.random_delay(1, 2)
                posts = await self.page.locator('[role="feed"] [aria-posinset]').all()
                number_of_posts = len(posts)
                logger.debug(f"Found {number_of_posts} total posts in DOM")

            await self.random_delay(2, 4)
            post = posts[current_index]
            
            try:
                await post.is_visible(timeout=1000)
                await post.scroll_into_view_if_needed(timeout=1000)
            except:
                logger.debug("Failed to scroll to post, skipping")
                current_index += 1
                continue              
            author_locator = post.locator('b').first
            try:
                await author_locator.scroll_into_view_if_needed(timeout=1000)
                await author_locator.is_visible(timeout=1000)
                await self.random_delay(1, 2)
                author_name = await author_locator.inner_text(timeout=1000)
            except Exception as e:
                logger.debug(f"Failed to extract author name: {e}, skipping post")
                current_index += 1
                continue

            if "Anonymous" in author_name or "Anonimowy" in author_name:
                logger.debug("Skipping anonymous post")
                current_index += 1
                continue

            await author_locator.scroll_into_view_if_needed(timeout=1000)
            available_links = await post.locator('a[attributionsrc^="/privacy_sandbox/"]').all()
            await self.random_delay(0.2, 0.5)
            participant_anchor_link = await available_links[0].get_attribute("href", timeout=1000)
            participant_id = participant_anchor_link.split("user/")[1].split("/")[0]

            for link in available_links[1:5]:
                try:
                    if not await link.is_visible():
                        continue
                    
                    # await link.scroll_into_view_if_needed(timeout=1000)
                    await self.random_delay(1.3, 1.7)
                    await link.hover(timeout=1000)
                    
                    tooltip = self.page.locator('[role="tooltip"]')
                    tooltip_text = await tooltip.inner_text(timeout=1000)
                    await self.random_delay(0.5, 1.0)
                    
                    has_time = re.search(r'\d{1,2}:\d{2}', tooltip_text)
                    has_day = re.search(r'\b\d{1,2}\b', tooltip_text) 
                    if has_time or has_day:
                        data_postu = tooltip_text
                        logger.debug(f"Found tooltip with date/time: {tooltip_text}")
                        break
                    else:                    
                        logger.debug(f"Tooltip does not contain date/time: {tooltip_text}")
                except Exception as e:
                    logger.debug(f"Failed to hover or get tooltip: {str(e)}")
                    continue
            
            if data_postu:
                is_recent = self.is_post_recent(data_postu)
                if not is_recent:
                    old_posts_streak += 1
                    logger.debug(f"Post date {data_postu} is older than {self.hours_back} hours, streak: {old_posts_streak}/3")
                    if old_posts_streak >= 3:
                        logger.debug(f"Found 3 old posts in a row, stopping")
                        break
                    current_index += 1
                    continue
                else:
                    old_posts_streak = 0
                
            await post.scroll_into_view_if_needed(timeout=1000)
            await self.random_delay(0.2, 0.5)
            logger.debug(f"Processing initial post at index {current_index}")
            
            text_locator = post.locator('[data-ad-rendering-role="story_message"]')
            if not await text_locator.count():
                logger.debug("No text content found in post, skipping")
                current_index += 1
                continue
            
            post_text = await text_locator.first.inner_text()
            expand_name = "See more" if "See more" in post_text else "Zobacz więcej"

            if expand_name.lower() in post_text.lower():
                try:
                    logger.debug("Expanding 'See more' content")
                    see_more = post.locator(f'[role="button"]:has-text("{expand_name}")')
                    await see_more.scroll_into_view_if_needed(timeout=1000)
                    await self.random_delay(0.5, 1.2)
                    await see_more.click(timeout=3000)
                    await self.random_delay(0.8, 1.5)
                    post_text = await text_locator.inner_text()
                    if len(post_text) > 3000:
                        await self.human_like_scroll()
                except Exception as e:
                    logger.debug(f"Failed to click 'See more' button: {e}")

            current_index += 1

            print(f"\n{'─'*80}")
            print(f"📝 POST #{len(dane_z_postu) + 1}")
            print(f"👤 Author: {author_name}")
            print(f"📅 Date: {data_postu or 'N/A'}")
            print(f"💬 Content:\n{post_text[:300]}{'...' if len(post_text) > 300 else ''}")

            scraped_posts += 1
            if scraped_posts >= self.max_posts_to_scan:
                logger.debug(f"Reached max posts to scan: {self.max_posts_to_scan}, stopping")
                break

            dane_z_postu.append({
                "id": f"{group_id}_{participant_id}_{current_index}",
                "author": author_name,
                "user_id": participant_id,
                "content": post_text,
                "date": data_postu,
                "group_id": group_id
            })
        
        return dane_z_postu
    
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

