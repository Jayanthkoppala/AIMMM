"""
Strategy Management API Router
Endpoints for CRUD operations, execution, and scheduling of trading strategies
"""
from fastapi import APIRouter, HTTPException, Header, Query
from typing import Optional, List
import json
from app.utils.database import db_connection
from app.utils.logger import logger
from app.config import settings
from app.services import privy_service
from app.services.user_service import user_service
from app.services.strategy_executor import strategy_executor
from app.services.strategy_scheduler import strategy_scheduler
from app.services.paper_trading_dex import paper_trading_dex
from app.models.strategy import (
    CreateStrategyRequest,
    UpdateStrategyRequest,
    StrategyResponse,
    ExecuteStrategyRequest,
    ActivateStrategyRequest,
    ExecutionResponse,
    TradingState,
    ExecutionResult,
    ParseNaturalLanguageRequest
)


router = APIRouter(prefix="/strategies", tags=["strategies"])


async def get_authenticated_user(
    authorization: Optional[str] = Header(None),
    wallet_address_header: Optional[str] = Header(None, alias="X-Wallet-Address")
) -> tuple[str, str]:
    """
    Verify Privy access token or wallet/session and return user UUID and wallet_address.
    Creates or retrieves user from users table.
    Raises HTTPException if authentication fails.
    
    Returns:
        tuple: (user_id as UUID string, wallet_address)
    """
    user_identifier = None
    privy_user_id = None
    email = None
    wallet_address = None
    session_id = None
    auth_method = "session"
    privy_user = None
    
    # Try Privy authentication first if token is provided
    if authorization and authorization.startswith("Bearer "):
        access_token = authorization.replace("Bearer ", "")
        
        # Try to verify with Privy
        privy_user = await privy_service.privy_service.verify_access_token(access_token)
        
        if privy_user:
            privy_user_id = privy_user.get('id')
            
            # Extract wallet address from linked_accounts if available
            wallet_address = None
            linked_accounts = privy_user.get('linked_accounts', [])
            for account in linked_accounts:
                if account.get('type') == 'wallet':
                    wallet_address = account.get('address')
                    break
            
            # Fallback to direct wallet field
            if not wallet_address and privy_user.get('wallet'):
                wallet_address = privy_user.get('wallet', {}).get('address', '')
            
            # Extract email from Privy user data
            # Privy returns email in linked_accounts
            email = None
            for account in linked_accounts:
                if account.get('type') == 'email':
                    email = account.get('address')
                    break
            
            # Fallback: check other possible locations
            if not email:
                if privy_user.get('email'):
                    email_obj = privy_user.get('email')
                    email = email_obj.get('address') if isinstance(email_obj, dict) else email_obj
                elif privy_user.get('google', {}).get('email'):
                    email = privy_user.get('google', {}).get('email')
                elif privy_user.get('apple', {}).get('email'):
                    email = privy_user.get('apple', {}).get('email')
            
            # Only use Privy if we got a valid user ID
            if privy_user_id:
                user_identifier = privy_user_id
                auth_method = "privy"
                logger.info(f"Privy authentication successful: {privy_user_id} (email: {email or 'none'}, wallet: {wallet_address or 'none'})")
                logger.debug(f"Privy user data keys: {list(privy_user.keys())}")
            else:
                logger.warning("Privy returned user but no user ID, falling back to wallet/session")
        else:
            logger.warning("Privy authentication failed, falling back to wallet/session")
    
    # Fallback: Use wallet address or session ID when Privy is not configured or failed
    if not user_identifier:
        # Always try to get wallet address or session ID from header first (works even if Privy is configured)
        if wallet_address_header:
            identifier = wallet_address_header.strip()
            # Check if it's a session ID (starts with "session-") or a wallet address
            if identifier.startswith("session-"):
                # It's a session ID from frontend
                session_id = identifier
                user_identifier = session_id
                wallet_address = None  # Will be updated when wallet connects
                auth_method = "session"
                logger.info(f"Using session-based authentication: {session_id}")
                # Try to find existing user by session, and update wallet if provided later
            else:
                # It's a wallet address - prioritize wallet over session
                wallet_address = identifier.lower()
                # First try to find user by wallet address
                existing_wallet_user = user_service.get_user_by_wallet_address(wallet_address)
                if existing_wallet_user:
                    # User exists with this wallet, use their identifier
                    user_identifier = existing_wallet_user['user_identifier']
                    logger.info(f"Found existing user by wallet: {existing_wallet_user['id']}")
                else:
                    # New wallet, create identifier
                    user_identifier = f"wallet-{wallet_address}"
                auth_method = "wallet"
                logger.info(f"Using wallet-based authentication: {wallet_address}")
        elif not settings.PRIVY_APP_ID or not settings.PRIVY_APP_SECRET:
            # No identifier provided and Privy not configured - use a session-based fallback for development
            logger.warning("Privy not configured and no wallet address/session ID provided - using session fallback")
            session_id = "session-fallback"
            user_identifier = session_id
            wallet_address = "0x0000000000000000000000000000000000000000000000000000000000000000"
            auth_method = "session"
        else:
            # Privy is configured but authentication failed and no wallet/session provided
            if authorization and authorization.startswith("Bearer "):
                raise HTTPException(status_code=401, detail="Invalid access token. Please provide X-Wallet-Address header as fallback")
            else:
                raise HTTPException(status_code=401, detail="Authorization header or X-Wallet-Address required")
    
    # Ensure we have a user_identifier before trying to create user
    if not user_identifier:
        logger.error("No user identifier available for authentication")
        raise HTTPException(status_code=401, detail="Unable to identify user")
    
    # Get or create user in database
    user = user_service.get_or_create_user(
        user_identifier=user_identifier,
        privy_user_id=privy_user_id,
        email=email,
        wallet_address=wallet_address,
        session_id=session_id,
        auth_method=auth_method
    )
    
    if not user:
        logger.error(f"Failed to get or create user with identifier: {user_identifier}")
        raise HTTPException(status_code=500, detail="Failed to authenticate user")
    
    logger.info(f"Authenticated user: {user['id']} (identifier: {user_identifier}, method: {auth_method})")
    
    # Return UUID as string and wallet address
    return str(user['id']), wallet_address or ""


