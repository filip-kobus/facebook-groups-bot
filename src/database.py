from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy import Column, ForeignKey, Integer, String, Boolean, DateTime, select, desc, UniqueConstraint, Text, JSON, Float
from src.groups import groups_ids
from typing import Optional, List
from rapidfuzz import fuzz
import datetime
import json

DATABASE_URL = "sqlite+aiosqlite:///leads.db"

engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)
Base = declarative_base()

class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(String, unique=True, index=True)
    content = Column(String)
    author = Column(String)
    user_id = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.now)
    is_lead = Column(Boolean, default=None, nullable=True)
    is_contacted = Column(Boolean, default=False)
    bot_id = Column(String, index=True, default="leasing")  # Bot identifier
    group_id = Column(String, index=True)  # Linked to Group, but without FK constraint since (group_id, bot_id) is composite unique
    messages = relationship("Message", back_populates="post")

class Group(Base):
    __tablename__ = "group"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(String, index=True)
    bot_id = Column(String, index=True, default="leasing")  # Bot identifier
    last_scrape_date = Column(DateTime, default=datetime.datetime.now)
    last_run_error = Column(Boolean, default=False)
    last_error_message = Column(String, nullable=True)
    
    __table_args__ = (
        UniqueConstraint('group_id', 'bot_id', name='uix_group_bot'),
    )

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(String)
    sent_at = Column(DateTime, default=datetime.datetime.now)
    post_id = Column(String, ForeignKey("posts.post_id"))
    post = relationship("Post", back_populates="messages")

class BotRun(Base):
    """History of bot executions"""
    __tablename__ = "bot_runs"

    id = Column(Integer, primary_key=True, index=True)
    bot_id = Column(String, index=True, nullable=False)
    run_type = Column(String, nullable=False)  # scrape, classify, message, invite, full
    status = Column(String, nullable=False, default="running")  # running, completed, failed, cancelled
    started_at = Column(DateTime, default=datetime.datetime.now)
    finished_at = Column(DateTime, nullable=True)
    total_items = Column(Integer, default=0)
    processed_items = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    triggered_by = Column(String, default="manual")  # manual, system, schedule
    run_metadata = Column(Text, nullable=True)  # JSON string for additional data
    
    jobs = relationship("Job", back_populates="bot_run")

class Job(Base):
    """Active jobs with real-time progress tracking"""
    __tablename__ = "jobs"

    id = Column(String, primary_key=True)  # UUID
    bot_id = Column(String, index=True, nullable=False)
    bot_run_id = Column(Integer, ForeignKey("bot_runs.id"), nullable=True)
    job_type = Column(String, nullable=False)  # scrape, classify, message, invite, full
    status = Column(String, nullable=False, default="pending")  # pending, running, completed, failed, cancelled
    progress = Column(Float, default=0.0)  # 0-100
    started_at = Column(DateTime, default=datetime.datetime.now)
    current_step = Column(String, nullable=True)
    log_messages = Column(Text, nullable=True)  # JSON array of log messages
    
    bot_run = relationship("BotRun", back_populates="jobs")

class Setting(Base):
    """Key-value settings per bot"""
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    bot_id = Column(String, index=True, nullable=False)
    key = Column(String, nullable=False)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    
    __table_args__ = (
        UniqueConstraint('bot_id', 'key', name='uix_bot_setting'),
    )

class GroupMembership(Base):
    """Groups associated with bots (alternative to YAML groups list)"""
    __tablename__ = "group_memberships"

    id = Column(Integer, primary_key=True, index=True)
    bot_id = Column(String, index=True, nullable=False)
    group_id = Column(String, nullable=False)
    added_at = Column(DateTime, default=datetime.datetime.now)
    is_active = Column(Boolean, default=True)
    
    __table_args__ = (
        UniqueConstraint('bot_id', 'group_id', name='uix_bot_group'),
    )

