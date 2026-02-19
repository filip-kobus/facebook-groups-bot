import asyncio
import argparse
import datetime
from sqlalchemy import select
from loguru import logger
from src.database import SessionLocal, Post, Group


async def list_leads(bot_id: str = None):
    try:
        async with SessionLocal() as db:
            # stmt = select(Post).where(Post.is_lead == True, Post.is_contacted == False)
            query = select(Post).where(Post.created_at >= datetime.datetime.now() - datetime.timedelta(days=1))
            query = query.where(Post.is_lead == True, Post.is_contacted == False)
            if bot_id:
                query = query.where(Post.bot_id == bot_id)
            
            result = await db.execute(query)
            leads = result.scalars().all()

            for lead in leads:
                print(f"\n--- Lead ---")
                print(f"Bot: {lead.bot_id}")
                print(f"Group ID: {lead.group_id}")
                print(f"Post ID: {lead.post_id}")
                print(f"Created At: {lead.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"Is Lead: {lead.is_lead}")
                print(f"Is Contacted: {lead.is_contacted}")

    except Exception as e:
        logger.exception(f"Fatal error in listing messages execution: {e}")
        raise

async def list_groups(bot_id: str = None):
    try:
        async with SessionLocal() as db:
            query = select(Group)
            if bot_id:
                query = query.where(Group.bot_id == bot_id)
            
            result = await db.execute(query)
            groups = result.scalars().all()

            if not groups:
                logger.info(f"No groups found{f' for bot {bot_id}' if bot_id else ''}.")
                return

            logger.info(f"Listing all groups ({len(groups)}):")
            for i, group in enumerate(groups, 1):
                print(f"\n--- Group #{i} ---")
                print(f"Bot: {group.bot_id}")
                print(f"Group ID: {group.group_id}")
                print(f"Last Scrape Date: {group.last_scrape_date.strftime('%Y-%m-%d %H:%M:%S')}")

    except Exception as e:
        logger.exception(f"Fatal error in listing groups execution: {e}")
        raise

async def main():
    """Main entry point for listing leads."""
    parser = argparse.ArgumentParser(description="List leads and groups")
    parser.add_argument(
        "--bot",
        type=str,
        default=None,
        help="Filter by bot ID (default: show all bots)"
    )
    args = parser.parse_args()
    
    await list_leads(bot_id=args.bot)

if __name__ == "__main__":
    asyncio.run(main())
