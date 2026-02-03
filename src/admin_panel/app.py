from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from sqlalchemy import select, delete

from src.database import SessionLocal, Post, Group

app = FastAPI()
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    async with SessionLocal() as session:
        leads_result = await session.execute(
            select(Post)
            .where(Post.is_lead == True, Post.is_contacted == False)
            .order_by(Post.created_at.desc())
        )
        leads = leads_result.scalars().all()
        
        contacted_result = await session.execute(
            select(Post)
            .where(Post.is_lead == True, Post.is_contacted == True)
            .order_by(Post.created_at.desc())
        )
        contacted = contacted_result.scalars().all()
        
        groups_result = await session.execute(
            select(Group).order_by(Group.group_id)
        )
        groups = groups_result.scalars().all()
    
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "leads": leads, "contacted": contacted, "groups": groups}
    )


@app.post("/api/leads/{post_id}/unmark")
async def unmark_lead(post_id: str):
    async with SessionLocal() as session:
        result = await session.execute(
            select(Post).where(Post.post_id == post_id)
        )
        post = result.scalar_one_or_none()
        
        if post:
            post.is_lead = False
            await session.commit()
    
    return {"success": True}


@app.delete("/api/leads/{post_id}")
async def delete_lead(post_id: str):
    async with SessionLocal() as session:
        await session.execute(
            delete(Post).where(Post.post_id == post_id)
        )
        await session.commit()
    
    return {"success": True}


@app.get("/api/leads")
async def get_leads():
    async with SessionLocal() as session:
        result = await session.execute(
            select(Post)
            .where(Post.is_lead == True, Post.is_contacted == False)
            .order_by(Post.created_at.desc())
        )
        leads = result.scalars().all()
    
    return [
        {
            "post_id": lead.post_id,
            "author": lead.author,
            "content": lead.content[:200] + "..." if len(lead.content) > 200 else lead.content,
            "created_at": lead.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "group_id": lead.group_id,
        }
        for lead in leads
    ]


@app.get("/api/groups")
async def get_groups():
    async with SessionLocal() as session:
        result = await session.execute(select(Group).order_by(Group.group_id))
        groups = result.scalars().all()
    
    return [
        {
            "group_id": group.group_id,
            "last_scrape_date": group.last_scrape_date.strftime("%Y-%m-%d %H:%M:%S") if group.last_scrape_date else "Never",
            "last_run_error": group.last_run_error,
            "last_error_message": group.last_error_message or "",
        }
        for group in groups
    ]


@app.get("/api/contacted")
async def get_contacted():
    async with SessionLocal() as session:
        result = await session.execute(
            select(Post)
            .where(Post.is_lead == True, Post.is_contacted == True)
            .order_by(Post.created_at.desc())
        )
        contacted = result.scalars().all()
    
    return [
        {
            "post_id": lead.post_id,
            "author": lead.author,
            "content": lead.content[:200] + "..." if len(lead.content) > 200 else lead.content,
            "created_at": lead.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "group_id": lead.group_id,
        }
        for lead in contacted
    ]


@app.post("/api/contacted/{post_id}/reset")
async def reset_contact(post_id: str):
    async with SessionLocal() as session:
        result = await session.execute(
            select(Post).where(Post.post_id == post_id)
        )
        post = result.scalar_one_or_none()
        
        if post:
            post.is_contacted = False
            await session.commit()
    
    return {"success": True}
