from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from sqlalchemy import select, delete, func
from sqlalchemy.orm import selectinload
import math

from src.database import SessionLocal, Post, Group, Message

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
    
    return HTMLResponse(content="", status_code=200)


@app.delete("/api/leads/{post_id}")
async def delete_lead(post_id: str):
    async with SessionLocal() as session:
        await session.execute(
            delete(Post).where(Post.post_id == post_id)
        )
        await session.commit()
    
    return HTMLResponse(content="", status_code=200)


@app.get("/api/leads")
async def get_leads(page: int = Query(1, ge=1), per_page: int = Query(20, ge=1, le=100)):
    async with SessionLocal() as session:
        # Zlicz wszystkie leady
        count_result = await session.execute(
            select(func.count()).select_from(Post)
            .where(Post.is_lead == True, Post.is_contacted == False)
        )
        total = count_result.scalar()
        
        # Pobierz dane z paginacją
        offset = (page - 1) * per_page
        result = await session.execute(
            select(Post)
            .where(Post.is_lead == True, Post.is_contacted == False)
            .order_by(Post.created_at.desc())
            .limit(per_page)
            .offset(offset)
        )
        leads = result.scalars().all()
    
    return JSONResponse({
        "data": [
            {
                "post_id": lead.post_id,
                "author": lead.author,
                "content": lead.content[:200] + "..." if len(lead.content) > 200 else lead.content,
                "created_at": lead.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "group_id": lead.group_id,
            }
            for lead in leads
        ],
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": math.ceil(total / per_page) if total > 0 else 0
    })


@app.get("/api/groups")
async def get_groups(page: int = Query(1, ge=1), per_page: int = Query(20, ge=1, le=100)):
    async with SessionLocal() as session:
        # Zlicz wszystkie grupy
        count_result = await session.execute(
            select(func.count()).select_from(Group)
        )
        total = count_result.scalar()
        
        # Pobierz dane z paginacją
        offset = (page - 1) * per_page
        result = await session.execute(
            select(Group)
            .order_by(Group.group_id)
            .limit(per_page)
            .offset(offset)
        )
        groups = result.scalars().all()
    
    return JSONResponse({
        "data": [
            {
                "group_id": group.group_id,
                "last_scrape_date": group.last_scrape_date.strftime("%Y-%m-%d %H:%M:%S") if group.last_scrape_date else "Never",
                "last_run_error": group.last_run_error,
                "last_error_message": group.last_error_message or "",
            }
            for group in groups
        ],
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": math.ceil(total / per_page) if total > 0 else 0
    })


@app.get("/api/contacted")
async def get_contacted(page: int = Query(1, ge=1), per_page: int = Query(20, ge=1, le=100)):
    async with SessionLocal() as session:
        # Zlicz wszystkie skontaktowane
        count_result = await session.execute(
            select(func.count()).select_from(Post)
            .where(Post.is_lead == True, Post.is_contacted == True)
        )
        total = count_result.scalar()
        
        # Pobierz dane z paginacją
        offset = (page - 1) * per_page
        result = await session.execute(
            select(Post)
            .where(Post.is_lead == True, Post.is_contacted == True)
            .order_by(Post.created_at.desc())
            .limit(per_page)
            .offset(offset)
        )
        contacted = result.scalars().all()
    
    return JSONResponse({
        "data": [
            {
                "post_id": lead.post_id,
                "author": lead.author,
                "content": lead.content[:200] + "..." if len(lead.content) > 200 else lead.content,
                "created_at": lead.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "group_id": lead.group_id,
            }
            for lead in contacted
        ],
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": math.ceil(total / per_page) if total > 0 else 0
    })


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
    
    return HTMLResponse(content="", status_code=200)


@app.get("/api/messages")
async def get_messages(page: int = Query(1, ge=1), per_page: int = Query(20, ge=1, le=100)):
    async with SessionLocal() as session:
        # Zlicz wszystkie wiadomości
        count_result = await session.execute(
            select(func.count()).select_from(Message)
            .join(Post)
        )
        total = count_result.scalar()
        
        # Pobierz dane z paginacją
        offset = (page - 1) * per_page
        result = await session.execute(
            select(Message)
            .options(selectinload(Message.post))
            .join(Post)
            .order_by(Message.sent_at.desc())
            .limit(per_page)
            .offset(offset)
        )
        messages = result.scalars().all()
        
        # Przetwarzaj dane wewnątrz sesji
        messages_data = [
            {
                "id": message.id,
                "content": message.content,
                "sent_at": message.sent_at.strftime("%Y-%m-%d %H:%M:%S"),
                "post_id": message.post_id,
                "post_author": message.post.author if message.post else "Unknown",
                "post_content": (message.post.content[:100] + "...") if message.post and len(message.post.content) > 100 else (message.post.content if message.post else ""),
                "group_id": message.post.group_id if message.post else "Unknown"
            }
            for message in messages
        ]
    
    return JSONResponse({
        "data": messages_data,
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": math.ceil(total / per_page) if total > 0 else 0
    })

