"""Bot processor system for handling different bot types."""
from abc import ABC, abstractmethod
from typing import List, Optional
from loguru import logger

from src.bot_config import BotConfig, BotType
from src.analyzer import LeadAnalyzer
from src.chatbot import Chatbot
from src.database import Post, SessionLocal
from src.scraper import FacebookScraper


class BaseBotProcessor(ABC):
    """Base class for bot processors."""
    
    def __init__(self, bot_config: BotConfig):
        """
        Initialize bot processor.
        
        Args:
            bot_config: Bot configuration
        """
        self.bot_config = bot_config
        self.bot_id = bot_config.bot_id
    
    @abstractmethod
    async def classify_posts(self, posts: List[Post]) -> List[Post]:
        """
        Classify posts to identify candidates.
        
        Args:
            posts: List of posts to classify
            
        Returns:
            List of posts identified as candidates
        """
        pass
    
    @abstractmethod
    async def process_candidates(self, candidates: List[Post], scraper: Optional[FacebookScraper] = None) -> int:
        """
        Process identified candidates (send messages or invite).
        
        Args:
            candidates: List of candidate posts
            scraper: Optional Facebook scraper instance
            
        Returns:
            Number of successfully processed candidates
        """
        pass
    
    @abstractmethod
    def get_classification_prompt(self) -> str:
        """Get the classification prompt for this bot type."""
        pass
    
    @abstractmethod
    def get_processing_prompt(self) -> Optional[str]:
        """Get the processing prompt for this bot type."""
        pass


class LeadBotProcessor(BaseBotProcessor):
    """Processor for lead generation bots."""
    
    def get_classification_prompt(self) -> str:
        """Get the lead classification prompt."""
        return self.bot_config.classification_prompt or ""
    
    def get_processing_prompt(self) -> Optional[str]:
        """Get the messaging prompt."""
        return self.bot_config.messaging_prompt
    
    async def classify_posts(self, posts: List[Post]) -> List[Post]:
        """
        Classify posts to identify leads using AI.
        
        Args:
            posts: List of posts to classify
            
        Returns:
            List of posts identified as leads
        """
        if not posts:
            return []
        
        logger.info(f"[{self.bot_id}] Classifying {len(posts)} posts for leads...")
        
        # Use LeadAnalyzer with bot-specific prompt
        analyzer = LeadAnalyzer(
            classification_prompt=self.get_classification_prompt()
        )
        
        batch_size = 10
        classified_posts = []
        
        async with SessionLocal() as db:
            for i in range(0, len(posts), batch_size):
                batch = posts[i:i + batch_size]
                logger.info(f"[{self.bot_id}] Analyzing batch {i//batch_size + 1}/{(len(posts)-1)//batch_size + 1}")
                
                # Analyze batch
                analyses = await analyzer.analyze_posts(batch)
                
                # Update posts with analysis results
                for post, analysis in zip(batch, analyses):
                    post.is_lead = analysis.is_lead
                    
                    if analysis.is_lead:
                        # Check for duplicates
                        from src.database import check_duplicate_lead
                        is_duplicate = await check_duplicate_lead(
                            db, post.user_id, post.content, self.bot_id
                        )
                        
                        if is_duplicate:
                            logger.info(f"[{self.bot_id}] Skipping duplicate lead from {post.author}")
                            post.is_lead = False
                        else:
                            classified_posts.append(post)
                            logger.info(f"[{self.bot_id}] ✓ Lead found: {post.author}")
                    
                    db.add(post)
                
                await db.commit()
        
        logger.info(f"[{self.bot_id}] Found {len(classified_posts)} new leads")
        return classified_posts
    
    async def process_candidates(self, candidates: List[Post], scraper: Optional[FacebookScraper] = None) -> int:
        """
        Send private messages to leads.
        
        Args:
            candidates: List of lead posts
            scraper: Facebook scraper instance
            
        Returns:
            Number of successfully sent messages
        """
        if not candidates:
            logger.info(f"[{self.bot_id}] No leads to process")
            return 0
        
        # Respect max_messages_per_run limit
        max_messages = self.bot_config.max_messages_per_run or len(candidates)
        candidates = candidates[:max_messages]
        
        logger.info(f"[{self.bot_id}] Processing {len(candidates)} leads (max: {max_messages})...")
        
        # Initialize scraper if not provided
        if scraper is None:
            scraper = FacebookScraper(self.bot_config.user_profile_dir)
            await scraper.init()
        
        # Initialize chatbot
        chatbot = Chatbot(messaging_prompt=self.get_processing_prompt())
        
        sent_count = 0
        
        async with SessionLocal() as db:
            for post in candidates:
                try:
                    logger.info(f"[{self.bot_id}] Generating message for {post.author}...")
                    
                    # Generate personalized message
                    message = await chatbot.generate_message(post.author, post.content)
                    
                    logger.info(f"[{self.bot_id}] Sending message to {post.author}...")
                    
                    # Send message via Messenger
                    await scraper.send_message(post.user_id, [message])
                    
                    # Mark as contacted
                    post.is_contacted = True
                    db.add(post)
                    
                    # Save message to database
                    from src.database import Message
                    msg_record = Message(
                        content=message,
                        post_id=post.post_id
                    )
                    db.add(msg_record)
                    
                    await db.commit()
                    
                    sent_count += 1
                    logger.info(f"[{self.bot_id}] ✓ Message sent to {post.author} ({sent_count}/{len(candidates)})")
                    
                    # Delay between messages
                    import asyncio
                    await asyncio.sleep(5)
                    
                except Exception as e:
                    logger.error(f"[{self.bot_id}] Failed to send message to {post.author}: {e}")
                    continue
        
        logger.info(f"[{self.bot_id}] Sent {sent_count} messages")
        return sent_count


