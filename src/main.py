import asyncio
from loguru import logger
from src.scraper import FacebookScraper
from src.analyzer import LeadAnalyzer
from src.excel_exporter import ExcelExporter
from src.group_processor import GroupProcessor
from src.groups import groups_ids


# Configure loguru
logger.remove()  # Remove default handler
logger.add(
    "logs/bot_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="7 days",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
)
logger.add(
    lambda msg: print(msg, end=""),
    level="DEBUG",
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
)
logger.add(
    lambda msg: print(msg, end=""),
    level="INFO",
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
)

async def main():
    """Main entry point for the Facebook groups lead scraper."""  
    scraper = None
    try:
        scraper = FacebookScraper()
        analyzer = LeadAnalyzer(batch_size=10)
        exporter = ExcelExporter()
        
        processor = GroupProcessor(scraper, analyzer, exporter)
        
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


