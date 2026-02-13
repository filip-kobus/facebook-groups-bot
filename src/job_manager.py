"""Job management system for background task execution."""
import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional, Callable, Any
from loguru import logger

from src.database import SessionLocal, create_bot_run, update_bot_run, create_job, update_job, get_job, cleanup_stale_jobs
from src.bot_config import get_bot_config
from src.bot_processor import get_bot_processor
from src.group_processor import GroupProcessor
from src.scraper import FacebookScraper


@dataclass
class JobContext:
    """Context for a running job."""
    job_id: str
    bot_id: str
    job_type: str
    task: asyncio.Task
    status: str
    progress: float
    started_at: datetime
    bot_run_id: Optional[int] = None
    cancellation_token: Optional[asyncio.Event] = None


class JobManager:
    """Singleton job manager for orchestrating background tasks."""
    
    _instance: Optional['JobManager'] = None
    
    def __init__(self):
        """Initialize job manager."""
        self._jobs: Dict[str, JobContext] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        self._initialized = False
    
    @classmethod
    def get_instance(cls) -> 'JobManager':
        """Get or create singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    async def initialize(self):
        """Initialize job manager and cleanup stale jobs."""
        if self._initialized:
            return
        
        logger.info("Initializing JobManager...")
        
        # Clean up stale jobs from previous runs
        async with SessionLocal() as db:
            await cleanup_stale_jobs(db)
        
        # Start background cleanup task
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        
        self._initialized = True
        logger.info("JobManager initialized")
    
    async def start_job(
        self, 
        bot_id: str, 
        job_type: str, 
        triggered_by: str = "manual",
        **params
    ) -> str:
        """
        Start a new background job.
        
        Args:
            bot_id: Bot identifier
            job_type: Type of job (scrape, classify, message, invite, full)
            triggered_by: Who/what triggered the job
            **params: Additional parameters for the job
            
        Returns:
            Job ID
        """
        job_id = str(uuid.uuid4())
        
        logger.info(f"Starting job {job_id}: {job_type} for bot {bot_id}")
        
        # Create database records
        async with SessionLocal() as db:
            bot_run = await create_bot_run(db, bot_id, job_type, triggered_by)
            await create_job(db, job_id, bot_id, job_type, bot_run.id)
        
        # Create cancellation token
        cancel_event = asyncio.Event()
        
        # Create context
        context = JobContext(
            job_id=job_id,
            bot_id=bot_id,
            job_type=job_type,
            task=None,  # Will be set below
            status="pending",
            progress=0.0,
            started_at=datetime.now(),
            bot_run_id=bot_run.id,
            cancellation_token=cancel_event
        )
        
        # Start async task
        task = asyncio.create_task(
            self._run_job(context, **params)
        )
        context.task = task
        
        # Store context
        self._jobs[job_id] = context
        
        logger.info(f"Job {job_id} started")
        return job_id
    
    async def _run_job(self, context: JobContext, **params):
        """
        Execute a job in the background.
        
        Args:
            context: Job context
            **params: Job parameters
        """
        job_id = context.job_id
        bot_id = context.bot_id
        job_type = context.job_type
        
        try:
            # Update status to running
            context.status = "running"
            async with SessionLocal() as db:
                await update_job(db, job_id, status="running", current_step="Starting...")
            
            # Load bot config
            bot_config = get_bot_config(bot_id)
            
            # Execute job based on type
            if job_type == "scrape":
                await self._run_scrape_job(context, bot_config)
            elif job_type == "classify":
                await self._run_classify_job(context, bot_config)
            elif job_type == "message" or job_type == "invite":
                await self._run_process_job(context, bot_config)
            elif job_type == "full":
                await self._run_full_pipeline(context, bot_config)
            else:
                raise ValueError(f"Unknown job type: {job_type}")
            
            # Mark as completed
            context.status = "completed"
            context.progress = 100.0
            
            async with SessionLocal() as db:
                await update_job(db, job_id, status="completed", progress=100.0)
                await update_bot_run(db, context.bot_run_id, status="completed")
            
            logger.info(f"Job {job_id} completed successfully")
            
        except asyncio.CancelledError:
            logger.warning(f"Job {job_id} was cancelled")
            context.status = "cancelled"
            
            async with SessionLocal() as db:
                await update_job(db, job_id, status="cancelled")
                await update_bot_run(db, context.bot_run_id, status="cancelled")
                
        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}", exc_info=True)
            context.status = "failed"
            
            async with SessionLocal() as db:
                await update_job(db, job_id, status="failed", log_message=f"Error: {str(e)}")
                await update_bot_run(db, context.bot_run_id, status="failed", error_message=str(e))
    
    async def _run_scrape_job(self, context: JobContext, bot_config):
        """Run scraping job."""
        logger.info(f"[{context.job_id}] Starting scrape for bot {bot_config.name}")
        
        async with SessionLocal() as db:
            await update_job(db, context.job_id, current_step="Scraping groups...", log_message="Starting group scraping")
        
        # Initialize processor
        processor = GroupProcessor(bot_config)
        
        # Scrape all groups
        await processor.process_all_groups()
        
        context.progress = 100.0
        
        async with SessionLocal() as db:
            await update_job(db, context.job_id, progress=100.0, log_message="Scraping completed")
    
    async def _run_classify_job(self, context: JobContext, bot_config):
        """Run classification job."""
        logger.info(f"[{context.job_id}] Starting classification for bot {bot_config.name}")
        
        async with SessionLocal() as db:
            await update_job(db, context.job_id, current_step="Classifying posts...", log_message="Starting post classification")
            
            # Get unclassified posts
            from src.database import get_not_classified_posts
            posts = await get_not_classified_posts(db, bot_config.bot_id)
        
        if not posts:
            logger.info(f"[{context.job_id}] No posts to classify")
            async with SessionLocal() as db:
                await update_job(db, context.job_id, log_message="No posts to classify")
            return
        
        logger.info(f"[{context.job_id}] Classifying {len(posts)} posts")
        
        # Get processor
        processor = get_bot_processor(bot_config)
        
        # Classify posts
        candidates = await processor.classify_posts(posts)
        
        context.progress = 100.0
        
        async with SessionLocal() as db:
            await update_job(
                db, context.job_id, 
                progress=100.0, 
                log_message=f"Classification completed: {len(candidates)} candidates found"
            )
            await update_bot_run(db, context.bot_run_id, total_items=len(posts), processed_items=len(candidates))
    
    async def _run_process_job(self, context: JobContext, bot_config):
        """Run message/invite processing job."""
        job_type_name = "messaging" if context.job_type == "message" else "inviting"
        logger.info(f"[{context.job_id}] Starting {job_type_name} for bot {bot_config.name}")
        
        async with SessionLocal() as db:
            await update_job(
                db, context.job_id, 
                current_step=f"{job_type_name.capitalize()}...", 
                log_message=f"Starting {job_type_name}"
            )
            
            # Get uncontacted leads/candidates
            from src.database import Post, select
            result = await db.execute(
                select(Post).where(
                    Post.bot_id == bot_config.bot_id,
                    Post.is_lead == True,
                    Post.is_contacted == False
                )
            )
            candidates = result.scalars().all()
        
        if not candidates:
            logger.info(f"[{context.job_id}] No candidates to process")
            async with SessionLocal() as db:
                await update_job(db, context.job_id, log_message="No candidates to process")
            return
        
        logger.info(f"[{context.job_id}] Processing {len(candidates)} candidates")
        
        # Get processor
        processor = get_bot_processor(bot_config)
        
        # Initialize scraper
        scraper = FacebookScraper(bot_config.user_profile_dir)
        await scraper.init()
        
        try:
            # Process candidates
            processed_count = await processor.process_candidates(candidates, scraper)
            
            context.progress = 100.0
            
            async with SessionLocal() as db:
                await update_job(
                    db, context.job_id, 
                    progress=100.0, 
                    log_message=f"{job_type_name.capitalize()} completed: {processed_count} processed"
                )
                await update_bot_run(db, context.bot_run_id, total_items=len(candidates), processed_items=processed_count)
        finally:
            await scraper.close()
    
    async def _run_full_pipeline(self, context: JobContext, bot_config):
        """Run full pipeline: scrape -> classify -> process."""
        logger.info(f"[{context.job_id}] Starting full pipeline for bot {bot_config.name}")
        
        # Step 1: Scrape (0-33%)
        async with SessionLocal() as db:
            await update_job(db, context.job_id, current_step="Step 1/3: Scraping", progress=0.0)
        
        await self._run_scrape_job(context, bot_config)
        context.progress = 33.0
        
        async with SessionLocal() as db:
            await update_job(db, context.job_id, progress=33.0, log_message="Scraping completed")
        
        # Step 2: Classify (33-66%)
        async with SessionLocal() as db:
            await update_job(db, context.job_id, current_step="Step 2/3: Classifying", progress=33.0)
        
        await self._run_classify_job(context, bot_config)
        context.progress = 66.0
        
        async with SessionLocal() as db:
            await update_job(db, context.job_id, progress=66.0, log_message="Classification completed")
        
        # Step 3: Process (66-100%)
        async with SessionLocal() as db:
            await update_job(db, context.job_id, current_step="Step 3/3: Processing", progress=66.0)
        
        await self._run_process_job(context, bot_config)
        context.progress = 100.0
        
        async with SessionLocal() as db:
            await update_job(db, context.job_id, progress=100.0, log_message="Full pipeline completed")
    
    async def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a running job.
        
        Args:
            job_id: Job ID to cancel
            
        Returns:
            True if cancelled, False if not found or already finished
        """
        context = self._jobs.get(job_id)
        
        if not context:
            logger.warning(f"Job {job_id} not found")
            return False
        
        if context.status in ["completed", "failed", "cancelled"]:
            logger.warning(f"Job {job_id} already finished with status: {context.status}")
            return False
        
        logger.info(f"Cancelling job {job_id}")
        
        # Set cancellation event
        if context.cancellation_token:
            context.cancellation_token.set()
        
        # Cancel task
        if context.task and not context.task.done():
            context.task.cancel()
        
        return True
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current status of a job.
        
        Args:
            job_id: Job ID
            
        Returns:
            Job status dictionary or None if not found
        """
        context = self._jobs.get(job_id)
        
        if not context:
            return None
        
        return {
            "job_id": context.job_id,
            "bot_id": context.bot_id,
            "job_type": context.job_type,
            "status": context.status,
            "progress": context.progress,
            "started_at": context.started_at.isoformat()
        }
    
    def get_all_active_jobs(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all active jobs."""
        return {
            job_id: self.get_job_status(job_id)
            for job_id, context in self._jobs.items()
            if context.status in ["pending", "running"]
        }
    
    async def _periodic_cleanup(self):
        """Periodically clean up finished jobs from memory."""
        while True:
            try:
                await asyncio.sleep(300)  # Every 5 minutes
                
                # Remove finished jobs older than 10 minutes
                cutoff = datetime.now()
                to_remove = []
                
                for job_id, context in self._jobs.items():
                    if context.status in ["completed", "failed", "cancelled"]:
                        age = (cutoff - context.started_at).total_seconds()
                        if age > 600:  # 10 minutes
                            to_remove.append(job_id)
                
                for job_id in to_remove:
                    del self._jobs[job_id]
                    logger.debug(f"Cleaned up old job: {job_id}")
                    
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")


# Singleton instance getter
def get_job_manager() -> JobManager:
    """Get the global JobManager instance."""
    return JobManager.get_instance()
