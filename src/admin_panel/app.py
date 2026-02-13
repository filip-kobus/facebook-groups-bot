from fastapi import FastAPI, Request, Query, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from sqlalchemy import select, delete, func
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import math
import asyncio
import json
from loguru import logger

from src.database import SessionLocal, Post, Group, Message, BotRun, Job, get_recent_bot_runs, get_active_jobs, get_job as db_get_job
from src.bot_config import get_loader, BotType
from src.job_manager import get_job_manager
import yaml

app = FastAPI()
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, bot_id: str = Query(None)):
    async with SessionLocal() as session:
        # Build queries with optional bot filter
        leads_query = select(Post).where(Post.is_lead == True, Post.is_contacted == False)
        contacted_query = select(Post).where(Post.is_lead == True, Post.is_contacted == True)
        groups_query = select(Group)
        
        if bot_id:
            leads_query = leads_query.where(Post.bot_id == bot_id)
            contacted_query = contacted_query.where(Post.bot_id == bot_id)
            groups_query = groups_query.where(Group.bot_id == bot_id)
        
        leads_result = await session.execute(leads_query.order_by(Post.created_at.desc()))
        leads = leads_result.scalars().all()
        
        contacted_result = await session.execute(contacted_query.order_by(Post.created_at.desc()))
        contacted = contacted_result.scalars().all()
        
        groups_result = await session.execute(groups_query.order_by(Group.group_id))
        groups = groups_result.scalars().all()
        
        # Get unique bot_ids for filter
        bots_result = await session.execute(select(Post.bot_id).distinct())
        available_bots = [b for b in bots_result.scalars().all() if b]
    
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "leads": leads, "contacted": contacted, "groups": groups,
         "bot_id": bot_id, "available_bots": available_bots}
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
async def get_leads(page: int = Query(1, ge=1), per_page: int = Query(20, ge=1, le=100), bot_id: str = Query(None)):
    async with SessionLocal() as session:
        # Zlicz wszystkie leady
        count_query = select(func.count()).select_from(Post).where(
            Post.is_lead == True, Post.is_contacted == False
        )
        if bot_id:
            count_query = count_query.where(Post.bot_id == bot_id)
        
        count_result = await session.execute(count_query)
        total = count_result.scalar()
        
        # Pobierz dane z paginacją
        offset = (page - 1) * per_page
        leads_query = select(Post).where(
            Post.is_lead == True, Post.is_contacted == False
        ).order_by(Post.created_at.desc()).limit(per_page).offset(offset)
        
        if bot_id:
            leads_query = leads_query.where(Post.bot_id == bot_id)
        
        result = await session.execute(leads_query)
        leads = result.scalars().all()
    
    return JSONResponse({
        "data": [
            {
                "post_id": lead.post_id,
                "author": lead.author,
                "content": lead.content[:200] + "..." if len(lead.content) > 200 else lead.content,
                "created_at": lead.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "group_id": lead.group_id,
                "bot_id": lead.bot_id,
            }
            for lead in leads
        ],
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": math.ceil(total / per_page) if total > 0 else 0
    })


