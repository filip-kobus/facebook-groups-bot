import asyncio
import random
from typing import List, Dict
from src.scraper import FacebookScraper
from src.analyzer import LeadAnalyzer
from src.excel_exporter import ExcelExporter


class GroupProcessor:
    """Orchestrates the processing of Facebook groups - scraping, analyzing, and exporting."""
    
    def __init__(
        self,
        scraper: FacebookScraper,
        analyzer: LeadAnalyzer,
        exporter: ExcelExporter
    ):
        """
        Initialize the group processor.
        
        Args:
            scraper: FacebookScraper instance
            analyzer: LeadAnalyzer instance
            exporter: ExcelExporter instance
        """
        self.scraper = scraper
        self.analyzer = analyzer
        self.exporter = exporter
        self.all_posts = []
    
    async def random_delay_between_groups(self):
        """Random delay between processing groups."""
        delay = random.uniform(5, 15)
        print(f"Waiting {delay:.1f} seconds before next group...")
        await asyncio.sleep(delay)
    
    async def process_group(self, group_id: str) -> List[Dict]:
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
        self.all_posts.extend(all_analyzed_posts)
        
        total_leads = sum(1 for p in all_analyzed_posts if p["is_lead"])
        print(f"\nGroup {group_id} complete: {total_leads}/{len(all_analyzed_posts)} total leads")
        
        # Export all analyzed posts from this group immediately (for later review)
        if all_analyzed_posts:
            self.exporter.export_to_excel(all_analyzed_posts, append=True)
        
        return all_analyzed_posts
    
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
            total_leads = sum(1 for p in self.all_posts if p.get("is_lead", False))
            if total_leads > 0:
                print(f"\n✅ All groups processed successfully")
                print(f"📊 Total leads found: {total_leads}")
            else:
                print("\n⚠️  No leads found across all groups")
            
        finally:
            # Cleanup
            await self.scraper.save_cookies()
            await self.scraper.cleanup()
