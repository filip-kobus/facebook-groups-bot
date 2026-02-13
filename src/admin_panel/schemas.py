"""Pydantic schemas for admin panel API."""
from pydantic import BaseModel
from typing import Optional, Dict, List


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


class GroupAddModel(BaseModel):
    """Model for adding a group."""
    group_id: str


class GroupScrapeDateModel(BaseModel):
    """Model for updating group scrape date."""
    scrape_date: str  # ISO format datetime string
