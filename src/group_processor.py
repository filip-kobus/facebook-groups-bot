import asyncio
import random
import datetime
import os
from typing import List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import select
from src.scraper import FacebookScraper
from src.database import Post, Group, get_last_scraping_date, check_duplicate_post
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

class GroupProcessor:
    def __init__(
        self,
        scraper: FacebookScraper,
        db: AsyncSession,
        bot_id: str = "leasing",
        force_full_rescrape: bool = False,
    ):
        self.scraper = scraper
        self.db = db
        self.bot_id = bot_id
        self.force_full_rescrape = force_full_rescrape
    
    async def random_delay_between_groups(self):
        delay = random.uniform(2, 4)
        print(f"Waiting {delay:.1f} seconds before next group...")
        await asyncio.sleep(delay)
    
    async def process_group(self, group_id: str):
        print(f"\n{'='*80}")
        print(f"Processing group: {group_id} (bot: {self.bot_id})")
        print(f"{'='*80}\n")
        
        start_time = datetime.datetime.now()
        
        # If force_full_rescrape is enabled, ignore last scrape date
        if self.force_full_rescrape:
            latest_post_date = None
            logger.info(f"Force full rescrape enabled - ignoring last scrape date for group {group_id}")
        else:
            latest_post_date = await get_last_scraping_date(self.db, group_id, self.bot_id)
        
        result = await self.db.execute(
            select(Group).where(Group.group_id == group_id, Group.bot_id == self.bot_id)
        )
        group = result.scalars().first()
        
        try:
            posts = await self.scraper.scrape_posts(group_id, latest_post_date)
            number_of_new_posts = len(posts)
            print(f"\nScraped {number_of_new_posts} new posts.")
            
            for post_data in posts:
                post = Post(
                    post_id=post_data["id"],
                    content=post_data["content"],
                    author=post_data["author"],
                    user_id=post_data["user_id"],
                    group_id=group_id,
                    bot_id=self.bot_id
                )

                is_duplicate = await check_duplicate_post(self.db, post)
                if is_duplicate:
                    print(f"Skipping duplicate post {post.post_id} from user {post.author}")
                    number_of_new_posts -= 1
                    continue
                self.db.add(post)
            
            await self.db.commit()
            
            group.last_scrape_date = start_time
            group.last_run_error = False
            group.last_error_message = None
            await self.db.commit()
            
            print(f"\nGroup {group_id} complete: {number_of_new_posts} new posts saved.")
            
        except Exception as e:
            os.makedirs("logs/screenshots", exist_ok=True)
            screenshot_path = f"logs/screenshots/error_{group_id}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            try:
                await self.scraper.page.screenshot(path=screenshot_path)
                logger.error(f"Error screenshot saved to {screenshot_path}")
            except Exception as screenshot_error:
                logger.error(f"Failed to capture screenshot: {screenshot_error}")
            
            group.last_run_error = True
            group.last_error_message = str(e)
            await self.db.commit()
            print(f"\nError in group {group_id}: {e}")
            raise

    async def process_all_groups(self, group_ids: List[str]):
        await self.scraper.init_browser()
        
        try:
            for idx, group_id in enumerate(group_ids):
                try:
                    await self.process_group(group_id)
                    
                    if idx < len(group_ids) - 1:
                        await self.random_delay_between_groups()
                except Exception as e:
                    print(f"Error processing group {group_id}: {e}")
                    continue
            
            print(f"\n✅ All groups processed successfully")

        finally:
            if self.scraper:
                await self.scraper.cleanup()
