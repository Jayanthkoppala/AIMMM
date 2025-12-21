from supabase import create_client, Client
from typing import Optional, Dict, List
from app.config import settings
from datetime import datetime
from app.utils.logger import logger


class SupabaseService:
    def __init__(self):
        self.client: Optional[Client] = None
        # Only create client if both URL and KEY are provided and not empty
        supabase_url = getattr(settings, 'SUPABASE_URL', '') or ''
        supabase_key = getattr(settings, 'SUPABASE_KEY', '') or ''
        
        # Check if credentials are provided (not empty after stripping)
        url_provided = bool(supabase_url and supabase_url.strip())
        key_provided = bool(supabase_key and supabase_key.strip())
        
        if url_provided and key_provided:
            try:
                self.client = create_client(supabase_url.strip(), supabase_key.strip())
                logger.info("Supabase client initialized successfully")
            except Exception as e:
                # Only warn if credentials were provided but invalid
                logger.warning(f"Supabase client initialization failed (credentials may be invalid): {e}")
                logger.info("Using direct PostgreSQL connection instead")
                self.client = None
        else:
            # Credentials not provided - this is fine, we use direct PostgreSQL
            logger.debug("Supabase client not configured (using direct PostgreSQL connection)")
            self.client = None
    
    async def get_or_create_user(self, wallet_address: str, privy_user_id: Optional[str] = None) -> Optional[Dict]:
        """Get or create user by wallet address"""
        if not self.client:
            return None
        
        try:
            # Check if user exists
            result = self.client.table("users").select("*").eq("wallet_address", wallet_address).execute()
            
            if result.data:
                return result.data[0]
            
            # Create new user
            new_user = {
                "wallet_address": wallet_address,
                "privy_user_id": privy_user_id,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            result = self.client.table("users").insert(new_user).execute()
            return result.data[0] if result.data else None
            
        except Exception as e:
            logger.error(f"Error getting/creating user: {e}", exc_info=True)
            return None
    
    async def create_agent_execution(
        self,
        user_id: str,
        mode: str,
        token_a_address: str,
        token_b_address: str,
        switchboard_feed_id: Optional[str],
        oracle_price_a: float,
        oracle_price_b: float,
        llm_action: str,
        llm_confidence: float,
        executed: bool,
        tx_hash: Optional[str],
        execution_cost: float
    ) -> Optional[Dict]:
        """Create agent execution record"""
        if not self.client:
            return None
        
        try:
            execution = {
                "user_id": user_id,
                "mode": mode,
                "token_a_address": token_a_address,
                "token_b_address": token_b_address,
                "switchboard_feed_id": switchboard_feed_id,
                "oracle_price_a": oracle_price_a,
                "oracle_price_b": oracle_price_b,
                "llm_action": llm_action,
                "llm_confidence": llm_confidence,
                "executed": executed,
                "tx_hash": tx_hash,
                "execution_cost": execution_cost,
                "created_at": datetime.utcnow().isoformat()
            }
            
            result = self.client.table("agent_executions").insert(execution).execute()
            return result.data[0] if result.data else None
            
        except Exception as e:
            logger.error(f"Error creating agent execution: {e}", exc_info=True)
            return None
    
    async def get_user_executions(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict]:
        """Get agent executions for a user"""
        if not self.client:
            return []
        
        try:
            result = self.client.table("agent_executions")\
                .select("*")\
                .eq("user_id", user_id)\
                .order("created_at", desc=True)\
                .limit(limit)\
                .offset(offset)\
                .execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Error getting user executions: {e}", exc_info=True)
            return []
    
    async def create_payment_record(
        self,
        agent_execution_id: str,
        invoice_id: str,
        amount: float,
        tx_hash: str,
        status: str = "pending"
    ) -> Optional[Dict]:
        """Create payment record"""
        if not self.client:
            return None
        
        try:
            payment = {
                "agent_execution_id": agent_execution_id,
                "invoice_id": invoice_id,
                "amount": amount,
                "tx_hash": tx_hash,
                "status": status,
                "created_at": datetime.utcnow().isoformat()
            }
            
            result = self.client.table("payments").insert(payment).execute()
            return result.data[0] if result.data else None
            
        except Exception as e:
            logger.error(f"Error creating payment record: {e}", exc_info=True)
            return None


supabase_service = SupabaseService()

