"""Migration script to add bot_id column to existing database."""
import asyncio
import aiosqlite
from loguru import logger

DATABASE_PATH = "leads.db"

async def migrate():
    """Add bot_id column to posts and group tables with default value 'leasing'."""
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            # Check if bot_id already exists in posts table
            cursor = await db.execute("PRAGMA table_info(posts)")
            columns = await cursor.fetchall()
            post_columns = [col[1] for col in columns]
            
            if "bot_id" not in post_columns:
                logger.info("Adding bot_id column to posts table...")
                await db.execute("ALTER TABLE posts ADD COLUMN bot_id TEXT DEFAULT 'leasing'")
                await db.execute("CREATE INDEX IF NOT EXISTS ix_posts_bot_id ON posts (bot_id)")
                logger.success("Added bot_id to posts table")
            else:
                logger.info("bot_id column already exists in posts table")
            
            # Check if bot_id already exists in group table
            cursor = await db.execute("PRAGMA table_info('group')")
            columns = await cursor.fetchall()
            group_columns = [col[1] for col in columns]
            
            if "bot_id" not in group_columns:
                logger.info("Adding bot_id column to group table...")
                await db.execute("ALTER TABLE 'group' ADD COLUMN bot_id TEXT DEFAULT 'leasing'")
                await db.execute("CREATE INDEX IF NOT EXISTS ix_group_bot_id ON 'group' (bot_id)")
                logger.success("Added bot_id to group table")
            else:
                logger.info("bot_id column already exists in group table")
            
            await db.commit()
            logger.success("Migration completed successfully!")
            
    except Exception as e:
        logger.exception(f"Migration failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(migrate())
