from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy import Column, ForeignKey, Integer, String, Boolean, DateTime, select, desc, UniqueConstraint
from src.groups import groups_ids
from typing import Optional, List
from rapidfuzz import fuzz
import datetime

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

async def sync_groups_from_config(db: AsyncSession, bot_id: str, group_ids: List[str], initial_scrape_days: int = 1) -> None:
    from loguru import logger
    
    result = await db.execute(
        select(Group).where(Group.bot_id == bot_id)
    )
    existing_groups = {g.group_id: g for g in result.scalars().all()}
    
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
    
    await db.commit()
    logger.info(f"Group sync complete for bot {bot_id}: {len(group_ids)} groups in config")
