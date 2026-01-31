from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy import Column, ForeignKey, Integer, String, Boolean, DateTime, select, desc
from groups import groups_ids
from typing import Optional
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
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    is_lead = Column(Boolean, default=None, nullable=True)
    group_id = Column(String, ForeignKey("group.group_id"))
    group = relationship("Group", back_populates="posts")

class Group(Base):
    __tablename__ = "group"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(String, unique=True, index=True)
    last_scrape_date = Column(DateTime, default=datetime.datetime.utcnow)
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
    sent_at = Column(DateTime, default=datetime.datetime.utcnow)
    lead_id = Column(Integer, ForeignKey("lead.id"))
    lead = relationship("Lead", back_populates="messages")

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as session:
        one_day_ago = datetime.datetime.utcnow() - datetime.timedelta(days=1)
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