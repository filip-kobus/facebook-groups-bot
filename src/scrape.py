import asyncio
from loguru import logger
from scraper import FacebookScraper
from group_processor import GroupProcessor
from database import init_db, SessionLocal, get_groups

async def main():
    """Main entry point for the Facebook groups lead scraper."""
    await init_db()
    
    scraper = None
    try:
        async with SessionLocal() as db:
            groups_ids = await get_groups(db)
            scraper = FacebookScraper()
            processor = GroupProcessor(scraper, db)
            await processor.process_all_groups(groups_ids)

            logger.success("All groups processed successfully!")
    except Exception as e:
        logger.exception(f"Fatal error in main execution: {e}")
        raise
    finally:
        if scraper:
            await scraper.context.storage_state(path="state.json")
            await scraper.cleanup()
            logger.debug("Browser cleanup completed")


if __name__ == "__main__":
    asyncio.run(main())
