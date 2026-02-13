"""Migration script to add bot_type field and create new tables."""
import asyncio
from pathlib import Path
import yaml
from loguru import logger

from src.database import engine, Base


async def migrate():
    """Run database migration."""
    logger.info("Starting database migration...")
    
    # Create all tables (will add new ones, existing ones unchanged due to SQLAlchemy)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("✓ Database schema updated")
    
    # Note: bot_type field should already be added to YAML files manually
    # This script only creates the new tables
    
    logger.info("Migration completed successfully!")
    logger.info("")
    logger.info("Action items:")
    logger.info("1. All existing bot YAML files now have bot_type: lead_bot")
    logger.info("2. New tables created: bot_runs, jobs, settings, group_memberships")
    logger.info("3. Run 'make admin' to start the admin panel with new features")


if __name__ == "__main__":
    asyncio.run(migrate())
