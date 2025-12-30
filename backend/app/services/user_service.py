"""
User Service - Manages user creation and retrieval
"""
from typing import Optional, Dict
from app.utils.database import db_connection
from app.utils.logger import logger
import uuid


class UserService:
    """Service for managing users in the database"""
    
    @staticmethod
    def get_or_create_user(
        user_identifier: str,
        privy_user_id: Optional[str] = None,
        email: Optional[str] = None,
        wallet_address: Optional[str] = None,
        session_id: Optional[str] = None,
        auth_method: str = "wallet"
    ) -> Optional[Dict]:
        """
        Get or create a user in the database.
        
        Args:
            user_identifier: Unique identifier (Privy ID, wallet address, or session ID)
            privy_user_id: Privy user ID if available
            email: Email address if available (from Privy email login)
            wallet_address: Wallet address if available
            session_id: Session ID if available
            auth_method: Authentication method ('privy', 'wallet', 'session')
        
        Returns:
            User dict with 'id' (UUID) and other fields, or None if error
        """
        if not db_connection.pool:
            logger.error("Database connection not available")
            return None
        
        try:
            # First, try to find existing user by Privy ID if provided (highest priority)
            if privy_user_id:
                existing_privy_user = db_connection.execute_query(
                    "SELECT id, user_identifier, privy_user_id, email, wallet_address, session_id, auth_method FROM users WHERE privy_user_id = %s",
                    (privy_user_id,),
                    fetch_one=True
                )
                if existing_privy_user:
                    # User exists with this Privy ID, update and return
                    updates = ["last_active = NOW()", "updated_at = NOW()"]
                    update_params = []  # ✅ Start EMPTY
                    
                    # Update email if provided and not set
                    if email and not existing_privy_user.get('email'):
                        updates.append("email = %s")
                        update_params.append(email.lower())
                    
                    # Update wallet address if provided and not set
                    if wallet_address and wallet_address != "0x0000000000000000000000000000000000000000000000000000000000000000":
                        if not existing_privy_user.get('wallet_address') or existing_privy_user.get('wallet_address') == "0x0000000000000000000000000000000000000000000000000000000000000000":
                            updates.append("wallet_address = %s")
                            update_params.append(wallet_address.lower())
                    
                    if len(update_params) > 0:  # Only if we have fields to update
                        update_params.append(str(existing_privy_user['id']))  # ✅ ID LAST
                        update_query = f"UPDATE users SET {', '.join(updates)} WHERE id = %s::uuid"
                        db_connection.execute_query(update_query, tuple(update_params), fetch_all=False)
                        logger.info(f"Updated user {existing_privy_user['id']} with new data")
                    logger.info(f"Found existing user by Privy ID: {existing_privy_user['id']}")
                    return existing_privy_user
            
            # Second, try to find existing user by email if provided
            if email:
                existing_email_user = db_connection.execute_query(
                    "SELECT id, user_identifier, privy_user_id, email, wallet_address, session_id, auth_method FROM users WHERE email = %s",
                    (email.lower(),),
                    fetch_one=True
                )
                if existing_email_user:
                    # User exists with this email, update other fields
                    updates = ["last_active = NOW()", "updated_at = NOW()"]
                    update_params = []
                    
                    # Update privy_user_id if provided and not set
                    if privy_user_id and not existing_email_user.get('privy_user_id'):
                        updates.append("privy_user_id = %s")
                        update_params.append(privy_user_id)
                    
                    # Update wallet address if provided and not set
                    if wallet_address and wallet_address != "0x0000000000000000000000000000000000000000000000000000000000000000":
                        if not existing_email_user.get('wallet_address') or existing_email_user.get('wallet_address') == "0x0000000000000000000000000000000000000000000000000000000000000000":
                            updates.append("wallet_address = %s")
                            update_params.append(wallet_address.lower())
                    
                    if len(update_params) > 0:
                        update_params.append(str(existing_email_user['id']))
                        update_query = f"UPDATE users SET {', '.join(updates)} WHERE id = %s::uuid"
                        db_connection.execute_query(update_query, tuple(update_params), fetch_all=False)
                    logger.info(f"Found existing user by email: {existing_email_user['id']}")
                    return existing_email_user
            
            # Third, try to find existing user by wallet address if provided
            if wallet_address and wallet_address != "0x0000000000000000000000000000000000000000000000000000000000000000":
                existing_wallet_user = db_connection.execute_query(
                    "SELECT id, user_identifier, privy_user_id, email, wallet_address, session_id, auth_method FROM users WHERE wallet_address = %s",
                    (wallet_address.lower(),),
                    fetch_one=True
                )
                if existing_wallet_user:
                    # User exists with this wallet, update other fields
                    updates = ["last_active = NOW()", "updated_at = NOW()"]
                    update_params = []
                    
                    # Update privy_user_id if provided and not set
                    if privy_user_id and not existing_wallet_user.get('privy_user_id'):
                        updates.append("privy_user_id = %s")
                        update_params.append(privy_user_id)
                    
                    # Update email if provided and not set
                    if email and not existing_wallet_user.get('email'):
                        updates.append("email = %s")
                        update_params.append(email.lower())
                    
                    if len(update_params) > 0:
                        update_params.append(str(existing_wallet_user['id']))
                        update_query = f"UPDATE users SET {', '.join(updates)} WHERE id = %s::uuid"
                        db_connection.execute_query(update_query, tuple(update_params), fetch_all=False)
                    logger.info(f"Found existing user by wallet: {existing_wallet_user['id']}")
                    return existing_wallet_user
            
            # Then, try to find existing user by identifier
            find_query = """
                SELECT id, user_identifier, privy_user_id, email, wallet_address, session_id, auth_method
                FROM users
                WHERE user_identifier = %s
            """
            existing_user = db_connection.execute_query(
                find_query,
                (user_identifier,),
                fetch_one=True
            )
            
            if existing_user:
                # Update last_active timestamp and wallet address if provided
                updates = ["last_active = NOW()", "updated_at = NOW()"]
                update_params = []  # ✅ Start EMPTY
                
                # If wallet address is provided and user doesn't have one, update it
                # Also update if current wallet_address is null or empty
                if wallet_address and wallet_address != "0x0000000000000000000000000000000000000000000000000000000000000000":
                    current_wallet = existing_user.get('wallet_address')
                    # Update if wallet_address is None, empty string, or the zero address
                    if not current_wallet or current_wallet == "0x0000000000000000000000000000000000000000000000000000000000000000" or current_wallet.strip() == "":
                        updates.append("wallet_address = %s")
                        update_params.append(wallet_address.lower())
                        logger.info(f"Updating wallet address for user {existing_user['id']}: {wallet_address}")
                    elif current_wallet.lower() != wallet_address.lower():
                        # Wallet address changed - update it
                        updates.append("wallet_address = %s")
                        update_params.append(wallet_address.lower())
                        logger.info(f"Updating wallet address for user {existing_user['id']}: {current_wallet} -> {wallet_address}")
                
                # If privy_user_id is provided and user doesn't have one, update it
                if privy_user_id and not existing_user.get('privy_user_id'):
                    updates.append("privy_user_id = %s")
                    update_params.append(privy_user_id)
                    logger.info(f"Updating privy_user_id for user {existing_user['id']}: {privy_user_id}")
                
                # If email is provided and user doesn't have one, update it
                if email and not existing_user.get('email'):
                    updates.append("email = %s")
                    update_params.append(email.lower())
                    logger.info(f"Updating email for user {existing_user['id']}: {email}")
                
                # Only execute UPDATE if we have parameters (more than just timestamp updates)
                if len(update_params) > 0:
                    update_params.append(str(existing_user['id']))  # ✅ ID LAST
                    update_query = f"""
                        UPDATE users
                        SET {", ".join(updates)}
                        WHERE id = %s::uuid
                    """
                    db_connection.execute_query(update_query, tuple(update_params), fetch_all=False)
                
                # Fetch updated user
                updated_user = db_connection.execute_query(
                    find_query,
                    (user_identifier,),
                    fetch_one=True
                )
                logger.debug(f"Found existing user: {existing_user['id']}")
                return updated_user or existing_user
            
            # User doesn't exist, create new one
            user_id = uuid.uuid4()
            # Convert UUID to string for psycopg2 compatibility
            user_id_str = str(user_id)
            create_query = """
                INSERT INTO users (
                    id, user_identifier, privy_user_id, email, wallet_address, session_id, auth_method
                )
                VALUES (%s::uuid, %s, %s, %s, %s, %s, %s)
                RETURNING id, user_identifier, privy_user_id, email, wallet_address, session_id, auth_method, created_at
            """
            
            new_user = db_connection.execute_query(
                create_query,
                (user_id_str, user_identifier, privy_user_id, email.lower() if email else None, wallet_address, session_id, auth_method),
                fetch_one=True
            )
            
            if new_user:
                logger.info(f"Created new user: {new_user['id']} (identifier: {user_identifier}, method: {auth_method})")
                return new_user
            else:
                logger.error(f"Failed to create user with identifier: {user_identifier}")
                return None
                
        except Exception as e:
            logger.error(f"Error in get_or_create_user: {e}", exc_info=True)
            return None
    
    @staticmethod
    def get_user_by_id(user_id: str) -> Optional[Dict]:
        """
        Get user by UUID.
        
        Args:
            user_id: User UUID
        
        Returns:
            User dict or None
        """
        if not db_connection.pool:
            return None
        
        try:
            query = """
                SELECT id, user_identifier, privy_user_id, wallet_address, session_id, auth_method, created_at
                FROM users
                WHERE id = %s
            """
            return db_connection.execute_query(query, (user_id,), fetch_one=True)
        except Exception as e:
            logger.error(f"Error getting user by ID: {e}", exc_info=True)
            return None
    
    @staticmethod
    def get_user_by_wallet_address(wallet_address: str) -> Optional[Dict]:
        """
        Get user by wallet address.
        
        Args:
            wallet_address: Wallet address
        
        Returns:
            User dict or None
        """
        if not db_connection.pool:
            return None
        
        try:
            query = """
                SELECT id, user_identifier, privy_user_id, wallet_address, session_id, auth_method, created_at
                FROM users
                WHERE wallet_address = %s
            """
            return db_connection.execute_query(query, (wallet_address.lower(),), fetch_one=True)
        except Exception as e:
            logger.error(f"Error getting user by wallet address: {e}", exc_info=True)
            return None


# Create singleton instance
user_service = UserService()

