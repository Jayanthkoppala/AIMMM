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


async def get_authenticated_user(authorization: Optional[str]) -> tuple[str, str]:
    """
    Verify Privy access token and return user_id and wallet_address.
    Raises HTTPException if authentication fails.
    
    For development: If Privy is not configured, uses a test user.
    """
    if not authorization or not authorization.startswith("Bearer "):
        # Development mode: check if Privy is configured
        if not settings.PRIVY_APP_ID or not settings.PRIVY_APP_SECRET:
            logger.warning("Privy not configured - using test user for development")
            return "test-user-123", "0x0000000000000000000000000000000000000000000000000000000000000000"
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    access_token = authorization.replace("Bearer ", "")
    
    # Try to verify with Privy
    privy_user = await privy_service.privy_service.verify_access_token(access_token)
    
    if not privy_user:
        # Development mode fallback
        if not settings.PRIVY_APP_ID or not settings.PRIVY_APP_SECRET:
            logger.warning("Privy verification failed - using test user for development")
            return "test-user-123", "0x0000000000000000000000000000000000000000000000000000000000000000"
        raise HTTPException(status_code=401, detail="Invalid access token")
    
    user_id = privy_user.get('id')
    wallet_address = privy_user.get('wallet', {}).get('address', '')
    
    return user_id, wallet_address


@router.post("")
async def create_strategy(
    request: CreateStrategyRequest,
    authorization: Optional[str] = Header(None)
):
    """Create a new trading strategy"""
    user_id, wallet_address = await get_authenticated_user(authorization)
    
    try:
        # Convert strategy config to JSON
        config_json = json.dumps(request.strategy_config.dict())
        
        # pool_id is now a simple integer (or None)
        pool_id_value = request.pool_id
        
        query = """
            INSERT INTO user_strategies (
                user_id, wallet_address, name, description, visibility, pool_id, pool_address, execution_interval, strategy_config
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
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
    visibility: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """List user's strategies"""
    user_id, _ = await get_authenticated_user(authorization)
    
    try:
        # Build query with filters
        conditions = ["user_id = %s"]
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
        
        return {
            "strategies": results or [],
            "count": len(results or []),
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Error fetching strategies: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{strategy_id}")
async def get_strategy(
    strategy_id: str,
    authorization: Optional[str] = Header(None)
):
    """Get a specific strategy"""
    user_id, _ = await get_authenticated_user(authorization)
    
    try:
        query = """
            SELECT *
            FROM user_strategies
            WHERE id = %s AND user_id = %s
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
    authorization: Optional[str] = Header(None)
):
    """Update a strategy"""
    user_id, _ = await get_authenticated_user(authorization)
    
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
            WHERE id = %s AND user_id = %s
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
    authorization: Optional[str] = Header(None)
):
    """Delete a strategy"""
    user_id, _ = await get_authenticated_user(authorization)
    
    try:
        query = """
            DELETE FROM user_strategies
            WHERE id = %s AND user_id = %s
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
    authorization: Optional[str] = Header(None)
):
    """Manually execute a strategy"""
    user_id, _ = await get_authenticated_user(authorization)
    
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
    include_closed: bool = Query(False)
):
    """Get current trading state for a strategy"""
    user_id, _ = await get_authenticated_user(authorization)
    
    try:
        # Verify strategy ownership
        strategy_query = """
            SELECT id FROM user_strategies
            WHERE id = %s AND user_id = %s
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
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    include_market_data: bool = Query(False)
):
    """Get execution history for a strategy"""
    user_id, _ = await get_authenticated_user(authorization)
    
    try:
        # Verify strategy ownership
        strategy_query = """
            SELECT id FROM user_strategies
            WHERE id = %s AND user_id = %s
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
    authorization: Optional[str] = Header(None)
):
    """Get trading performance statistics for a strategy"""
    user_id, _ = await get_authenticated_user(authorization)
    
    try:
        # Verify strategy ownership
        strategy_query = """
            SELECT id FROM user_strategies
            WHERE id = %s AND user_id = %s
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
    authorization: Optional[str] = Header(None)
):
    """Activate automated execution for a strategy"""
    user_id, _ = await get_authenticated_user(authorization)
    
    try:
        query = """
            UPDATE user_strategies
            SET is_active = TRUE,
                execution_interval = %s,
                updated_at = NOW()
            WHERE id = %s AND user_id = %s
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
    authorization: Optional[str] = Header(None)
):
    """Deactivate automated execution for a strategy"""
    user_id, _ = await get_authenticated_user(authorization)
    
    try:
        query = """
            UPDATE user_strategies
            SET is_active = FALSE,
                updated_at = NOW()
            WHERE id = %s AND user_id = %s
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
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0)
):
    """Get executions formatted as chat-style messages"""
    user_id, _ = await get_authenticated_user(authorization)
    
    try:
        # Verify strategy ownership
        strategy_query = """
            SELECT id, name FROM user_strategies
            WHERE id = %s AND user_id = %s
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

