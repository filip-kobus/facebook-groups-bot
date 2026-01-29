import asyncio
import datetime
from sqlalchemy import select
from loguru import logger
from database import SessionLocal, Post
from scraper import FacebookScraper
from chatbot import Chatbot

async def main():
    """Main entry point for sending messages to leads from the last day."""
    scraper = None
    try:
        async with SessionLocal() as db:
            scraper = FacebookScraper()
            await scraper.init_browser()
            chatbot = Chatbot()

            now = datetime.datetime.utcnow()
            midnight_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
            stmt = select(Post).where(Post.is_lead == True, Post.created_at >= midnight_today)
            result = await db.execute(stmt)
            leads = result.scalars().all()

            logger.info(f"Found {len(leads)} leads from the last 24 hours to send messages to.")

            for lead in leads:
                message = await chatbot.suggest_message(lead.author, {"id": lead.post_id, "content": lead.content})
                
                messages_to_send = [
                    message
                ]
                await scraper.send_messages(lead.user_id, messages_to_send)
                logger.info(f"Message sent to lead {lead.author} ({lead.user_id}).")
                await asyncio.sleep(5)

            logger.success("All messages sent successfully!")

    except Exception as e:
        logger.exception(f"Fatal error in message sending execution: {e}")
        raise
    finally:
        if scraper:
            await scraper.cleanup()
            logger.debug("Browser cleanup completed")


if __name__ == "__main__":
    asyncio.run(main())
