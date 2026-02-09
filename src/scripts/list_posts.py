import asyncio
import datetime
from sqlalchemy import select
from loguru import logger
from src.database import SessionLocal, Post, Group


async def list_leads():
    try:
        async with SessionLocal() as db:
            # stmt = select(Post).where(Post.is_lead == True, Post.is_contacted == False)
            stmt=select(Post).where(Post.created_at >= datetime.datetime.now() - datetime.timedelta(days=1))
            result = await db.execute(stmt)
            leads = result.scalars().all()

            if not leads:
                logger.info("No messages sent in the last 24 hours.")
                return

            # Save to text file
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"logs/leads_{timestamp}.txt"
            
            logger.info(f"Messages sent in the last 24 hours ({len(leads)}), saving to {filename}")
            
            with open(filename, 'w') as f:
                f.write(f"Messages sent in the last 24 hours ({len(leads)})\n")
                f.write(f"Generated at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 60 + "\n\n")
                
                for i, lead in enumerate(leads, 1):
                    f.write(f"\n--- Lead #{i} ---\n")
                    f.write(f"Author: {lead.author}\n")
                    f.write(f"Date: {lead.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Content: {lead.content}\n")

    except Exception as e:
        logger.exception(f"Fatal error in listing messages execution: {e}")
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
            now = datetime.datetime.now()
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