async def init_db(bot_id: str = "leasing", group_ids: list = None):
    """Initialize database tables and create groups for a specific bot."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    if group_ids is None:
        group_ids = groups_ids
    
    async with SessionLocal() as session:
        one_day_ago = datetime.datetime.now() - datetime.timedelta(days=1)
        for group_id in group_ids:
            exists = await session.execute(
                select(Group).where(Group.group_id == group_id, Group.bot_id == bot_id)
            )
            if not exists.scalar_one_or_none():
                session.add(Group(group_id=group_id, bot_id=bot_id, last_scrape_date=one_day_ago))
        await session.commit()

async def get_db():
    async with SessionLocal() as session:
        yield session

async def get_last_scraping_date(db: AsyncSession, group_id: str, bot_id: str) -> Optional[datetime.datetime]:
    result = await db.execute(
        select(Group.last_scrape_date)
        .where(Group.group_id == group_id, Group.bot_id == bot_id)
        .limit(1)
    )
    return result.scalar_one_or_none()

async def get_groups(db: AsyncSession, bot_id: Optional[str] = None):
    if bot_id:
        result = await db.execute(select(Group.group_id).where(Group.bot_id == bot_id))
    else:
        result = await db.execute(select(Group.group_id))
    return result.scalars().all()

async def get_not_classified_posts(db: AsyncSession, bot_id: Optional[str] = None):
    query = select(Post).where(Post.is_lead == None)
    if bot_id:
        query = query.where(Post.bot_id == bot_id)
    result = await db.execute(query)
    return result.scalars().all()

async def check_duplicate_post(db: AsyncSession, post: Post) -> bool:
    result = await db.execute(
        select(Post).where(
            Post.content == post.content, 
            Post.user_id == post.user_id,
            Post.bot_id == post.bot_id
        )
    )
    existing_post = result.scalar_one_or_none()
    return existing_post is not None

async def check_duplicate_lead(db: AsyncSession, user_id: str, new_content: str, bot_id: str, similarity_threshold: float = 80.0) -> bool:
    result = await db.execute(
        select(Post)
        .where(Post.user_id == user_id, Post.is_lead == True, Post.bot_id == bot_id)
    )
    existing_lead_posts = result.scalars().all()
    
    if not existing_lead_posts:
        return False
    
    for existing_post in existing_lead_posts:
        if not existing_post.content or not new_content:
            continue
            
        similarity_score = fuzz.partial_ratio(existing_post.content.lower(), new_content.lower())
        
        if similarity_score >= similarity_threshold:
            return True
    
    return False

async def sync_groups_from_config(db: AsyncSession, bot_id: str, group_ids: List[str], initial_scrape_days: int = 1, remove_old: bool = False) -> None:
    from loguru import logger
    
    result = await db.execute(
        select(Group).where(Group.bot_id == bot_id)
    )
    existing_groups = {g.group_id: g for g in result.scalars().all()}
    
    # Add new groups
    for group_id in group_ids:
        if group_id not in existing_groups:
            logger.info(f"Creating new group record: {group_id} (bot: {bot_id})")
            new_group = Group(
                group_id=group_id,
                bot_id=bot_id,
                last_scrape_date=datetime.datetime.now() - datetime.timedelta(days=initial_scrape_days),
                last_run_error=False
            )
            db.add(new_group)
    
    # Remove groups that are no longer in config
    if remove_old:
        groups_to_remove = set(existing_groups.keys()) - set(group_ids)
        if groups_to_remove:
            logger.info(f"Removing {len(groups_to_remove)} groups no longer in config for bot {bot_id}: {groups_to_remove}")
            for group_id in groups_to_remove:
                await db.delete(existing_groups[group_id])
    
    await db.commit()
    logger.info(f"Group sync complete for bot {bot_id}: {len(group_ids)} groups in config")


# BotRun helper functions
async def create_bot_run(db: AsyncSession, bot_id: str, run_type: str, triggered_by: str = "manual") -> BotRun:
    """Create a new bot run record"""
    bot_run = BotRun(
        bot_id=bot_id,
        run_type=run_type,
        status="running",
        triggered_by=triggered_by,
        started_at=datetime.datetime.now()
    )
    db.add(bot_run)
    await db.commit()
    await db.refresh(bot_run)
    return bot_run

async def update_bot_run(
    db: AsyncSession, 
    bot_run_id: int, 
    status: Optional[str] = None,
    processed_items: Optional[int] = None,
    total_items: Optional[int] = None,
    error_message: Optional[str] = None
) -> None:
    """Update bot run status and progress"""
    result = await db.execute(select(BotRun).where(BotRun.id == bot_run_id))
    bot_run = result.scalar_one_or_none()
    
    if bot_run:
        if status:
            bot_run.status = status
            if status in ["completed", "failed", "cancelled"]:
                bot_run.finished_at = datetime.datetime.now()
        if processed_items is not None:
            bot_run.processed_items = processed_items
        if total_items is not None:
            bot_run.total_items = total_items
        if error_message is not None:
            bot_run.error_message = error_message
        
        await db.commit()

async def get_recent_bot_runs(db: AsyncSession, bot_id: Optional[str] = None, limit: int = 10) -> List[BotRun]:
    """Get recent bot runs, optionally filtered by bot_id"""
    query = select(BotRun).order_by(desc(BotRun.started_at)).limit(limit)
    if bot_id:
        query = query.where(BotRun.bot_id == bot_id)
    
    result = await db.execute(query)
    return result.scalars().all()

# Job helper functions
async def create_job(db: AsyncSession, job_id: str, bot_id: str, job_type: str, bot_run_id: Optional[int] = None) -> Job:
    """Create a new job record"""
    job = Job(
        id=job_id,
        bot_id=bot_id,
        job_type=job_type,
        bot_run_id=bot_run_id,
        status="pending",
        started_at=datetime.datetime.now(),
        log_messages="[]"
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job

async def update_job(
    db: AsyncSession,
    job_id: str,
    status: Optional[str] = None,
    progress: Optional[float] = None,
    current_step: Optional[str] = None,
    log_message: Optional[str] = None
) -> None:
    """Update job status and add log messages"""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    
    if job:
        if status:
            job.status = status
        if progress is not None:
            job.progress = progress
        if current_step:
            job.current_step = current_step
        if log_message:
            # Append log message to JSON array
            logs = json.loads(job.log_messages or "[]")
            logs.append({
                "timestamp": datetime.datetime.now().isoformat(),
                "message": log_message
            })
            job.log_messages = json.dumps(logs)
        
        await db.commit()

async def get_job(db: AsyncSession, job_id: str) -> Optional[Job]:
    """Get job by ID"""
    result = await db.execute(select(Job).where(Job.id == job_id))
    return result.scalar_one_or_none()

async def get_active_jobs(db: AsyncSession, bot_id: Optional[str] = None) -> List[Job]:
    """Get all active (not completed/failed/cancelled) jobs"""
    query = select(Job).where(Job.status.in_(["pending", "running"]))
    if bot_id:
        query = query.where(Job.bot_id == bot_id)
    
    result = await db.execute(query)
    return result.scalars().all()

async def cleanup_stale_jobs(db: AsyncSession) -> None:
    """Mark running jobs as failed (called on startup to handle crashes)"""
    result = await db.execute(select(Job).where(Job.status == "running"))
    stale_jobs = result.scalars().all()
    
    for job in stale_jobs:
        job.status = "failed"
        # Add log message
        logs = json.loads(job.log_messages or "[]")
        logs.append({
            "timestamp": datetime.datetime.now().isoformat(),
            "message": "Job marked as failed due to system restart"
        })
        job.log_messages = json.dumps(logs)
    
    if stale_jobs:
        await db.commit()
