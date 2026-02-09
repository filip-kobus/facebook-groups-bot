import asyncio
import argparse
import datetime
from sqlalchemy import select
from loguru import logger
from src.database import SessionLocal, Group


async def get_last_sync_times(bot_id: str = None):
    try:
        async with SessionLocal() as db:
            query = select(Group)
            if bot_id:
                query = query.where(Group.bot_id == bot_id)
            
            result = await db.execute(query.order_by(Group.bot_id, Group.group_id))
            groups = result.scalars().all()
            
            if not groups:
                print(f"No groups found{f' for bot {bot_id}' if bot_id else ''}.")
                return
            
            # Group by bot_id
            groups_by_bot = {}
            for group in groups:
                bot = group.bot_id or "unknown"
                if bot not in groups_by_bot:
                    groups_by_bot[bot] = []
                groups_by_bot[bot].append(group)
            
            # Display grouped by bot
            for bot, bot_groups in groups_by_bot.items():
                print(f"\n{'='*80}")
                print(f"Bot: {bot} ({len(bot_groups)} groups)")
                print(f"{'='*80}")
                for group in bot_groups:
                    status = "❌ ERROR" if group.last_run_error else "✅ OK"
                    print(f"  Group ID: {group.group_id} | Last Sync: {group.last_scrape_date} | Status: {status}")
                    if group.last_run_error and group.last_error_message:
                        print(f"    Error: {group.last_error_message}")

    except Exception as e:
        logger.exception(f"Fatal error in listing sync status: {e}")
        raise

async def main():
    parser = argparse.ArgumentParser(description="Check sync status of groups")
    parser.add_argument(
        "--bot",
        type=str,
        default=None,
        help="Filter by bot ID (default: show all bots)"
    )
    args = parser.parse_args()
    
    await get_last_sync_times(bot_id=args.bot)

if __name__ == "__main__":
    asyncio.run(main())
