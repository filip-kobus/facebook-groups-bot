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
from src.config import MAX_POSTS_TO_SCAN, THINKING_TIME_SCALE, USERS_DIR

load_dotenv()


class FacebookScraper:
    
    def __init__(self, user: str = "scraper", max_posts_to_scan: int = None):
        self.user_dir = os.path.join(USERS_DIR, user)
        os.makedirs(self.user_dir, exist_ok=True)
        self.max_posts_to_scan = max_posts_to_scan if max_posts_to_scan is not None else MAX_POSTS_TO_SCAN
        self.thinking_time_scale = max(0, min(10, THINKING_TIME_SCALE))
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

    async def is_logged_in(self) -> bool:
        """Check if user is logged in by looking for profile icon."""
        cookies = await self.browser.cookies("https://www.facebook.com")
    
        for cookie in cookies:
            if cookie['name'] == 'c_user':
                print(f"Znaleziono sesję dla użytkownika ID: {cookie['value']}")
                return True
        return False

    async def init_browser(self) -> Tuple:
        """Initialize browser and authenticate."""
        self.playwright = await async_playwright().start()

        self.browser = await self.playwright.chromium.launch_persistent_context(
            headless=False,
            channel="chrome",
            user_data_dir=self.user_dir,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process'
            ],
        )

        self.page = await self.browser.new_page()

        if not await self.is_logged_in():
            input("Nie znaleziono aktywnej sesji. Zaloguj się ręcznie i naciśnij Enter...")

    async def get_message_box(self, user_id: str):
        """Open Facebook Messenger."""
        await self.page.goto(f"https://www.facebook.com//{user_id}")
        await self.random_delay(2, 4)

        try:
            close_buttons = self.page.locator('[aria-label*="Close" i]')
            count = await close_buttons.count()
            if count > 0:
                for i in range(count):
                    await close_buttons.nth(i).click()
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

    async def _extract_author_name(self, post) -> Optional[str]:
        """Extract author name from a post."""
        author_locator = post.locator('b').first
        try:
            await author_locator.scroll_into_view_if_needed(timeout=1000)
            await author_locator.is_visible(timeout=1000)
            await self.random_delay(1, 2)
            author_name = await author_locator.inner_text(timeout=1000)
            
            if "Anonymous" in author_name or "Anonimowy" in author_name:
                logger.debug("Skipping anonymous post")
                return None
            
            return author_name
        except Exception as e:
            logger.debug(f"Failed to extract author name: {e}")
            return None

    async def _extract_user_id(self, post) -> Optional[str]:
        """Extract user ID from a post."""
        try:
            available_links = await post.locator('a[attributionsrc^="/privacy_sandbox/"]').all()
            if not available_links:
                return None
            
            await self.random_delay(0.2, 0.5)
            participant_anchor_link = await available_links[0].get_attribute("href", timeout=1000)
            participant_id = participant_anchor_link.split("user/")[1].split("/")[0]
            return participant_id
        except Exception as e:
            logger.debug(f"Failed to extract user ID: {e}")
            return None

    async def _extract_post_date(self, post) -> Optional[str]:
        """Extract post date by hovering over links and reading tooltips."""
        try:
            available_links = await post.locator('a[attributionsrc^="/privacy_sandbox/"]').all()
            
            for link in available_links[1:5]:
                try:
                    if not await link.is_visible():
                        continue
                    
                    await self.random_delay(0.1, 0.7)
                    await link.hover(timeout=1000)
                    
                    tooltip = self.page.locator('[role="tooltip"]')
                    tooltip_text = await tooltip.inner_text(timeout=1000)
                    await self.random_delay(0.5, 1.0)
                    
                    has_time = re.search(r'\d{1,2}:\d{2}', tooltip_text)
                    has_day = re.search(r'\b\d{1,2}\b', tooltip_text)
                    if has_time or has_day:
                        logger.debug(f"Found tooltip with date/time: {tooltip_text}")
                        return tooltip_text
                    else:
                        logger.debug(f"Tooltip does not contain date/time: {tooltip_text}")
                except Exception as e:
                    logger.debug(f"Failed to hover or get tooltip: {str(e)}")
                    continue
        except Exception as e:
            logger.debug(f"Failed to extract post date: {e}")
        
        return None

    async def _extract_post_content(self, post) -> Optional[str]:
        """Extract post content and expand 'See more' if needed."""
        try:
            text_locator = post.locator('[data-ad-rendering-role="story_message"]')
            if not await text_locator.count():
                logger.debug("No text content found in post")
                return None
            
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
            
            return post_text
        except Exception as e:
            logger.debug(f"Failed to extract post content: {e}")
            return None

    def _should_stop_for_old_post(self, parsed_date: Optional[datetime], 
                                   latest_post_date: Optional[datetime], 
                                   old_posts_streak: int) -> Tuple[bool, int]:
        """Check if scraping should stop due to old posts. Returns (should_stop, new_streak)."""
        if not parsed_date or not latest_post_date:
            return False, 0
        
        if parsed_date < latest_post_date:
            old_posts_streak += 1
            logger.debug(f"Post is older than latest in DB ({latest_post_date}), streak: {old_posts_streak}/3")
            if old_posts_streak >= 3:
                logger.debug(f"Found 3 old posts in a row, stopping")
                return True, old_posts_streak
            return False, old_posts_streak
        
        return False, 0

    def _print_post_info(self, post_number: int, author_name: str, date: Optional[str], content: str):
        """Print formatted post information."""
        print(f"\n{'─'*80}")
        print(f"📝 POST #{post_number}")
        print(f"👤 Author: {author_name}")
        print(f"📅 Date: {date or 'N/A'}")
        print(f"💬 Content:\n{content[:300]}{'...' if len(content) > 300 else ''}")

    async def scrape_posts(self, group_id: str, latest_post_date: Optional[datetime] = None) -> List[Dict]:
        """Scrape posts from a Facebook group."""
        await self.page.goto(f"https://www.facebook.com/groups/{group_id}/?sorting_setting=CHRONOLOGICAL")
        await self.random_delay(1, 2)
        await self.close_notification_popup()

        try:
            await self.page.wait_for_selector('[role="feed"] [aria-posinset]', timeout=3000)
        except Exception as e:
            logger.debug(f"Timeout waiting for posts to load: {e}")
        
        await self.human_like_scroll()
        await self.random_delay(1, 2)
        posts = await self.page.locator('[role="feed"] [aria-posinset]').all()
        number_of_posts = len(posts)
        logger.debug(f"Found {number_of_posts} total posts in DOM")
        
        current_index = 0
        scraped_posts = 0
        dane_z_postu = []
        old_posts_streak = 0
        no_new_posts_streak = 0
        MAX_NO_NEW_POSTS_STREAK = 3

        try:
            while True:
                # Scroll and refresh posts list if near the end
                if current_index >= number_of_posts - 2:
                    prev_count = number_of_posts
                    await self.human_like_scroll()
                    await self.random_delay(1, 2)
                    posts = await self.page.locator('[role="feed"] [aria-posinset]').all()
                    number_of_posts = len(posts)
                    logger.debug(f"Found {number_of_posts} total posts in DOM")

                    if number_of_posts <= prev_count:
                        no_new_posts_streak += 1
                        logger.warning(f"No new posts loaded after scroll ({no_new_posts_streak}/{MAX_NO_NEW_POSTS_STREAK})")
                        if no_new_posts_streak >= MAX_NO_NEW_POSTS_STREAK:
                            logger.warning("Facebook stopped loading new posts (scroll blocked?), moving on.")
                            break
                    else:
                        no_new_posts_streak = 0

                    if current_index >= number_of_posts:
                        logger.warning("current_index beyond post list, stopping.")
                        break

                await self.random_delay(1, 2)
                post = posts[current_index]
                
                # Scroll to post
                try:
                    await post.is_visible(timeout=1000)
                    await post.scroll_into_view_if_needed(timeout=1000)
                except:
                    logger.debug("Failed to scroll to post, skipping")
                    current_index += 1
                    continue

                # Extract author name
                author_name = await self._extract_author_name(post)
                if not author_name:
                    current_index += 1
                    continue

                # Extract user ID
                participant_id = await self._extract_user_id(post)
                if not participant_id:
                    logger.debug("Failed to extract user ID, skipping")
                    current_index += 1
                    continue

                # Extract post date
                data_postu = await self._extract_post_date(post)
                
                # Check if post is too old
                if data_postu:
                    parsed_date = self.parse_facebook_date(data_postu)
                    should_stop, old_posts_streak = self._should_stop_for_old_post(
                        parsed_date, latest_post_date, old_posts_streak
                    )
                    if should_stop:
                        break
                    if old_posts_streak > 0:
                        current_index += 1
                        continue

                # Extract post content
                await post.scroll_into_view_if_needed(timeout=1000)
                await self.random_delay(0.2, 0.5)
                logger.debug(f"Processing post at index {current_index}")
                
                post_text = await self._extract_post_content(post)
                if not post_text:
                    current_index += 1
                    continue

                # Print post info
                self._print_post_info(len(dane_z_postu) + 1, author_name, data_postu, post_text)

                # Add to results
                dane_z_postu.append({
                    "id": f"{group_id}_{participant_id}_{int(time.time())}",
                    "author": author_name,
                    "user_id": participant_id,
                    "content": post_text,
                    "date": data_postu,
                    "group_id": group_id
                })

                current_index += 1
                scraped_posts += 1
                
                # Check if reached max posts
                if scraped_posts >= self.max_posts_to_scan:
                    logger.debug(f"Reached max posts to scan: {self.max_posts_to_scan}, stopping")
                    break

        except Exception as e:
            logger.error(f"Error during scraping: {e}. Returning {len(dane_z_postu)} posts collected so far.")
        
        return dane_z_postu
    
    async def cleanup(self):
        """Cleanup browser resources."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

