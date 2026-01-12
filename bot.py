import asyncio
import random
from scraper import scrape_posts
from analyzer import analyze_posts_batch, batch_posts
from csv_handler import initialize_csv, append_posts_to_csv
from groups import groups_ids

async def random_delay_between_groups():
    delay = random.uniform(30, 60)
    print(f"Waiting {delay:.1f} seconds before next group...")
    await asyncio.sleep(delay)

async def process_group(group_id: str, max_posts: int = 50):
    print(f"\n{'='*80}")
    print(f"Processing group: {group_id}")
    print(f"{'='*80}\n")
    
    posts = await scrape_posts(group_id, max_posts)
    print(f"Scraped {len(posts)} posts")
    
    all_analyzed_posts = []
    
    for i, batch in enumerate(batch_posts(posts, batch_size=5), 1):
        print(f"Analyzing batch {i} ({len(batch)} posts)...")
        analyzed = await analyze_posts_batch(batch)
        all_analyzed_posts.extend(analyzed)
        
        leads_count = sum(1 for p in analyzed if p["is_lead"])
        print(f"Batch {i}: {leads_count}/{len(analyzed)} leads found")
    
    append_posts_to_csv(all_analyzed_posts)
    
    total_leads = sum(1 for p in all_analyzed_posts if p["is_lead"])
    print(f"\nGroup {group_id} complete: {total_leads}/{len(all_analyzed_posts)} total leads")
    
    return all_analyzed_posts

async def main():
    initialize_csv()
    
    for idx, group_id in enumerate(groups_ids):
        try:
            await process_group(group_id, max_posts=50)
            
            if idx < len(groups_ids) - 1:
                await random_delay_between_groups()
        except Exception as e:
            print(f"Error processing group {group_id}: {e}")
            continue
    
    print("\n✅ All groups processed successfully")

if __name__ == "__main__":
    asyncio.run(main())
