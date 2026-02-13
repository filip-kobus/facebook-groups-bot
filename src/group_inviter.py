"""Group invitation functionality for inviter bots."""
import asyncio
import random
from loguru import logger
from typing import Optional

from src.scraper import FacebookScraper


class GroupInviter:
    """Handles inviting users to Facebook groups."""
    
    def __init__(self, scraper: FacebookScraper):
        """
        Initialize group inviter.
        
        Args:
            scraper: FacebookScraper instance to use
        """
        self.scraper = scraper
        self.page = scraper.page
    
    async def invite_user_to_group(
        self, 
        user_id: str, 
        group_id: str, 
        message: Optional[str] = None
    ) -> bool:
        """
        Invite a user to a Facebook group.
        
        Args:
            user_id: Facebook user ID
            group_id: Facebook group ID
            message: Optional personal message to include
            
        Returns:
            True if invitation sent successfully, False otherwise
        """
        try:
            logger.info(f"Inviting user {user_id} to group {group_id}")
            
            # Navigate to group
            group_url = f"https://www.facebook.com/groups/{group_id}"
            await self.page.goto(group_url, wait_until="networkidle")
            await asyncio.sleep(random.uniform(2, 4))
            
            # Click "Invite" button (may vary based on Facebook UI)
            # This is a simplified implementation - actual selectors may need adjustment
            try:
                # Look for invite button
                invite_button = await self.page.wait_for_selector(
                    'div[aria-label*="Invite"], a[aria-label*="Invite"]',
                    timeout=5000
                )
                await invite_button.click()
                await asyncio.sleep(random.uniform(1, 2))
            except Exception as e:
                logger.warning(f"Could not find invite button: {e}")
                # Try alternative: post comment with invitation
                return await self._post_invitation_comment(user_id, group_id, message)
            
            # Search for user
            search_input = await self.page.wait_for_selector(
                'input[placeholder*="Search"], input[type="text"]',
                timeout=5000
            )
            
            # Type user ID or find in suggestions
            await self._human_like_typing(search_input, user_id)
            await asyncio.sleep(random.uniform(2, 3))
            
            # Select user from results
            user_result = await self.page.wait_for_selector(
                f'div[data-id="{user_id}"], li[data-id="{user_id}"]',
                timeout=5000
            )
            await user_result.click()
            await asyncio.sleep(random.uniform(1, 2))
            
            # Add optional message
            if message:
                try:
                    message_input = await self.page.wait_for_selector(
                        'textarea, input[placeholder*="message"]',
                        timeout=3000
                    )
                    await self._human_like_typing(message_input, message)
                    await asyncio.sleep(random.uniform(1, 2))
                except Exception:
                    logger.warning("Could not add personal message to invitation")
            
            # Send invitation
            send_button = await self.page.wait_for_selector(
                'button[type="submit"], div[aria-label*="Send"]',
                timeout=5000
            )
            await send_button.click()
            await asyncio.sleep(random.uniform(2, 3))
            
            logger.info(f"✓ Successfully invited user {user_id} to group {group_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to invite user {user_id} to group {group_id}: {e}")
            return False
    
    async def _post_invitation_comment(
        self, 
        user_id: str, 
        group_id: str, 
        message: Optional[str] = None
    ) -> bool:
        """
        Alternative method: Post a comment tagging the user with group link.
        
        Args:
            user_id: Facebook user ID
            group_id: Facebook group ID
            message: Optional message template
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Posting invitation comment for user {user_id}")
            
            # This would require finding the user's post and commenting
            # For now, this is a placeholder
            # In practice, you'd navigate to the post and comment with @mention
            
            logger.warning("Comment-based invitation not fully implemented")
            return False
            
        except Exception as e:
            logger.error(f"Failed to post invitation comment: {e}")
            return False
    
    async def _human_like_typing(self, element, text: str) -> None:
        """
        Type text in a human-like manner with random delays.
        
        Args:
            element: Page element to type into
            text: Text to type
        """
        for char in text:
            await element.type(char, delay=random.randint(50, 150))
            
            # Occasional longer pause (simulating thinking)
            if random.random() < 0.1:
                await asyncio.sleep(random.uniform(0.3, 0.8))
