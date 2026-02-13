"""Bot configuration loader for multi-bot architecture."""
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional
import yaml
from loguru import logger


class BotType(Enum):
    """Type of bot determining its behavior."""
    LEAD_BOT = "lead_bot"          # Finds leads, sends private messages
    INVITER_BOT = "inviter_bot"    # Finds candidates, invites to group


@dataclass
class BotConfig:
    bot_id: str
    name: str
    description: str
    bot_type: str  # Will be converted to BotType enum
    enabled: bool
    user_profile_dir: str
    groups: List[str]
    
    # Common settings
    max_posts_per_group: Optional[int] = None
    initial_scrape_days: int = 1
    force_full_rescrape: bool = False  # If True, ignore last scrape date and scrape all posts
    
    # Lead bot specific (optional for inviter bots)
    classification_prompt: Optional[str] = None
    messaging_prompt: Optional[str] = None
    max_messages_per_run: Optional[int] = None
    
    # Inviter bot specific (optional for lead bots)
    invitation_criteria_prompt: Optional[str] = None
    invitation_message_template: Optional[str] = None
    target_group: Optional[Dict[str, str]] = None
    max_invitations_per_run: Optional[int] = None
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.bot_id:
            raise ValueError("bot_id is required")
        if not self.groups:
            raise ValueError(f"Bot {self.bot_id} must have at least one group")
        if not self.user_profile_dir:
            raise ValueError(f"Bot {self.bot_id} must have user_profile_dir")
        
        # Convert string to BotType enum
        if isinstance(self.bot_type, str):
            try:
                self.bot_type = BotType(self.bot_type)
            except ValueError:
                raise ValueError(f"Invalid bot_type: {self.bot_type}. Must be 'lead_bot' or 'inviter_bot'")
        
        # Validate type-specific requirements
        if self.bot_type == BotType.LEAD_BOT:
            if not self.classification_prompt:
                raise ValueError(f"Lead bot {self.bot_id} must have classification_prompt")
            if not self.messaging_prompt:
                raise ValueError(f"Lead bot {self.bot_id} must have messaging_prompt")
        
        elif self.bot_type == BotType.INVITER_BOT:
            if not self.invitation_criteria_prompt:
                raise ValueError(f"Inviter bot {self.bot_id} must have invitation_criteria_prompt")
            if not self.target_group:
                raise ValueError(f"Inviter bot {self.bot_id} must have target_group configuration")
    
    @property
    def is_lead_bot(self) -> bool:
        """Check if this is a lead bot."""
        return self.bot_type == BotType.LEAD_BOT
    
    @property
    def is_inviter_bot(self) -> bool:
        """Check if this is an inviter bot."""
        return self.bot_type == BotType.INVITER_BOT


class BotConfigLoader:
    """Loads and manages bot configurations from YAML files."""
    
    def __init__(self, config_dir: str = "config/bots"):
        """
        Initialize the bot config loader.
        
        Args:
            config_dir: Directory containing bot YAML configuration files
        """
        self.config_dir = Path(config_dir)
        self._configs: Dict[str, BotConfig] = {}
        self._load_all_configs()
    
    def _load_all_configs(self):
        """Load all bot configurations from YAML files in config directory."""
        if not self.config_dir.exists():
            raise FileNotFoundError(f"Config directory not found: {self.config_dir}")
        
        yaml_files = list(self.config_dir.glob("*.yaml")) + list(self.config_dir.glob("*.yml"))
        
        if not yaml_files:
            raise FileNotFoundError(f"No YAML config files found in {self.config_dir}")
        
        for yaml_file in yaml_files:
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                
                config = BotConfig(**data)
                self._configs[config.bot_id] = config
                logger.info(f"Loaded config for bot: {config.bot_id} ({config.name})")
                
            except Exception as e:
                logger.error(f"Failed to load config from {yaml_file}: {e}")
                raise
    
    def get_bot(self, bot_id: str) -> BotConfig:
        """
        Get configuration for a specific bot.
        
        Args:
            bot_id: Bot identifier
            
        Returns:
            BotConfig object
            
        Raises:
            KeyError: If bot_id not found
        """
        if bot_id not in self._configs:
            available = ", ".join(self._configs.keys())
            raise KeyError(f"Bot '{bot_id}' not found. Available bots: {available}")
        
        return self._configs[bot_id]
    
    def get_all_bots(self, enabled_only: bool = True) -> List[BotConfig]:
        """
        Get all bot configurations.
        
        Args:
            enabled_only: If True, only return enabled bots
            
        Returns:
            List of BotConfig objects
        """
        configs = list(self._configs.values())
        if enabled_only:
            configs = [c for c in configs if c.enabled]
        return configs
    
    def list_bot_ids(self, enabled_only: bool = True) -> List[str]:
        """
        Get list of all bot IDs.
        
        Args:
            enabled_only: If True, only return enabled bots
            
        Returns:
            List of bot IDs
        """
        configs = self.get_all_bots(enabled_only=enabled_only)
        return [c.bot_id for c in configs]
    
    def save_bot(self, bot_id: str, config_data: dict) -> None:
        """
        Save bot configuration to YAML file.
        
        Args:
            bot_id: Bot identifier
            config_data: Configuration dictionary
        """
        yaml_path = self.config_dir / f"{bot_id}.yaml"
        
        with open(yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        
        logger.info(f"Saved config for bot: {bot_id} to {yaml_path}")
        
        # Reload configuration
        self.reload()
    
    def delete_bot(self, bot_id: str) -> None:
        """
        Delete bot configuration file.
        
        Args:
            bot_id: Bot identifier
        """
        if bot_id not in self._configs:
            raise KeyError(f"Bot '{bot_id}' not found")
        
        yaml_path = self.config_dir / f"{bot_id}.yaml"
        
        if yaml_path.exists():
            yaml_path.unlink()
            logger.info(f"Deleted config file: {yaml_path}")
        
        # Remove from memory
        del self._configs[bot_id]
    
    def reload(self) -> None:
        """Reload all configurations from disk."""
        self._configs.clear()
        self._load_all_configs()
        logger.info("Reloaded all bot configurations")


# Global loader instance
_loader: Optional[BotConfigLoader] = None


def get_loader() -> BotConfigLoader:
    """Get or create the global bot config loader instance."""
    global _loader
    if _loader is None:
        _loader = BotConfigLoader()
    return _loader


def get_bot_config(bot_id: str) -> BotConfig:
    """
    Convenience function to get a bot configuration.
    
    Args:
        bot_id: Bot identifier
        
    Returns:
        BotConfig object
    """
    return get_loader().get_bot(bot_id)


def get_all_bot_configs(enabled_only: bool = True) -> List[BotConfig]:
    """
    Convenience function to get all bot configurations.
    
    Args:
        enabled_only: If True, only return enabled bots
        
    Returns:
        List of BotConfig objects
    """
    return get_loader().get_all_bots(enabled_only=enabled_only)
