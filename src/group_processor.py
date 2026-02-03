import asyncio
import random
from typing import List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import select
from src.scraper import FacebookScraper
from src.database import Post, Group, get_last_scraping_date, check_duplicate_post
from sqlalchemy.ext.asyncio import AsyncSession
import datetime


class GroupProcessor:
    """Orchestrates the processing of Facebook groups - scraping, analyzing, and exporting."""
    
    def __init__(
        self,
        scraper: FacebookScraper,
        db: AsyncSession,
    ):
        self.scraper = scraper
        self.db = db
    
    async def random_delay_between_groups(self):
        delay = random.uniform(2, 4)
        print(f"Waiting {delay:.1f} seconds before next group...")
        await asyncio.sleep(delay)
    
    async def process_group(self, group_id: str):
        print(f"\n{'='*80}")
        print(f"Processing group: {group_id}")
        print(f"{'='*80}\n")
        
        start_time = datetime.datetime.now()
        latest_post_date = await get_last_scraping_date(self.db, group_id)
       
        posts = await self.scraper.scrape_posts(group_id, latest_post_date)
        number_of_new_posts = len(posts)
        print(f"\nScraped {number_of_new_posts} new posts.")
        
        for post_data in posts:
            post = Post(
                post_id=post_data["id"],
                content=post_data["content"],
                author=post_data["author"],
                user_id=post_data["user_id"],
                group_id=group_id
            )

            is_duplicate = await check_duplicate_post(self.db, post)
            if is_duplicate:
                print(f"Skipping duplicate post {post.post_id} from user {post.author}")
                number_of_new_posts -= 1
                continue
            self.db.add(post)
            
        result = await self.db.execute(
            select(Group).where(Group.group_id == group_id)
        )
        group = result.scalar_one_or_none()
        group.last_scrape_date = start_time
        await self.db.commit()
        
        print(f"\nGroup {group_id} complete: {number_of_new_posts} new posts saved.")

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
