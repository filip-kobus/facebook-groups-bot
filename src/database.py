from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy import Column, ForeignKey, Integer, String, Boolean, DateTime, select, desc
from src.groups import groups_ids
from typing import Optional
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
    group_id = Column(String, ForeignKey("group.group_id"))
    group = relationship("Group", back_populates="posts")

class Group(Base):
    __tablename__ = "group"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(String, unique=True, index=True)
    last_scrape_date = Column(DateTime, default=datetime.datetime.now)
    posts = relationship("Post", back_populates="group")

class Lead(Base):
    __tablename__ = "lead"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(String, unique=True, index=True)
    is_contacted = Column(Boolean, default=False)
    messages = relationship("Message", back_populates="lead")

class Message(Base):
    __tablename__ = "message"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(String)
    sent_at = Column(DateTime, default=datetime.datetime.now)
    lead_id = Column(Integer, ForeignKey("lead.id"))
    lead = relationship("Lead", back_populates="messages")

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as session:
        one_day_ago = datetime.datetime.now() - datetime.timedelta(days=1)
        for group_id in groups_ids:
            exists = await session.execute(
                select(Group).where(Group.group_id == group_id)
            )
            if not exists.scalar_one_or_none():
                session.add(Group(group_id=group_id, last_scrape_date=one_day_ago))
        await session.commit()

async def get_db():
    async with SessionLocal() as session:
        yield session

async def get_last_scraping_date(db: AsyncSession, group_id: str) -> Optional[datetime.datetime]:
    """Retrieve the latest post date for a given group from the database."""
    result = await db.execute(
        select(Group.last_scrape_date)
        .where(Group.group_id == group_id)
        .limit(1)
    )
    return result.scalar_one_or_none()

async def get_groups(db: AsyncSession):
    result = await db.execute(select(Group.group_id))
    return result.scalars().all()

async def get_not_classified_posts(db: AsyncSession):
    result = await db.execute(select(Post).where(Post.is_lead == None))
    return result.scalars().all()

async def check_duplicate_post(db: AsyncSession, post: Post) -> bool:
    """
    Check if exact same post exists.
    """
    result = await db.execute(
        select(Post).where(Post.content == post.content and Post.user_id == post.user_id)
    )
    existing_post = result.scalar_one_or_none()
    return existing_post is not None

async def check_duplicate_lead(db: AsyncSession, user_id: str, new_content: str, similarity_threshold: float = 80.0) -> bool:
    """
    Check if the user already has a lead with similar content.
    """
    # Get all posts from this user that are marked as leads
    result = await db.execute(
        select(Post)
        .join(Lead, Post.post_id == Lead.post_id)
        .where(Post.user_id == user_id)
    )
    existing_lead_posts = result.scalars().all()
    
    if not existing_lead_posts:
        return False
    
    # Check similarity with each existing lead post
    for existing_post in existing_lead_posts:
        if not existing_post.content or not new_content:
            continue
            
        # Use partial ratio for better matching of similar text
        similarity_score = fuzz.partial_ratio(existing_post.content.lower(), new_content.lower())
        
        if similarity_score >= similarity_threshold:
            return True
    
    return False