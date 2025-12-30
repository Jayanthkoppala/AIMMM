"""
Privy Service - User authentication and verification
"""
from typing import Optional, Dict
import httpx
import time
from app.config import settings
from app.utils.logger import logger


class PrivyService:
    """Service for Privy authentication verification"""
    
    def __init__(self):
        self.app_id = settings.PRIVY_APP_ID
        self.app_secret = settings.PRIVY_APP_SECRET
        self.base_url = "https://auth.privy.io"
        # Cache for verified tokens: {token: (user_data, timestamp)}
        self._token_cache: Dict[str, tuple[Dict, float]] = {}
        self._cache_ttl = 30  # Cache for 30 seconds
    
    async def verify_access_token(self, access_token: str) -> Optional[Dict]:
        """
        Verify Privy access token and get user info.
        Uses caching to avoid rate limiting on rapid requests.
        
        Args:
            access_token: Privy access token from frontend
        
        Returns:
            User info dict if valid, None otherwise
        """
        if not self.app_id or not self.app_secret:
            logger.warning("Privy credentials not configured")
            return None
        
        # Check cache first
        current_time = time.time()
        if access_token in self._token_cache:
            user_data, cached_time = self._token_cache[access_token]
            if current_time - cached_time < self._cache_ttl:
                logger.debug(f"Using cached Privy verification for token (cached {current_time - cached_time:.1f}s ago)")
                return user_data
            else:
                # Cache expired, remove it
                del self._token_cache[access_token]
        
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
                    response_data = response.json()
                    
                    # Privy returns user data nested in 'user' key
                    # Response format: { "user": { "id": "...", ... }, "identity_token": "..." }
                    user_data = response_data.get('user', response_data)  # Fallback to response_data if no 'user' key
                    
                    user_id = user_data.get('id', 'unknown')
                    logger.info(f"Privy user verified: {user_id}")
                    
                    if user_id == 'unknown':
                        logger.warning(f"Privy returned response but no user ID. Response keys: {list(response_data.keys())}")
                        logger.warning(f"User data keys: {list(user_data.keys())}")
                        logger.debug(f"Full Privy response: {response_data}")
                    
                    # Cache the result
                    self._token_cache[access_token] = (user_data, current_time)
                    
                    # Clean up old cache entries (keep only last 100)
                    if len(self._token_cache) > 100:
                        # Remove oldest entries
                        sorted_cache = sorted(self._token_cache.items(), key=lambda x: x[1][1])
                        for old_token, _ in sorted_cache[:-100]:
                            del self._token_cache[old_token]
                    
                    return user_data  # Return the user data, not the full response
                elif response.status_code == 429:
                    # Rate limited - try to use cached result if available
                    logger.warning(f"Privy rate limited (429). Checking cache...")
                    # If we have any cached entry for this token (even expired), try to use it
                    if access_token in self._token_cache:
                        user_data, _ = self._token_cache[access_token]
                        logger.info(f"Using expired cache entry due to rate limit")
                        return user_data
                    logger.warning(f"Privy token verification rate limited: 429")
                    return None
                else:
                    logger.warning(f"Privy token verification failed: {response.status_code}")
                    logger.debug(f"Response body: {response.text}")
                    return None
                    
        except httpx.RequestError as e:
            logger.error(f"Error verifying Privy access token: {e}", exc_info=True)
            # Try to use cached result on network errors
            if access_token in self._token_cache:
                user_data, _ = self._token_cache[access_token]
                logger.info(f"Using cached result due to network error")
                return user_data
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



