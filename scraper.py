import asyncio
import os
import json
import time
import random
from playwright.async_api import async_playwright, Page
from dotenv import load_dotenv

load_dotenv()

COOKIES_FILE = "cookies.json"

async def random_delay(min_seconds=1.5, max_seconds=4.0):
    await asyncio.sleep(random.uniform(min_seconds, max_seconds))

async def human_like_scroll(page: Page):
    viewport_height = page.viewport_size["height"] if page.viewport_size else 800
    scroll_amount = random.randint(int(viewport_height * 0.3), int(viewport_height * 0.7))
    
    await page.evaluate(f"""
        window.scrollBy({{
            top: {scroll_amount},
            behavior: 'smooth'
        }});
    """)
    await random_delay(0.5, 1.5)

async def random_mouse_movement(page: Page):
    viewport = page.viewport_size
    if viewport:
        x = random.randint(100, viewport["width"] - 100)
        y = random.randint(100, viewport["height"] - 100)
        await page.mouse.move(x, y)
        await asyncio.sleep(random.uniform(0.1, 0.3))

async def login(page: Page):
    await page.goto("https://www.facebook.com/login")
    await random_delay(2, 4)
    
    try:
        await page.get_by_role("button", name="Allow all cookies").click()
        await random_delay(1, 2)
    except:
        pass
    
    email_field = page.get_by_label("Email or phone number")
    await email_field.click()
    await random_delay(0.5, 1)
    
    for char in os.getenv("EMAIL"):
        await email_field.type(char, delay=random.randint(50, 150))
    
    await random_delay(0.8, 1.5)
    
    password_field = page.get_by_label("Password")
    await password_field.click()
    await random_delay(0.5, 1)
    
    for char in os.getenv("PASSWORD"):
        await password_field.type(char, delay=random.randint(50, 150))
    
    await random_delay(1, 2)
    await page.get_by_role("button", name="Log In").click()
    await random_delay(3, 5)

def is_authenticated():
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

async def confirm_cookies(page: Page):
    try:
        await page.get_by_role("button", name="Allow all cookies").click(timeout=5000)
    except:
        pass

async def close_notification_popup(page: Page):
    try:
        close_button = page.get_by_role("button", name="Close")
        await close_button.wait_for(state="visible", timeout=10000)
        await random_delay(0.5, 1.5)
        await close_button.click()
        await random_delay(1, 2)
    except:
        pass

async def scrape_posts(group_id: str, max_posts: int = 50):
    async with async_playwright() as p:
        viewport_width = random.randint(1366, 1920)
        viewport_height = random.randint(768, 1080)
        
        browser = await p.chromium.launch(
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
        
        is_auth = is_authenticated()
        
        context_options = {
            "viewport": {"width": viewport_width, "height": viewport_height},
            "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "locale": "pl-PL",
            "timezone_id": "Europe/Warsaw",
            "permissions": ["geolocation"],
            "geolocation": {"latitude": 52.2297, "longitude": 21.0122},
        }
        
        if is_auth:
            context_options["storage_state"] = COOKIES_FILE
        
        context = await browser.new_context(**context_options)
        
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            window.chrome = {
                runtime: {}
            };
        """)
        
        page = await context.new_page()
        
        if not is_auth:
            await login(page)
            await confirm_cookies(page)
        
        await page.goto(f"https://www.facebook.com/groups/{group_id}/?sorting_setting=CHRONOLOGICAL")
        await random_delay(3, 5)
        await close_notification_popup(page)
        
        await random_mouse_movement(page)
        await human_like_scroll(page)
        
        posts_data = []
        
        await page.wait_for_selector('[role="feed"] [aria-posinset]', timeout=15000)
        await random_delay(2, 3)
        posts = await page.locator('[role="feed"] [aria-posinset]').all()
        
        for i, post in enumerate(posts[:max_posts]):
            if i >= max_posts:
                break
            
            if i > 0 and i % 5 == 0:
                await human_like_scroll(page)
                await random_delay(2, 4)
                await random_mouse_movement(page)
            
            await random_delay(0.5, 1.5)
                
            try:
                author_locator = post.locator('h2').first
                await author_locator.scroll_into_view_if_needed(timeout=5000)
                await random_delay(0.3, 0.8)
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
                    await random_delay(0.5, 1.2)
                    await see_more.click(timeout=3000)
                    await random_delay(0.8, 1.5)
                    post_text = await text_locator.inner_text()
                except:
                    pass
            
            try:
                links = await post.locator('a[attributionsrc^="/privacy_sandbox/"]').all()
                participant_anchor_link = await links[0].get_attribute("href", timeout=5000)
                participant_id = participant_anchor_link.split("user/")[1].split("/")[0]
            except:
                participant_id = "unknown"
            
            post_date = None
            try:
                candidates = links[3:5]
                for date_link in candidates:
                    await random_delay(0.3, 0.7)
                    await date_link.hover()
                    tooltip = page.locator('[role="tooltip"]')
                    try:
                        await tooltip.wait_for(state="visible", timeout=2000)
                        post_date = await tooltip.inner_text()
                        await random_delay(0.2, 0.5)
                        break
                    except:
                        continue
            except:
                pass
            
            posts_data.append({
                "id": f"{group_id}_{participant_id}_{i}",
                "author": author_name,
                "user_id": participant_id,
                "content": post_text,
                "date": post_date,
                "group_id": group_id
            })
        
        await random_delay(2, 4)
        await context.storage_state(path=COOKIES_FILE)
        await random_delay(1, 2)
        await browser.close()
        
        return posts_data
