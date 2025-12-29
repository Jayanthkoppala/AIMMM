"""
Autonomous Wallet Service - Server-managed Aptos wallets for autonomous trading
"""
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from app.config import settings
from app.utils.logger import logger
from app.utils.database import db_connection
import httpx
import json


class AutonomousWalletService:
    """Manages server-side Aptos wallets for autonomous trading"""
    
    def __init__(self):
        # Get encryption key from settings
        encryption_key = settings.AUTONOMOUS_WALLET_ENCRYPTION_KEY
        if not encryption_key:
            logger.warning("AUTONOMOUS_WALLET_ENCRYPTION_KEY not set - wallet encryption disabled")
            self.cipher = None
        else:
            try:
                # Fernet requires base64-encoded 32-byte key
                key_bytes = encryption_key.encode() if isinstance(encryption_key, str) else encryption_key
                self.cipher = Fernet(key_bytes)
            except Exception as e:
                logger.error(f"Failed to initialize encryption cipher: {e}")
                self.cipher = None
    
    def _encrypt_private_key(self, private_key: str) -> str:
        """Encrypt private key for secure storage"""
        if not self.cipher:
            logger.warning("Encryption not available - storing private key in plain text (NOT RECOMMENDED)")
            return private_key
        return self.cipher.encrypt(private_key.encode()).decode()
    
    def _decrypt_private_key(self, encrypted_key: str) -> str:
        """Decrypt private key from storage"""
        if not self.cipher:
            # Assume plain text if encryption not available
            return encrypted_key
        try:
            return self.cipher.decrypt(encrypted_key.encode()).decode()
        except Exception as e:
            logger.error(f"Failed to decrypt private key: {e}")
            raise
    
    async def create_wallet_for_user(self, privy_user_id: str) -> Dict:
        """
        Create new Aptos wallet for autonomous trading.
        
        Note: This generates a new Aptos account. In production, you would:
        1. Generate account using Aptos SDK
        2. Encrypt private key
        3. Store in database
        
        For now, we'll use a simplified approach with Movement RPC.
        """
        if not db_connection.pool:
            logger.error("Database connection not available")
            return {"address": None, "created": False}
        
        try:
            # Generate a new account using Movement RPC
            # In a full implementation, you'd use: from aptos_sdk.account import Account
            # account = Account.generate()
            # For now, we'll create a placeholder that will be properly implemented
            # when Aptos SDK is available
            
            # Placeholder: Generate wallet address (this should use Aptos SDK)
            import secrets
            import hashlib
            
            # Generate a random private key (32 bytes)
            private_key_bytes = secrets.token_bytes(32)
            private_key_hex = private_key_bytes.hex()
            
            # For Movement/Aptos, we need to derive the address from the public key
            # This is a simplified version - in production use Aptos SDK
            # For now, we'll create a deterministic address from the private key
            address_hash = hashlib.sha256(private_key_bytes).hexdigest()[:64]
            wallet_address = f"0x{address_hash}"
            
            # Encrypt private key
            encrypted_key = self._encrypt_private_key(private_key_hex)
            
            # Store in database
            query = """
                INSERT INTO autonomous_wallets 
                (privy_user_id, wallet_address, encrypted_private_key)
                VALUES (%s, %s, %s)
                ON CONFLICT (privy_user_id) 
                DO UPDATE SET 
                    wallet_address = EXCLUDED.wallet_address,
                    encrypted_private_key = EXCLUDED.encrypted_private_key,
                    updated_at = NOW()
                RETURNING wallet_address
            """
            
            result = db_connection.execute_query(
                query, 
                (privy_user_id, wallet_address, encrypted_key),
                fetch_one=True
            )
            
            if result:
                logger.info(f"Created autonomous wallet for Privy user {privy_user_id}: {wallet_address}")
                return {
                    "address": result.get("wallet_address"),
                    "created": True
                }
            else:
                logger.error("Failed to create wallet in database")
                return {"address": None, "created": False}
                
        except Exception as e:
            logger.error(f"Error creating wallet for user: {e}", exc_info=True)
            return {"address": None, "created": False}
    
    async def get_wallet(self, privy_user_id: str) -> Optional[Dict]:
        """
        Get wallet info for a Privy user.
        
        Returns:
            Dict with wallet_address and private_key (decrypted), or None
        """
        if not db_connection.pool:
            return None
        
        try:
            query = """
                SELECT wallet_address, encrypted_private_key
                FROM autonomous_wallets
                WHERE privy_user_id = %s
            """
            
            result = db_connection.execute_query(query, (privy_user_id,), fetch_one=True)
            
            if not result:
                return None
            
            # Decrypt private key
            try:
                private_key_hex = self._decrypt_private_key(result['encrypted_private_key'])
            except Exception as e:
                logger.error(f"Failed to decrypt private key for user {privy_user_id}: {e}")
                return None
            
            return {
                "wallet_address": result['wallet_address'],
                "private_key": private_key_hex
            }
            
        except Exception as e:
            logger.error(f"Error getting wallet for user {privy_user_id}: {e}", exc_info=True)
            return None
    
    async def sign_and_submit_transaction(
        self,
        privy_user_id: str,
        transaction_payload: Dict[str, Any]
    ) -> Optional[str]:
        """
        Sign and submit transaction using autonomous wallet.
        
        This method:
        1. Gets the wallet for the user
        2. Gets a quote from Mosaic
        3. Signs the transaction using the private key
        4. Submits to Movement network
        5. Returns transaction hash
        
        Args:
            privy_user_id: Privy user ID
            transaction_payload: Transaction details (token_a, token_b, direction, amount_in, min_amount_out)
        
        Returns:
            Transaction hash if successful, None otherwise
        """
        wallet_info = await self.get_wallet(privy_user_id)
        
        if not wallet_info:
            logger.error(f"No autonomous wallet found for user {privy_user_id}")
            return None
        
        wallet_address = wallet_info['wallet_address']
        private_key = wallet_info['private_key']
        
        try:
            # Get quote from Mosaic
            from app.services import mosaic
            
            direction = transaction_payload.get('direction', 'X_TO_Y')
            token_a = transaction_payload.get('token_a')
            token_b = transaction_payload.get('token_b')
            amount_in = transaction_payload.get('amount_in')
            min_amount_out = transaction_payload.get('min_amount_out', 0)
            
            if direction == "X_TO_Y":
                src_asset = token_a
                dst_asset = token_b
            else:
                src_asset = token_b
                dst_asset = token_a
            
            # Get quote
            quote_data = await mosaic.get_quote(
                src_asset=src_asset,
                dst_asset=dst_asset,
                amount=str(amount_in),
                sender=wallet_address,
                slippage=100,
                receiver=wallet_address
            )
            
            if not quote_data:
                logger.error("Failed to get quote from Mosaic")
                return None
            
            # Get transaction data from quote
            tx_data = quote_data.get("tx")
            if not tx_data:
                logger.error("Quote data missing transaction information")
                return None
            
            # Sign and submit transaction
            # Note: This is a placeholder - actual implementation requires Aptos SDK
            # For now, we'll use Movement RPC to submit the transaction
            # In production, you would:
            # 1. Build transaction using Aptos SDK
            # 2. Sign with private key
            # 3. Submit to network
            
            # Placeholder implementation using Movement RPC
            movement_rpc = settings.MOVEMENT_RPC
            
            # Submit transaction (this is simplified - actual implementation needs proper signing)
            async with httpx.AsyncClient(timeout=30.0) as client:
                # In production, properly sign the transaction first
                # For now, this is a placeholder
                logger.warning(
                    "Transaction signing not fully implemented. "
                    "Requires Aptos SDK for proper transaction signing."
                )
                
                # Return None for now - this needs proper Aptos SDK integration
                return None
                
        except Exception as e:
            logger.error(f"Error signing and submitting transaction: {e}", exc_info=True)
            return None
    
    async def get_wallet_balance(self, privy_user_id: str, token_address: Optional[str] = None) -> float:
        """
        Get wallet balance for a Privy user.
        
        Args:
            privy_user_id: Privy user ID
            token_address: Optional token address (default: native token)
        
        Returns:
            Balance in USD
        """
        wallet_info = await self.get_wallet(privy_user_id)
        if not wallet_info:
            return 0.0
        
        wallet_address = wallet_info['wallet_address']
        
        # Use existing wallet service to get balance
        from app.services.wallet import get_wallet_balance_usd
        return await get_wallet_balance_usd(wallet_address, token_address)
    
    async def set_autonomous_enabled(self, privy_user_id: str, enabled: bool) -> bool:
        """Enable or disable autonomous trading for a user"""
        if not db_connection.pool:
            return False
        
        try:
            query = """
                UPDATE autonomous_wallets
                SET autonomous_enabled = %s, updated_at = NOW()
                WHERE privy_user_id = %s
                RETURNING id
            """
            
            result = db_connection.execute_query(
                query,
                (enabled, privy_user_id),
                fetch_one=True
            )
            
            return result is not None
            
        except Exception as e:
            logger.error(f"Error setting autonomous enabled: {e}", exc_info=True)
            return False
    
    async def get_autonomous_status(self, privy_user_id: str) -> Optional[Dict]:
        """Get autonomous trading status for a user"""
        if not db_connection.pool:
            return None
        
        try:
            query = """
                SELECT 
                    wallet_address,
                    autonomous_enabled,
                    risk_per_trade,
                    max_position_size
                FROM autonomous_wallets
                WHERE privy_user_id = %s
            """
            
            result = db_connection.execute_query(query, (privy_user_id,), fetch_one=True)
            return result
            
        except Exception as e:
            logger.error(f"Error getting autonomous status: {e}", exc_info=True)
            return None


# Create singleton instance
autonomous_wallet_service = AutonomousWalletService()

