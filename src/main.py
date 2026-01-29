import asyncio
from loguru import logger
from chatbot import Chatbot
from scraper import FacebookScraper
from analyzer import LeadAnalyzer
from group_processor import GroupProcessor
from groups import groups_ids
from messages import STARTING_MESSAGE, STARTING_MESSAGE_WHEN_PARAMS_GIVEN


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
        chatbot = Chatbot()
        
        processor = GroupProcessor(scraper, analyzer, exporter, chatbot)
        # Initialize browser before sending messages
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