@router.post("")
async def create_strategy(
    request: CreateStrategyRequest,
    authorization: Optional[str] = Header(None),
    wallet_address_header: Optional[str] = Header(None, alias="X-Wallet-Address")
):
    """Create a new trading strategy"""
    user_id, wallet_address = await get_authenticated_user(authorization, wallet_address_header)
    
    logger.info(f"Creating strategy for user_id: {user_id}, name: {request.name}")
    
    try:
        # Convert strategy config to JSON
        config_json = json.dumps(request.strategy_config.dict())
        
        # pool_id is now a simple integer (or None)
        pool_id_value = request.pool_id
        
        query = """
            INSERT INTO user_strategies (
                user_id, wallet_address, name, description, visibility, pool_id, pool_address, execution_interval, strategy_config
            )
            VALUES (%s::uuid, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
            RETURNING id, created_at, updated_at
        """
        
        result = db_connection.execute_query(
            query,
            (user_id, wallet_address, request.name, request.description, request.visibility, 
             pool_id_value, request.pool_address or request.pool_id, request.execution_interval, config_json),
            fetch_one=True
        )
        
        if not result:
            raise HTTPException(status_code=500, detail="Failed to create strategy")
        
        # Initialize paper trading balances
        strategy_id = str(result.get('id'))
        initial_capital = request.strategy_config.paper_trading_config.initial_capital_usdc
        await paper_trading_dex.initialize_strategy_balances(strategy_id, initial_capital)
        
        return {
            "id": strategy_id,
            "user_id": user_id,
            "wallet_address": wallet_address,
            "name": request.name,
            "description": request.description,
            "visibility": request.visibility,
            "is_active": False,
            "pool_id": pool_id_value,
            "pool_address": request.pool_address or request.pool_id,
            "strategy_config": request.strategy_config.dict(),
            "created_at": result.get('created_at'),
            "updated_at": result.get('updated_at'),
            "last_execution": None,
            "execution_interval": request.execution_interval
        }
        
    except Exception as e:
        logger.error(f"Error creating strategy: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def get_strategies(
    authorization: Optional[str] = Header(None),
    wallet_address_header: Optional[str] = Header(None, alias="X-Wallet-Address"),
    visibility: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """List user's strategies"""
    user_id, _ = await get_authenticated_user(authorization, wallet_address_header)
    
    logger.info(f"Fetching strategies for user_id: {user_id}")
    
    try:
        # Build query with filters
        conditions = ["user_id = %s::uuid"]
        params = [user_id]
        
        if visibility:
            conditions.append("visibility = %s")
            params.append(visibility)
        
        if is_active is not None:
            conditions.append("is_active = %s")
            params.append(is_active)
        
        where_clause = " AND ".join(conditions)
        
        query = f"""
            SELECT *
            FROM user_strategies
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])
        
        results = db_connection.execute_query(query, tuple(params), fetch_all=True)
        
        logger.info(f"Found {len(results or [])} strategies for user_id: {user_id}")
        
        return {
            "strategies": results or [],
            "count": len(results or []),
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Error fetching strategies for user_id {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{strategy_id}")
async def get_strategy(
    strategy_id: str,
    authorization: Optional[str] = Header(None),
    wallet_address: Optional[str] = Header(None, alias="X-Wallet-Address")
):
    """Get a specific strategy"""
    user_id, _ = await get_authenticated_user(authorization, wallet_address)
    
    try:
        query = """
            SELECT *
            FROM user_strategies
            WHERE id = %s::uuid AND user_id = %s::uuid
        """
        
        result = db_connection.execute_query(query, (strategy_id, user_id), fetch_one=True)
        
        if not result:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching strategy: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{strategy_id}")
async def update_strategy(
    strategy_id: str,
    request: UpdateStrategyRequest,
    authorization: Optional[str] = Header(None),
    wallet_address: Optional[str] = Header(None, alias="X-Wallet-Address")
):
    """Update a strategy"""
    user_id, _ = await get_authenticated_user(authorization, wallet_address)
    
    try:
        # Build update query dynamically
        updates = []
        params = []
        
        if request.name is not None:
            updates.append("name = %s")
            params.append(request.name)
        
        if request.description is not None:
            updates.append("description = %s")
            params.append(request.description)
        
        if request.visibility is not None:
            updates.append("visibility = %s")
            params.append(request.visibility)
        
        if request.is_active is not None:
            updates.append("is_active = %s")
            params.append(request.is_active)
        
        if request.execution_interval is not None:
            updates.append("execution_interval = %s")
            params.append(request.execution_interval)
        
        if request.strategy_config is not None:
            updates.append("strategy_config = %s::jsonb")
            params.append(json.dumps(request.strategy_config.dict()))
        
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        updates.append("updated_at = NOW()")
        
        query = f"""
            UPDATE user_strategies
            SET {", ".join(updates)}
            WHERE id = %s::uuid AND user_id = %s::uuid
            RETURNING *
        """
        params.extend([strategy_id, user_id])
        
        result = db_connection.execute_query(query, tuple(params), fetch_one=True)
        
        if not result:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating strategy: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{strategy_id}")
async def delete_strategy(
    strategy_id: str,
    authorization: Optional[str] = Header(None),
    wallet_address: Optional[str] = Header(None, alias="X-Wallet-Address")
):
    """Delete a strategy"""
    user_id, _ = await get_authenticated_user(authorization, wallet_address)
    
    try:
        query = """
            DELETE FROM user_strategies
            WHERE id = %s::uuid AND user_id = %s::uuid
            RETURNING id
        """
        
        result = db_connection.execute_query(query, (strategy_id, user_id), fetch_one=True)
        
        if not result:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        return {"message": "Strategy deleted successfully", "id": str(result.get('id'))}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting strategy: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{strategy_id}/execute")
async def execute_strategy_endpoint(
    strategy_id: str,
    request: ExecuteStrategyRequest,
    authorization: Optional[str] = Header(None),
    wallet_address: Optional[str] = Header(None, alias="X-Wallet-Address")
):
    """Manually execute a strategy"""
    user_id, _ = await get_authenticated_user(authorization, wallet_address)
    
    try:
        result = await strategy_executor.execute_strategy(
            strategy_id=strategy_id,
            user_id=user_id,
            execution_mode=request.execution_mode
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error executing strategy: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{strategy_id}/trading-state")
async def get_trading_state(
    strategy_id: str,
    authorization: Optional[str] = Header(None),
    wallet_address: Optional[str] = Header(None, alias="X-Wallet-Address"),
    include_closed: bool = Query(False)
):
    """Get current trading state for a strategy"""
    user_id, _ = await get_authenticated_user(authorization, wallet_address)
    
    try:
        # Verify strategy ownership
        strategy_query = """
            SELECT id FROM user_strategies
            WHERE id = %s::uuid AND user_id = %s::uuid
        """
        strategy = db_connection.execute_query(strategy_query, (strategy_id, user_id), fetch_one=True)
        
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        # Get strategy config to get pool_address for price calculation
        strategy_config_query = """
            SELECT strategy_config, pool_address
            FROM user_strategies
            WHERE id = %s
        """
        strategy_info = db_connection.execute_query(
            strategy_config_query,
            (strategy_id,),
            fetch_one=True
        )
        
        pool_address = strategy_info.get('pool_address') if strategy_info else None
        
        # Get portfolio value (with current prices)
        portfolio = await paper_trading_dex.calculate_portfolio_value(
            strategy_id,
            pool_address=pool_address
        )
        
        # Get active positions count
        active_positions = await paper_trading_dex.get_active_positions_count(strategy_id)
        
        return {
            "strategy_id": strategy_id,
            "balances": portfolio['balances'],
            "total_portfolio_value": float(portfolio['total_value']),
            "initial_capital": float(portfolio['initial_capital']),
            "unrealized_pnl": float(portfolio['unrealized_pnl']),
            "realized_pnl": float(portfolio.get('realized_pnl', 0)),
            "total_pnl": float(portfolio.get('total_pnl', portfolio['unrealized_pnl'])),
            "unrealized_pnl_pct": portfolio['unrealized_pnl_pct'],
            "total_pnl_pct": portfolio.get('total_pnl_pct', portfolio['unrealized_pnl_pct']),
            "active_positions": active_positions
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting trading state: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{strategy_id}/executions")
async def get_executions(
    strategy_id: str,
    authorization: Optional[str] = Header(None),
    wallet_address: Optional[str] = Header(None, alias="X-Wallet-Address"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    include_market_data: bool = Query(False)
):
    """Get execution history for a strategy"""
    user_id, _ = await get_authenticated_user(authorization, wallet_address)
    
    try:
        # Verify strategy ownership
        strategy_query = """
            SELECT id FROM user_strategies
            WHERE id = %s::uuid AND user_id = %s::uuid
        """
        strategy = db_connection.execute_query(strategy_query, (strategy_id, user_id), fetch_one=True)
        
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        # Select fields based on include_market_data
        fields = """
            id, strategy_id, user_id, execution_timestamp,
            llm_model, decision, confidence, reasoning,
            execution_mode, duration_seconds, llm_cost,
            trade_executed, tx_hash, symbol, side,
            amount_in, amount_out, price
        """
        
        if include_market_data:
            fields += ", market_data"
        
        query = f"""
            SELECT {fields}
            FROM strategy_executions
            WHERE strategy_id = %s
            ORDER BY execution_timestamp DESC
            LIMIT %s OFFSET %s
        """
        
        results = db_connection.execute_query(
            query,
            (strategy_id, limit, offset),
            fetch_all=True
        )
        
        return {
            "executions": results or [],
            "count": len(results or []),
            "limit": limit,
            "offset": offset
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting executions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{strategy_id}/statistics")
async def get_trade_statistics(
    strategy_id: str,
    authorization: Optional[str] = Header(None),
    wallet_address: Optional[str] = Header(None, alias="X-Wallet-Address")
):
    """Get trading performance statistics for a strategy"""
    user_id, _ = await get_authenticated_user(authorization, wallet_address)
    
    try:
        # Verify strategy ownership
        strategy_query = """
            SELECT id FROM user_strategies
            WHERE id = %s::uuid AND user_id = %s::uuid
        """
        strategy = db_connection.execute_query(strategy_query, (strategy_id, user_id), fetch_one=True)
        
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        # Get trade statistics
        stats = await paper_trading_dex.get_trade_statistics(strategy_id)
        
        return {
            "strategy_id": strategy_id,
            "statistics": stats
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting trade statistics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{strategy_id}/activate")
async def activate_strategy(
    strategy_id: str,
    request: ActivateStrategyRequest,
    authorization: Optional[str] = Header(None),
    wallet_address: Optional[str] = Header(None, alias="X-Wallet-Address")
):
    """Activate automated execution for a strategy"""
    user_id, _ = await get_authenticated_user(authorization, wallet_address)
    
    try:
        query = """
            UPDATE user_strategies
            SET is_active = TRUE,
                execution_interval = %s,
                updated_at = NOW()
            WHERE id = %s::uuid AND user_id = %s::uuid
            RETURNING id, is_active, execution_interval
        """
        
        result = db_connection.execute_query(
            query,
            (request.interval_minutes, strategy_id, user_id),
            fetch_one=True
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        return {
            "message": "Strategy activated",
            "strategy_id": str(result.get('id')),
            "is_active": result.get('is_active'),
            "execution_interval": result.get('execution_interval'),
            "execution_mode": request.execution_mode
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error activating strategy: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{strategy_id}/deactivate")
async def deactivate_strategy(
    strategy_id: str,
    authorization: Optional[str] = Header(None),
    wallet_address: Optional[str] = Header(None, alias="X-Wallet-Address")
):
    """Deactivate automated execution for a strategy"""
    user_id, _ = await get_authenticated_user(authorization, wallet_address)
    
    try:
        query = """
            UPDATE user_strategies
            SET is_active = FALSE,
                updated_at = NOW()
            WHERE id = %s::uuid AND user_id = %s::uuid
            RETURNING id, is_active
        """
        
        result = db_connection.execute_query(query, (strategy_id, user_id), fetch_one=True)
        
        if not result:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        return {
            "message": "Strategy deactivated",
            "strategy_id": str(result.get('id')),
            "is_active": result.get('is_active')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deactivating strategy: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{strategy_id}/executions/messages")
async def get_executions_as_messages(
    strategy_id: str,
    authorization: Optional[str] = Header(None),
    wallet_address: Optional[str] = Header(None, alias="X-Wallet-Address"),
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0)
):
    """Get executions formatted as chat-style messages"""
    user_id, _ = await get_authenticated_user(authorization, wallet_address)
    
    try:
        # Verify strategy ownership
        strategy_query = """
            SELECT id, name FROM user_strategies
            WHERE id = %s::uuid AND user_id = %s::uuid
        """
        strategy = db_connection.execute_query(strategy_query, (strategy_id, user_id), fetch_one=True)
        
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        # Get executions
        query = """
            SELECT 
                execution_timestamp, decision, confidence, reasoning,
                trade_executed, symbol, side, amount_in, amount_out, price
            FROM strategy_executions
            WHERE strategy_id = %s
            ORDER BY execution_timestamp DESC
            LIMIT %s OFFSET %s
        """
        
        results = db_connection.execute_query(
            query,
            (strategy_id, limit, offset),
            fetch_all=True
        )
        
        # Format as messages
        messages = []
        for exec in results or []:
            timestamp = exec.get('execution_timestamp')
            decision = exec.get('decision')
            confidence = float(exec.get('confidence', 0))
            reasoning = exec.get('reasoning', '')
            trade_executed = exec.get('trade_executed', False)
            
            message = f"**{decision}** (confidence: {confidence:.2%})\n\n{reasoning}"
            
            if trade_executed:
                symbol = exec.get('symbol', '')
                side = exec.get('side', '')
                amount_in = float(exec.get('amount_in', 0))
                amount_out = float(exec.get('amount_out', 0))
                price = float(exec.get('price', 0))
                
                message += f"\n\n✅ Trade executed: {side.upper()} {symbol}\n"
                message += f"Amount: {amount_in:.4f} → {amount_out:.4f}\n"
                message += f"Price: ${price:.6f}"
            
            messages.append({
                "timestamp": timestamp,
                "role": "assistant",
                "content": message,
                "metadata": {
                    "decision": decision,
                    "confidence": confidence,
                    "trade_executed": trade_executed
                }
            })
        
        return {
            "strategy_name": strategy.get('name'),
            "messages": messages,
            "count": len(messages)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting execution messages: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

