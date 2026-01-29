import asyncio
import datetime
from sqlalchemy import select
from loguru import logger
from database import SessionLocal, Post

async def main():
    """Main entry point for listing messages sent to leads from the last day."""
    try:
        async with SessionLocal() as db:
            now = datetime.datetime.utcnow()
            midnight_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
            stmt = select(Post).where(Post.is_lead == True, Post.created_at >= midnight_today)
            result = await db.execute(stmt)
            leads = result.scalars().all()

            if not leads:
                logger.info("No messages sent in the last 24 hours.")
                return

            logger.info(f"Messages sent in the last 24 hours ({len(leads)}):")
            for i, lead in enumerate(leads, 1):
                print(f"\n--- Lead #{i} ---")
                print(f"Author: {lead.author} (ID: {lead.user_id})")
                print(f"Group ID: {lead.group_id}")
                print(f"Post ID: {lead.post_id}")
                print(f"Timestamp: {lead.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"Content: {lead.content}")

    except Exception as e:
        logger.exception(f"Fatal error in listing messages execution: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
