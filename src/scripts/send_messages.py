import asyncio
from httpx import post
from sqlalchemy import select
from loguru import logger
from src.database import SessionLocal, Post, Message
from src.scraper import FacebookScraper
from src.chatbot import Chatbot

async def main():
    scraper = None
    try:
        scraper = FacebookScraper()
        await scraper.init_browser()
        chatbot = Chatbot()

        async with SessionLocal() as db:
            stmt = select(Post).where(Post.is_lead == True, Post.is_contacted == False)
            result = await db.execute(stmt)
            posts = result.scalars().all()

        logger.info(f"Found {len(posts)} leads from the last 24 hours to send messages to.")

        for post in posts:
            async with SessionLocal() as db:
                db.add(post)
                author = post.author
                user_id = post.user_id
                message_content = await chatbot.suggest_message(author, {"id": post.post_id, "content": post.content})
                
                messages_to_send = [
                    message_content
                ]
                try:
                    await scraper.send_messages(user_id, messages_to_send)
                    
                    message = Message(content=message_content, post_id=post.post_id)
                    db.add(message)
                except Exception as e:
                    logger.error(f"Failed to send message to lead {author} ({user_id}): {e}")
                finally:
                    post.is_contacted = True
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
