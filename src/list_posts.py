import asyncio
import datetime
from sqlalchemy import select
from loguru import logger
from database import SessionLocal, Post, Group, Lead


async def list_posts():
    try:
        async with SessionLocal() as db:
            now = datetime.datetime.utcnow()
            midnight_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
            midnight_yesterday = midnight_today - datetime.timedelta(days=1)
            # stmt = select(Post).where(Post.is_lead == True, Post.created_at >= midnight_yesterday)
            stmt = select(Post).where(Post.is_lead == True)
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

async def list_leads():
    try:
        async with SessionLocal() as db:
            stmt = select(Lead)
            result = await db.execute(stmt)
            leads = result.scalars().all()

            if not leads:
                logger.info("No leads found in the database.")
                return

            logger.info(f"Listing all leads ({len(leads)}):")
            for i, lead in enumerate(leads, 1):
                post = await db.execute(select(Post).where(Post.post_id == lead.post_id))
                post = post.scalar_one_or_none()
                print(f"\n--- Lead #{i} ---")
                print(f"Post ID: {lead.post_id}")
                print(f"Is Contacted: {lead.is_contacted}")
                print(f"Content: {post.content}")

    except Exception as e:
        logger.exception(f"Fatal error in listing leads execution: {e}")
        raise

async def list_groups():
    try:
        async with SessionLocal() as db:
            stmt = select(Group)
            result = await db.execute(stmt)
            groups = result.scalars().all()

            if not groups:
                logger.info("No groups found in the database.")
                return

            logger.info(f"Listing all groups ({len(groups)}):")
            for i, group in enumerate(groups, 1):
                print(f"\n--- Group #{i} ---")
                print(f"Group ID: {group.group_id}")
                print(f"Last Scrape Date: {group.last_scrape_date.strftime('%Y-%m-%d %H:%M:%S')}")

    except Exception as e:
        logger.exception(f"Fatal error in listing groups execution: {e}")
        raise

async def main():
    """Main entry point for listing messages sent to leads from the last day."""
    try:
        async with SessionLocal() as db:
            now = datetime.datetime.utcnow()
            midnight_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
            midnight_yesterday = midnight_today - datetime.timedelta(days=1)
            # stmt = select(Post).where(Post.is_lead == True, Post.created_at >= midnight_yesterday)
            stmt = select(Post).where(Post.is_lead == True)
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
    asyncio.run(list_leads())
