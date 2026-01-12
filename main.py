import asyncio
import os
from playwright.async_api import async_playwright
from dotenv import load_dotenv
import time, json

load_dotenv()

COOKIES_FILE = "cookies.json"

async def login(page):
    await page.goto("https://www.facebook.com/login")
    await page.get_by_role("button", name="Allow all cookies").click()
    await page.get_by_label("Email or phone number").fill(os.getenv("EMAIL"))
    await page.get_by_label("Password").fill(os.getenv("PASSWORD"))
    await page.get_by_role("button", name="Log In").click()

def is_authenticated():
    """Sprawdza czy użytkownik jest zalogowany na podstawie COOKIES_FILE"""
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
        print(f"Błąd podczas sprawdzania autentykacji: {e}")
        return False

async def confirm_cookies(page):
    try:
        await page.get_by_role("button", name="Allow all cookies").click(timeout=5000)
    except:
        pass  # Przycisk nie istnieje, kontynuuj

async def close_notification_popup(page):
    """Zamyka popup z powiadomieniami push, jeśli się pojawi"""
    try:
        close_button = page.get_by_role("button", name="Close")
        await close_button.wait_for(state="visible", timeout=10000)
        await close_button.click()
        print("Zamknięto popup z powiadomieniami.")
    except:
        print("Popup z powiadomieniami nie pojawił się.")

async def click_middle_of_screen(page):
    viewport = page.viewport_size
    if viewport:
        x = viewport["width"] / 2
        y = viewport["height"] / 2
        await page.mouse.click(x, y)

async def get_first_post_date(page):
    input()
    await page.wait_for_selector('[role="feed"] [aria-posinset]', timeout=15000)
    
    posts = await page.locator('[role="feed"] [aria-posinset]').all()
    
    if not posts:
        print("❌ Nie znaleziono żadnych postów.")
        return
    
    print(f"\n{'='*80}")
    print(f"📊 Znaleziono {len(posts)} postów na stronie")
    print(f"{'='*80}\n")
    
    for i, post in enumerate(posts):
        print(f"\n{'─'*80}")
        print(f"📝 POST #{i+1}")
        print(f"{'─'*80}")
        
        try:
            author_locator = post.locator('h2').first
            await author_locator.scroll_into_view_if_needed(timeout=5000)
            author_name = await author_locator.inner_text()
        except:
            print(f"⚠️  Nie udało się pobrać autora, pomijam.\n")
            continue
        
        text_locator = post.locator('[data-ad-rendering-role="story_message"]')
        if not await text_locator.count():
            print(f"⚠️  Nie udało się pobrać treści posta, pomijam.\n")
            continue
        
        post_text = await text_locator.inner_text()
        if "See More" in post_text or "See more" in post_text:
            try:
                see_more = post.locator('[role="button"]:has-text("See more")')
                await see_more.scroll_into_view_if_needed(timeout=3000)
                await see_more.click(timeout=3000)
                post_text = await text_locator.inner_text()
            except:
                pass  # Nie udało się rozwinąć, używamy skróconej wersji
        
        print(f"👤 Autor: {author_name}")
        
        if "Anonymous" in author_name or "Anonimowy" in author_name:
            print(f"🔒 Post anonimowy - pomijam\n")
            continue

        links = await post.locator('a[attributionsrc^="/privacy_sandbox/"]').all()
        participant_anchor_link = await links[0].get_attribute("href", timeout=5000)
        participant_id = participant_anchor_link.split("user/")[1].split("/")[0]
        
        print(f"🆔 ID użytkownika: {participant_id}")
        
        # Data zwykle jest w linkach od 3 wzwyż
        candidates = links[3:5]
        
        for date_link in candidates:
            await date_link.hover()
            
            tooltip = page.locator('[role="tooltip"]')
            try:
                await tooltip.wait_for(state="visible", timeout=2000)
                full_date = await tooltip.inner_text()
                
                print(f"📅 Data publikacji: {full_date}")
                break
            except:
                continue
        
        # Wyświetl fragment treści posta
        preview = post_text[:200] + "..." if len(post_text) > 200 else post_text
        print(f"\n💬 Treść:")
        print(f"   {preview}\n")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=['--start-maximized'])
        is_auth = is_authenticated()
        
        if is_auth:
            context = await browser.new_context(storage_state=COOKIES_FILE, no_viewport=True)
        else:
            context = await browser.new_context(no_viewport=True)
        
        page = await context.new_page()
        
        if not is_auth:
            await login(page)
            await confirm_cookies(page)
        group_id = "1378465175518200"

        await page.goto(f"https://www.facebook.com/groups/{group_id}/?sorting_setting=CHRONOLOGICAL")
        await close_notification_popup(page)
        await get_first_post_date(page)
        input()
        await context.storage_state(path=COOKIES_FILE)
        # await page.get_by_label("Close").click()

if __name__ == "__main__":
    asyncio.run(main())