@app.get("/api/groups")
async def get_groups(page: int = Query(1, ge=1), per_page: int = Query(20, ge=1, le=100), bot_id: str = Query(None)):
    async with SessionLocal() as session:
        # Build query with optional bot filter
        groups_query = select(Group)
        if bot_id:
            groups_query = groups_query.where(Group.bot_id == bot_id)
        
        # Zlicz wszystkie grupy
        count_query = select(func.count()).select_from(Group)
        if bot_id:
            count_query = count_query.where(Group.bot_id == bot_id)
        
        count_result = await session.execute(count_query)
        total = count_result.scalar()
        
        # Pobierz dane z paginacją
        offset = (page - 1) * per_page
        result = await session.execute(
            groups_query
            .order_by(Group.group_id)
            .limit(per_page)
            .offset(offset)
        )
        groups = result.scalars().all()
    
    return JSONResponse({
        "data": [
            {
                "group_id": group.group_id,
                "bot_id": group.bot_id,
                "last_scrape_date": group.last_scrape_date.strftime("%Y-%m-%d %H:%M:%S") if group.last_scrape_date else "Never",
                "last_scrape_date_iso": group.last_scrape_date.isoformat() if group.last_scrape_date else "",
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


# ========== Bot Management API ==========

class BotConfigModel(BaseModel):
    """Pydantic model for bot configuration."""
    bot_id: str
    name: str
    description: str
    bot_type: str
    enabled: bool
    user_profile_dir: str
    groups: List[str]
    max_posts_per_group: Optional[int] = None
    initial_scrape_days: int = 1
    classification_prompt: Optional[str] = None
    messaging_prompt: Optional[str] = None
    max_messages_per_run: Optional[int] = None
    invitation_criteria_prompt: Optional[str] = None
    invitation_message_template: Optional[str] = None
    target_group: Optional[Dict[str, str]] = None
    max_invitations_per_run: Optional[int] = None


@app.get("/api/bots")
async def get_bots(enabled_only: bool = Query(False)):
    """Get all bot configurations."""
    try:
        loader = get_loader()
        bots = loader.get_all_bots(enabled_only=enabled_only)
        
        return JSONResponse({
            "bots": [
                {
                    "bot_id": bot.bot_id,
                    "name": bot.name,
                    "description": bot.description,
                    "bot_type": bot.bot_type.value,
                    "enabled": bot.enabled,
                    "groups_count": len(bot.groups)
                }
                for bot in bots
            ]
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/bots/{bot_id}")
async def get_bot(bot_id: str):
    """Get detailed bot configuration."""
    try:
        loader = get_loader()
        bot = loader.get_bot(bot_id)
        
        return JSONResponse({
            "bot_id": bot.bot_id,
            "name": bot.name,
            "description": bot.description,
            "bot_type": bot.bot_type.value,
            "enabled": bot.enabled,
            "user_profile_dir": bot.user_profile_dir,
            "groups": bot.groups,
            "max_posts_per_group": bot.max_posts_per_group,
            "initial_scrape_days": bot.initial_scrape_days,
            "classification_prompt": bot.classification_prompt,
            "messaging_prompt": bot.messaging_prompt,
            "max_messages_per_run": bot.max_messages_per_run,
            "invitation_criteria_prompt": bot.invitation_criteria_prompt,
            "invitation_message_template": bot.invitation_message_template,
            "target_group": bot.target_group,
            "max_invitations_per_run": bot.max_invitations_per_run
        })
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/bots")
async def create_bot(config: BotConfigModel):
    """Create a new bot configuration."""
    try:
        loader = get_loader()
        
        # Convert to dict for YAML
        config_dict = config.dict(exclude_none=True)
        
        # Save to YAML file
        loader.save_bot(config.bot_id, config_dict)
        
        return JSONResponse({"message": f"Bot {config.bot_id} created successfully"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/bots/{bot_id}")
async def update_bot(bot_id: str, config: BotConfigModel):
    """Update bot configuration."""
    try:
        if bot_id != config.bot_id:
            raise HTTPException(status_code=400, detail="Bot ID mismatch")
        
        loader = get_loader()
        
        # Convert to dict for YAML
        config_dict = config.dict(exclude_none=True)
        
        # Save to YAML file
        loader.save_bot(bot_id, config_dict)
        
        return JSONResponse({"message": f"Bot {bot_id} updated successfully"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/bots/{bot_id}")
async def delete_bot(bot_id: str):
    """Delete bot configuration."""
    try:
        loader = get_loader()
        loader.delete_bot(bot_id)
        
        return JSONResponse({"message": f"Bot {bot_id} deleted successfully"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== Group Management API ==========

@app.get("/api/bots/{bot_id}/groups")
async def get_bot_groups(bot_id: str):
    """Get groups for a specific bot."""
    try:
        loader = get_loader()
        bot = loader.get_bot(bot_id)
        
        # Get group status from database
        async with SessionLocal() as session:
            result = await session.execute(
                select(Group).where(Group.bot_id == bot_id)
            )
            db_groups = {g.group_id: g for g in result.scalars().all()}
        
        groups_data = []
        for group_id in bot.groups:
            db_group = db_groups.get(group_id)
            groups_data.append({
                "group_id": group_id,
                "last_scrape_date": db_group.last_scrape_date.isoformat() if db_group and db_group.last_scrape_date else None,
                "last_run_error": db_group.last_run_error if db_group else False,
                "last_error_message": db_group.last_error_message if db_group else None
            })
        
        return JSONResponse({"groups": groups_data})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class GroupAddModel(BaseModel):
    """Model for adding a group."""
    group_id: str


class GroupScrapeDateModel(BaseModel):
    """Model for updating group scrape date."""
    scrape_date: str  # ISO format datetime string


@app.patch("/api/groups/{bot_id}/{group_id}/scrape-date")
async def update_group_scrape_date(bot_id: str, group_id: str, date_data: GroupScrapeDateModel):
    """Update last_scrape_date for a specific group."""
    try:
        from datetime import datetime
        
        # Parse the date
        try:
            new_date = datetime.fromisoformat(date_data.scrape_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)")
        
        async with SessionLocal() as session:
            result = await session.execute(
                select(Group).where(Group.group_id == group_id, Group.bot_id == bot_id)
            )
            group = result.scalar_one_or_none()
            
            if not group:
                raise HTTPException(status_code=404, detail=f"Group {group_id} not found for bot {bot_id}")
            
            group.last_scrape_date = new_date
            await session.commit()
        
        return JSONResponse({
            "message": "Scrape date updated successfully",
            "group_id": group_id,
            "bot_id": bot_id,
            "new_scrape_date": new_date.isoformat()
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/bots/{bot_id}/groups")
async def add_bot_group(bot_id: str, group_data: GroupAddModel):
    """Add a group to bot configuration."""
    try:
        loader = get_loader()
        bot = loader.get_bot(bot_id)
        
        # Add group to bot's groups list
        if group_data.group_id not in bot.groups:
            bot.groups.append(group_data.group_id)
            
            # Save updated config
            config_dict = {
                "bot_id": bot.bot_id,
                "name": bot.name,
                "description": bot.description,
                "bot_type": bot.bot_type.value,
                "enabled": bot.enabled,
                "user_profile_dir": bot.user_profile_dir,
                "groups": bot.groups,
                "max_posts_per_group": bot.max_posts_per_group,
                "initial_scrape_days": bot.initial_scrape_days,
                "classification_prompt": bot.classification_prompt,
                "messaging_prompt": bot.messaging_prompt,
                "max_messages_per_run": bot.max_messages_per_run,
                "invitation_criteria_prompt": bot.invitation_criteria_prompt,
                "invitation_message_template": bot.invitation_message_template,
                "target_group": bot.target_group,
                "max_invitations_per_run": bot.max_invitations_per_run
            }
            
            # Remove None values
            config_dict = {k: v for k, v in config_dict.items() if v is not None}
            
            loader.save_bot(bot_id, config_dict)
            
            return JSONResponse({"message": f"Group {group_data.group_id} added to bot {bot_id}"})
        else:
            return JSONResponse({"message": f"Group {group_data.group_id} already exists"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/bots/{bot_id}/groups/{group_id}")
async def remove_bot_group(bot_id: str, group_id: str):
    """Remove a group from bot configuration."""
    try:
        loader = get_loader()
        bot = loader.get_bot(bot_id)
        
        # Remove group from bot's groups list
        if group_id in bot.groups:
            bot.groups.remove(group_id)
            
            # Save updated config (same as add_bot_group)
            config_dict = {
                "bot_id": bot.bot_id,
                "name": bot.name,
                "description": bot.description,
                "bot_type": bot.bot_type.value,
                "enabled": bot.enabled,
                "user_profile_dir": bot.user_profile_dir,
                "groups": bot.groups,
                "max_posts_per_group": bot.max_posts_per_group,
                "initial_scrape_days": bot.initial_scrape_days,
                "classification_prompt": bot.classification_prompt,
                "messaging_prompt": bot.messaging_prompt,
                "max_messages_per_run": bot.max_messages_per_run,
                "invitation_criteria_prompt": bot.invitation_criteria_prompt,
                "invitation_message_template": bot.invitation_message_template,
                "target_group": bot.target_group,
                "max_invitations_per_run": bot.max_invitations_per_run
            }
            
            # Remove None values
            config_dict = {k: v for k, v in config_dict.items() if v is not None}
            
            loader.save_bot(bot_id, config_dict)
            
            return JSONResponse({"message": f"Group {group_id} removed from bot {bot_id}"})
        else:
            raise HTTPException(status_code=404, detail=f"Group {group_id} not found in bot {bot_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== Job Control API ==========

@app.post("/api/bots/{bot_id}/scrape")
async def start_scrape_job(bot_id: str):
    """Start scraping job for a bot."""
    try:
        job_manager = get_job_manager()
        await job_manager.initialize()
        
        job_id = await job_manager.start_job(bot_id, "scrape", triggered_by="api")
        
        return JSONResponse({"job_id": job_id, "message": "Scraping job started"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/bots/{bot_id}/classify")
async def start_classify_job(bot_id: str):
    """Start classification job for a bot."""
    try:
        job_manager = get_job_manager()
        await job_manager.initialize()
        
        job_id = await job_manager.start_job(bot_id, "classify", triggered_by="api")
        
        return JSONResponse({"job_id": job_id, "message": "Classification job started"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/bots/{bot_id}/process")
async def start_process_job(bot_id: str):
    """Start processing job (messages/invites) for a bot."""
    try:
        job_manager = get_job_manager()
        await job_manager.initialize()
        
        # Determine job type based on bot type
        loader = get_loader()
        bot = loader.get_bot(bot_id)
        
        job_type = "message" if bot.bot_type == BotType.LEAD_BOT else "invite"
        
        job_id = await job_manager.start_job(bot_id, job_type, triggered_by="api")
        
        return JSONResponse({"job_id": job_id, "message": f"{job_type.capitalize()} job started"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/bots/{bot_id}/run-full")
async def start_full_run(bot_id: str):
    """Start full pipeline for a bot."""
    try:
        job_manager = get_job_manager()
        await job_manager.initialize()
        
        job_id = await job_manager.start_job(bot_id, "full", triggered_by="api")
        
        return JSONResponse({"job_id": job_id, "message": "Full pipeline started"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Get status of a specific job."""
    try:
        # Check in-memory first
        job_manager = get_job_manager()
        status = job_manager.get_job_status(job_id)
        
        if status:
            return JSONResponse(status)
        
        # Check database
        async with SessionLocal() as session:
            job = await db_get_job(session, job_id)
            
            if not job:
                raise HTTPException(status_code=404, detail="Job not found")
            
            return JSONResponse({
                "job_id": job.id,
                "bot_id": job.bot_id,
                "job_type": job.job_type,
                "status": job.status,
                "progress": job.progress,
                "started_at": job.started_at.isoformat(),
                "current_step": job.current_step,
                "logs": json.loads(job.log_messages) if job.log_messages else []
            })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    """Cancel a running job."""
    try:
        job_manager = get_job_manager()
        success = await job_manager.cancel_job(job_id)
        
        if success:
            return JSONResponse({"message": f"Job {job_id} cancelled"})
        else:
            raise HTTPException(status_code=404, detail="Job not found or already finished")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/jobs/active")
async def get_active_jobs_api(bot_id: Optional[str] = Query(None)):
    """Get all active jobs."""
    try:
        job_manager = get_job_manager()
        jobs = job_manager.get_all_active_jobs()
        
        # Filter by bot_id if provided
        if bot_id:
            jobs = {jid: j for jid, j in jobs.items() if j["bot_id"] == bot_id}
        
        return JSONResponse({"jobs": list(jobs.values())})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/jobs/stream")
async def jobs_stream():
    """Server-Sent Events endpoint for real-time job updates."""
    async def event_generator():
        """Generate SSE events for job updates."""
        job_manager = get_job_manager()
        
        while True:
            try:
                # Get all active jobs
                jobs = job_manager.get_all_active_jobs()
                
                # Send update
                if jobs:
                    data = json.dumps({"jobs": list(jobs.values())})
                    yield f"data: {data}\n\n"
                
                # Wait before next update
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Error in SSE stream: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                await asyncio.sleep(5)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.get("/api/bot-runs")
async def get_bot_runs_api(bot_id: Optional[str] = Query(None), limit: int = Query(10, ge=1, le=100)):
    """Get recent bot run history."""
    try:
        async with SessionLocal() as session:
            runs = await get_recent_bot_runs(session, bot_id, limit)
            
            return JSONResponse({
                "runs": [
                    {
                        "id": run.id,
                        "bot_id": run.bot_id,
                        "run_type": run.run_type,
                        "status": run.status,
                        "started_at": run.started_at.isoformat(),
                        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
                        "total_items": run.total_items,
                        "processed_items": run.processed_items,
                        "error_message": run.error_message,
                        "triggered_by": run.triggered_by
                    }
                    for run in runs
                ]
            })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== Initialize on startup ==========

@app.on_event("startup")
async def startup_event():
    """Initialize job manager on startup."""
    job_manager = get_job_manager()
    await job_manager.initialize()


