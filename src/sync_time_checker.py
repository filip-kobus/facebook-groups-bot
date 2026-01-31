import asyncio
import datetime
from sqlalchemy import select
from loguru import logger
from database import SessionLocal, Group


async def get_last_sync_times():
    try:
        async with SessionLocal() as db:
            result = await db.execute(select(Group))
            groups = result.scalars().all()
            for group in groups:
                print(f"Group ID: {group.group_id} | Last Sync Time: {group.last_scrape_date}")

    except Exception as e:
        logger.exception(f"Fatal error in listing messages execution: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(get_last_sync_times())
