import asyncio
from loguru import logger
from scraper import FacebookScraper
from analyzer import LeadAnalyzer
from group_processor import GroupProcessor
from groups import groups_ids
from database import init_db, SessionLocal

async def main():
    """Main entry point for the Facebook groups lead scraper."""
    await init_db()
    
    scraper = None
    try:
        async with SessionLocal() as db:
            scraper = FacebookScraper()
            analyzer = LeadAnalyzer(batch_size=10)
            
            processor = GroupProcessor(scraper, analyzer, db)
            await processor.process_all_groups(groups_ids)

            logger.success("All groups processed successfully!")
    except Exception as e:
        logger.exception(f"Fatal error in main execution: {e}")
        raise
    finally:
        if scraper:
            await scraper.cleanup()
            logger.debug("Browser cleanup completed")


if __name__ == "__main__":
    asyncio.run(main())
