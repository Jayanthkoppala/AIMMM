"""
Privy Service - User authentication and verification
"""
from typing import Optional, Dict
import httpx
from app.config import settings
from app.utils.logger import logger


class PrivyService:
    """Service for Privy authentication verification"""
    
    def __init__(self):
        self.app_id = settings.PRIVY_APP_ID
        self.app_secret = settings.PRIVY_APP_SECRET
        self.base_url = "https://auth.privy.io"
    
    async def verify_access_token(self, access_token: str) -> Optional[Dict]:
        """
        Verify Privy access token and get user info.
        
        Args:
            access_token: Privy access token from frontend
        
        Returns:
            User info dict if valid, None otherwise
        """
        if not self.app_id or not self.app_secret:
            logger.warning("Privy credentials not configured")
            return None
        
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "privy-app-id": self.app_id
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/users/me",
                    headers=headers
                )
                
                if response.status_code == 200:
                    user_data = response.json()
                    logger.info(f"Privy user verified: {user_data.get('id', 'unknown')}")
                    return user_data
                else:
                    logger.warning(f"Privy token verification failed: {response.status_code}")
                    return None
                    
        except httpx.RequestError as e:
            logger.error(f"Error verifying Privy access token: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Unexpected error verifying Privy token: {e}", exc_info=True)
            return None
    
    async def get_user_by_id(self, privy_user_id: str) -> Optional[Dict]:
        """
        Get Privy user details by ID (server-to-server).
        
        Args:
            privy_user_id: Privy user ID
        
        Returns:
            User info dict if found, None otherwise
        """
        if not self.app_id or not self.app_secret:
            logger.warning("Privy credentials not configured")
            return None
        
        try:
            headers = {
                "Authorization": f"Bearer {self.app_secret}",
                "privy-app-id": self.app_id
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/users/{privy_user_id}",
                    headers=headers
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(f"Failed to get Privy user {privy_user_id}: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting Privy user by ID: {e}", exc_info=True)
            return None


# Create singleton instance
privy_service = PrivyService()

