import asyncio
import random
from typing import List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import select
from scraper import FacebookScraper
from database import Post, Group, get_last_scraping_date
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
        
        start_time = datetime.datetime.utcnow()
        latest_post_date = await get_last_scraping_date(self.db, group_id)
       
        posts = await self.scraper.scrape_posts(group_id, latest_post_date)
        print(f"\nScraped {len(posts)} new posts.")
        
        for post_data in posts:
            post = Post(
                post_id=post_data["id"],
                content=post_data["content"],
                author=post_data["author"],
                user_id=post_data["user_id"],
                group_id=group_id
            )
            self.db.add(post)
        result = await self.db.execute(
            select(Group).where(Group.group_id == group_id)
        )
        group = result.scalar_one_or_none()
        group.last_scrape_date = start_time
        await self.db.commit()
        
        print(f"\nGroup {group_id} complete: {len(posts)} new posts saved.")

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
                await self.scraper.context.storage_state(path="state.json")
                await self.scraper.cleanup()