class InviterBotProcessor(BaseBotProcessor):
    """Processor for group invitation bots."""
    
    def get_classification_prompt(self) -> str:
        """Get the invitation criteria prompt."""
        return self.bot_config.invitation_criteria_prompt or ""
    
    def get_processing_prompt(self) -> Optional[str]:
        """Get the invitation message template."""
        return self.bot_config.invitation_message_template
    
    async def classify_posts(self, posts: List[Post]) -> List[Post]:
        """
        Classify posts to identify invitation candidates.
        
        Args:
            posts: List of posts to classify
            
        Returns:
            List of posts identified as candidates
        """
        if not posts:
            return []
        
        logger.info(f"[{self.bot_id}] Classifying {len(posts)} posts for invitation candidates...")
        
        # Use LeadAnalyzer with inviter-specific prompt
        # (reusing LeadAnalyzer but with different prompt)
        analyzer = LeadAnalyzer(
            classification_prompt=self.get_classification_prompt()
        )
        
        batch_size = 10
        classified_posts = []
        
        async with SessionLocal() as db:
            for i in range(0, len(posts), batch_size):
                batch = posts[i:i + batch_size]
                logger.info(f"[{self.bot_id}] Analyzing batch {i//batch_size + 1}/{(len(posts)-1)//batch_size + 1}")
                
                # Analyze batch
                analyses = await analyzer.analyze_posts(batch)
                
                # Update posts with analysis results
                for post, analysis in zip(batch, analyses):
                    post.is_lead = analysis.is_lead  # Reusing is_lead field for candidates
                    
                    if analysis.is_lead:
                        # Check for duplicates
                        from src.database import check_duplicate_lead
                        is_duplicate = await check_duplicate_lead(
                            db, post.user_id, post.content, self.bot_id
                        )
                        
                        if is_duplicate:
                            logger.info(f"[{self.bot_id}] Skipping duplicate candidate from {post.author}")
                            post.is_lead = False
                        else:
                            classified_posts.append(post)
                            logger.info(f"[{self.bot_id}] ✓ Candidate found: {post.author}")
                    
                    db.add(post)
                
                await db.commit()
        
        logger.info(f"[{self.bot_id}] Found {len(classified_posts)} invitation candidates")
        return classified_posts
    
    async def process_candidates(self, candidates: List[Post], scraper: Optional[FacebookScraper] = None) -> int:
        """
        Invite candidates to target group.
        
        Args:
            candidates: List of candidate posts
            scraper: Facebook scraper instance
            
        Returns:
            Number of successful invitations
        """
        if not candidates:
            logger.info(f"[{self.bot_id}] No candidates to invite")
            return 0
        
        # Respect max_invitations_per_run limit
        max_invitations = self.bot_config.max_invitations_per_run or len(candidates)
        candidates = candidates[:max_invitations]
        
        logger.info(f"[{self.bot_id}] Processing {len(candidates)} invitation candidates (max: {max_invitations})...")
        
        # Initialize scraper if not provided
        if scraper is None:
            scraper = FacebookScraper(self.bot_config.user_profile_dir)
            await scraper.init()
        
        # Import GroupInviter
        from src.group_inviter import GroupInviter
        inviter = GroupInviter(scraper)
        
        target_group = self.bot_config.target_group
        if not target_group or 'id' not in target_group:
            logger.error(f"[{self.bot_id}] No target group configured")
            return 0
        
        invited_count = 0
        
        async with SessionLocal() as db:
            for post in candidates:
                try:
                    logger.info(f"[{self.bot_id}] Inviting {post.author} to group...")
                    
                    # Get invitation message (optional)
                    message = None
                    if self.bot_config.invitation_message_template:
                        # Could use AI to personalize, or use template
                        message = self.bot_config.invitation_message_template
                    
                    # Invite user to group
                    success = await inviter.invite_user_to_group(
                        user_id=post.user_id,
                        group_id=target_group['id'],
                        message=message
                    )
                    
                    if success:
                        # Mark as contacted (reusing field)
                        post.is_contacted = True
                        db.add(post)
                        
                        # Save action to database (reuse Message table)
                        from src.database import Message
                        msg_record = Message(
                            content=f"Invited to group: {target_group.get('name', target_group['id'])}",
                            post_id=post.post_id
                        )
                        db.add(msg_record)
                        
                        await db.commit()
                        
                        invited_count += 1
                        logger.info(f"[{self.bot_id}] ✓ Invited {post.author} ({invited_count}/{len(candidates)})")
                    
                    # Delay between invitations
                    import asyncio
                    await asyncio.sleep(5)
                    
                except Exception as e:
                    logger.error(f"[{self.bot_id}] Failed to invite {post.author}: {e}")
                    continue
        
        logger.info(f"[{self.bot_id}] Sent {invited_count} invitations")
        return invited_count


def get_bot_processor(bot_config: BotConfig) -> BaseBotProcessor:
    """
    Factory function to get appropriate bot processor.
    
    Args:
        bot_config: Bot configuration
        
    Returns:
        Bot processor instance
    """
    if bot_config.bot_type == BotType.LEAD_BOT:
        return LeadBotProcessor(bot_config)
    elif bot_config.bot_type == BotType.INVITER_BOT:
        return InviterBotProcessor(bot_config)
    else:
        raise ValueError(f"Unknown bot type: {bot_config.bot_type}")
