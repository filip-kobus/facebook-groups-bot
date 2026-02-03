import asyncio
from httpx import post
from sqlalchemy import select
from loguru import logger
from src.database import SessionLocal, Post, Lead
from src.scraper import FacebookScraper
from src.chatbot import Chatbot

async def main():
    """Main entry point for sending messages to leads from the last day."""
    scraper = None
    try:
        scraper = FacebookScraper()
        await scraper.init_browser()
        chatbot = Chatbot()

        async with SessionLocal() as db:
            stmt = select(Lead).where(Lead.is_contacted == False)
            result = await db.execute(stmt)
            leads = result.scalars().all()

        logger.info(f"Found {len(leads)} leads from the last 24 hours to send messages to.")

        for lead in leads:
            async with SessionLocal() as db:
                db.add(lead)
                post = await db.execute(select(Post).where(Post.post_id == lead.post_id))
                post = post.scalar_one_or_none()
                author = post.author
                user_id = post.user_id
                message = await chatbot.suggest_message(author, {"id": post.post_id, "content": post.content})
                
                messages_to_send = [
                    message
                ]
                try:
                    await scraper.send_messages(user_id, messages_to_send)
                except Exception as e:
                    logger.error(f"Failed to send message to lead {author} ({user_id}): {e}")
                finally:
                    lead.is_contacted = True
                    await db.commit()
                    logger.info(f"Message sent to lead {author} ({user_id}).")
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
