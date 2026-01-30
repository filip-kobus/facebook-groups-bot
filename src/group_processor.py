import asyncio
import random
from typing import List, Dict
from sqlalchemy.orm import Session
from scraper import FacebookScraper
from analyzer import LeadAnalyzer
from database import Post
from sqlalchemy.ext.asyncio import AsyncSession


class GroupProcessor:
    """Orchestrates the processing of Facebook groups - scraping, analyzing, and exporting."""
    
    def __init__(
        self,
        scraper: FacebookScraper,
        analyzer: LeadAnalyzer,
        db: AsyncSession,
    ):
        """
        Initialize the group processor.
        
        Args:
            scraper: FacebookScraper instance
            analyzer: LeadAnalyzer instance
            db: SQLAlchemy session
        """
        self.scraper = scraper
        self.analyzer = analyzer
        self.db = db
        self.all_posts = []
    
    async def random_delay_between_groups(self):
        """Random delay between processing groups."""
        delay = random.uniform(5, 15)
        print(f"Waiting {delay:.1f} seconds before next group...")
        await asyncio.sleep(delay)
    
    async def process_group(self, group_id: str):
        """
        Process a single Facebook group: scrape, analyze, and collect posts.
        
        Args:
            group_id: Facebook group ID
            
        Returns:
            List of analyzed posts
        """
        print(f"\n{'='*80}")
        print(f"Processing group: {group_id}")
        print(f"{'='*80}\n")
        
        # Scrape posts
        posts = await self.scraper.scrape_posts(group_id)
        print(f"\nScraped {len(posts)} posts from last {self.scraper.hours_back} hours")
        
        # Analyze posts in batches
        all_analyzed_posts = []
        
        for i, batch in enumerate(self.analyzer.batch_posts(posts), 1):
            print(f"Analyzing batch {i} ({len(batch)} posts)...")
            analyzed = await self.analyzer.analyze_posts_batch(batch)
            all_analyzed_posts.extend(analyzed)
            
            leads_count = sum(1 for p in analyzed if p["is_lead"])
            print(f"Batch {i}: {leads_count}/{len(analyzed)} leads found")
        
        # Add to collection
        for post_data in all_analyzed_posts:
            post = Post(
                post_id=post_data["id"],
                content=post_data["content"],
                author=post_data["author"],
                user_id=post_data["user_id"],
                is_lead=post_data["is_lead"],
                group_id=group_id
            )
            self.db.add(post)
        await self.db.commit()
        
        total_leads = sum(1 for p in all_analyzed_posts if p["is_lead"])
        print(f"\nGroup {group_id} complete: {total_leads}/{len(all_analyzed_posts)} total leads")

    async def process_all_groups(self, group_ids: List[str]):
        """
        Process all groups and export leads at the end.
        
        Args:
            group_ids: List of Facebook group IDs to process
        """
        # Initialize browser
        await self.scraper.init_browser()
        
        try:
            # Process each group
            for idx, group_id in enumerate(group_ids):
                try:
                    await self.process_group(group_id)
                    
                    if idx < len(group_ids) - 1:
                        await self.random_delay_between_groups()
                except Exception as e:
                    print(f"Error processing group {group_id}: {e}")
                    continue
            
            # Summary
            print(f"\n✅ All groups processed successfully")

        finally:
            if self.scraper:
                await self.scraper.context.storage_state(path="state.json")
                await self.scraper.cleanup()
