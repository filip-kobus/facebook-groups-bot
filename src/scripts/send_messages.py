import asyncio
import argparse
from sqlalchemy import select
from loguru import logger
from src.database import SessionLocal, Post, Message, init_db
from src.scraper import FacebookScraper
from src.chatbot import Chatbot
from src.bot_config import get_bot_config, get_all_bot_configs

async def send_messages_for_bot(bot_id: str):
    """Send messages to leads for a specific bot."""
    bot_config = get_bot_config(bot_id)
    logger.info(f"Starting message sending for bot: {bot_config.name} ({bot_id})")
    
    await init_db(bot_id=bot_id, group_ids=bot_config.groups)
    
    scraper = None
    try:
        scraper = FacebookScraper(user=bot_id)
        await scraper.init_browser()
        chatbot = Chatbot(system_prompt=bot_config.messaging_prompt)

        async with SessionLocal() as db:
            stmt = select(Post).where(
                Post.is_lead == True,
                Post.is_contacted == False,
                Post.bot_id == bot_id
            )
            result = await db.execute(stmt)
            posts = result.scalars().all()

        logger.info(f"Found {len(posts)} leads for bot {bot_id} to send messages to.")

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
        logger.success(f"All messages sent successfully for bot {bot_id}!")

    except Exception as e:
        logger.exception(f"Fatal error in message sending for bot {bot_id}: {e}")
        raise
    finally:
        if scraper:
            await scraper.cleanup()
            logger.debug("Browser cleanup completed")

async def main():
    parser = argparse.ArgumentParser(description="Send messages to identified leads")
    parser.add_argument(
        "--bot",
        type=str,
        default="leasing",
        help="Bot ID to send messages for (default: leasing). Use 'all' to run for all enabled bots."
    )
    args = parser.parse_args()
    
    if args.bot == "all":
        bots = get_all_bot_configs(enabled_only=True)
        logger.info(f"Running message sending for {len(bots)} enabled bots")
        
        for bot_config in bots:
            logger.info(f"\n{'='*80}")
            logger.info(f"Starting bot: {bot_config.name} ({bot_config.bot_id})")
            logger.info(f"{'='*80}\n")
            await send_messages_for_bot(bot_config.bot_id)
    else:
        await send_messages_for_bot(args.bot)


if __name__ == "__main__":
    asyncio.run(main())
