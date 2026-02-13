import asyncio
import argparse
from loguru import logger
from src.scraper import FacebookScraper
from src.group_processor import GroupProcessor
from src.database import init_db, SessionLocal, sync_groups_from_config
from src.bot_config import get_bot_config, get_all_bot_configs

async def scrape_bot(bot_id: str):
    bot_config = get_bot_config(bot_id)
    logger.info(f"Starting scrape for bot: {bot_config.name} ({bot_id})")
    
    await init_db(bot_id=bot_id, group_ids=bot_config.groups)
    
    scraper = None
    try:
        async with SessionLocal() as db:
            await sync_groups_from_config(
                db, 
                bot_id, 
                bot_config.groups, 
                initial_scrape_days=bot_config.initial_scrape_days
            )
            
            scraper = FacebookScraper(
                user=bot_id,
                max_posts_to_scan=bot_config.max_posts_per_group
            )
            processor = GroupProcessor(
                scraper, 
                db, 
                bot_id=bot_id,
                force_full_rescrape=bot_config.force_full_rescrape
            )
            await processor.process_all_groups(bot_config.groups)

            logger.success(f"All groups processed successfully for bot: {bot_id}!")
    except Exception as e:
        logger.exception(f"Fatal error in scraping for bot {bot_id}: {e}")
        raise
    finally:
        if scraper:
            await scraper.cleanup()
            logger.debug("Browser cleanup completed")

async def main():
    """Main entry point for the Facebook groups lead scraper."""
    parser = argparse.ArgumentParser(description="Scrape Facebook groups for leads")
    parser.add_argument(
        "--bot",
        type=str,
        default="leasing",
        help="Bot ID to run scraping for (default: leasing). Use 'all' to run for all enabled bots."
    )
    args = parser.parse_args()
    
    if args.bot == "all":
        # Run for all enabled bots sequentially
        bots = get_all_bot_configs(enabled_only=True)
        logger.info(f"Running scraper for {len(bots)} enabled bots")
        
        for bot_config in bots:
            logger.info(f"\n{'='*80}")
            logger.info(f"Starting bot: {bot_config.name} ({bot_config.bot_id})")
            logger.info(f"{'='*80}\n")
            await scrape_bot(bot_config.bot_id)
    else:
        await scrape_bot(args.bot)


if __name__ == "__main__":
    asyncio.run(main())
