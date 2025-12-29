"""
OHLCV Data API endpoints - CoinGecko Integration (OPTIMIZED)
Fetches pre-aggregated OHLCV candles from CoinGecko pool endpoints.
Only 1-minute candles are fetched and stored.

KEY FIXES:
1. Better error handling and validation
2. Improved response formatting with consistent structure
3. Added input validation for all endpoints
4. Better async handling for backfill operations
5. Fixed potential race conditions in pool management
6. Added progress tracking for long-running operations
7. Improved logging and error messages
"""
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from app.services.ohlcv import ohlcv_service
from app.utils.logger import logger
from app.utils.database import db_connection
import asyncio


router = APIRouter(prefix="/ohlcv", tags=["ohlcv"])


# Request/Response Models
class PoolRequest(BaseModel):
    """Request model for adding pools."""
    pool_address: str = Field(..., min_length=1, description="Pool address")
    network: str = Field(default="movement", description="Network ID")
    
    @validator('pool_address')
    def validate_pool_address(cls, v):
        if not v or not v.strip():
            raise ValueError('pool_address cannot be empty')
        return v.strip()


class BackfillRequest(BaseModel):
    """Request model for backfill operations."""
    num_candles: int = Field(default=200, ge=1, le=1000, description="Number of candles to backfill")
    
    @validator('num_candles')
    def validate_num_candles(cls, v):
        if v < 1:
            raise ValueError('num_candles must be at least 1')
        if v > 1000:
            raise ValueError('num_candles cannot exceed 1000')
        return v


class StandardResponse(BaseModel):
    """Standard API response format."""
    status: str = Field(..., description="ok or error")
    message: str = Field(..., description="Human-readable message")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    error: Optional[str] = Field(None, description="Error details if status=error")


@router.post("/backfill/all", response_model=StandardResponse)
async def backfill_all_pools(
    background_tasks: BackgroundTasks,
    request: BackfillRequest = BackfillRequest()
):
    """
    Backfill historical candles for all active pools.
    
    This is a long-running operation that runs in the background.
    
    Args:
        num_candles: Number of historical candles to fetch per pool (1-1000, default: 200)
    
    Returns:
        Status and job information
    """
    from app.services.ohlcv_scheduler import ohlcv_scheduler
    
    if not db_connection.pool:
        raise HTTPException(
            status_code=503,
            detail="Database connection not available"
        )
    
    try:
        # Get all active pools
        query = """
            SELECT pool_address, network, pool_name 
            FROM pools 
            WHERE is_active = TRUE
            ORDER BY created_at DESC
        """
        pools = db_connection.execute_query(query, fetch_all=True)
        
        if not pools:
            return StandardResponse(
                status="error",
                message="No active pools found in database",
                data={"pools_found": 0}
            )
        
        num_pools = len(pools)
        logger.info(f"Starting backfill for {num_pools} pool(s), {request.num_candles} candles each")
        
        # Run backfill in background
        async def run_backfill():
            results = []
            total_stored = 0
            success_count = 0
            error_count = 0
            
            for pool in pools:
                pool_address = pool["pool_address"]
                network = pool.get("network", "movement")
                pool_name = pool.get("pool_name", "Unknown")
                
                try:
                    logger.info(f"Backfilling pool: {pool_name} ({pool_address[:20]}...)")
                    stored = await ohlcv_scheduler.backfill_historical_candles(
                        pool_address=pool_address,
                        network=network,
                        num_candles=request.num_candles
                    )
                    results.append({
                        "pool_address": pool_address,
                        "pool_name": pool_name,
                        "network": network,
                        "candles_stored": stored,
                        "status": "success"
                    })
                    total_stored += stored
                    success_count += 1
                except Exception as e:
                    logger.error(f"Error backfilling pool {pool_address[:20]}...: {e}", exc_info=True)
                    results.append({
                        "pool_address": pool_address,
                        "pool_name": pool_name,
                        "network": network,
                        "error": str(e),
                        "status": "error"
                    })
                    error_count += 1
            
            logger.info(f"Backfill complete: {success_count} succeeded, {error_count} failed, {total_stored} total candles")
        
        # Schedule background task
        background_tasks.add_task(run_backfill)
        
        return StandardResponse(
            status="ok",
            message=f"Backfill started for {num_pools} pool(s) in background",
            data={
                "pools_count": num_pools,
                "candles_per_pool": request.num_candles,
                "estimated_total_candles": num_pools * request.num_candles
            }
        )
        
    except Exception as e:
        logger.error(f"Error starting backfill: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start backfill: {str(e)}"
        )


@router.get("/scheduler/status")
async def get_scheduler_status():
    """
    Get the status of the OHLCV scheduler with detailed information.
    """
    from app.services.ohlcv_scheduler import ohlcv_scheduler
    from app.config import settings
    from app.services.api_tracker import api_tracker
    
    try:
        # Calculate current interval
        pools = ohlcv_scheduler.get_pools_from_db()
        num_pools = len(pools)
        current_interval = ohlcv_scheduler.calculate_scheduler_interval(num_pools)
        
        status = {
            "scheduler": {
                "enabled": settings.OHLCV_SCHEDULER_ENABLED,
                "running": ohlcv_scheduler.running,
                "pools_in_memory": len(ohlcv_scheduler.pools),
                "pools_from_database": num_pools,
                "current_interval_seconds": current_interval,
                "current_interval_minutes": round(current_interval / 60, 1),
                "configured_interval_seconds": settings.OHLCV_SCHEDULER_INTERVAL_SECONDS,
                "lookback_minutes": settings.OHLCV_SCHEDULER_LOOKBACK_MINUTES,
            }
        }
        
        # Get database statistics
        if db_connection.pool:
            try:
                # Active pools count
                query = "SELECT COUNT(*) as count FROM pools WHERE is_active = TRUE"
                result = db_connection.execute_query(query, fetch_one=True)
                active_pools = result.get("count", 0) if result else 0
                
                # Total pools count
                query = "SELECT COUNT(*) as count FROM pools"
                result = db_connection.execute_query(query, fetch_one=True)
                total_pools = result.get("count", 0) if result else 0
                
                # Total candles
                query = "SELECT COUNT(*) as count FROM ohlcv_candles"
                result = db_connection.execute_query(query, fetch_one=True)
                total_candles = result.get("count", 0) if result else 0
                
                # Candles per pool (top 5)
                query = """
                    SELECT p.pool_name, p.pool_address, COUNT(o.id) as candle_count
                    FROM pools p
                    LEFT JOIN ohlcv_candles o ON p.id = o.pool_id
                    WHERE p.is_active = TRUE
                    GROUP BY p.id, p.pool_name, p.pool_address
                    ORDER BY candle_count DESC
                    LIMIT 5
                """
                top_pools = db_connection.execute_query(query, fetch_all=True)
                
                status["database"] = {
                    "connected": True,
                    "active_pools": active_pools,
                    "total_pools": total_pools,
                    "total_candles": total_candles,
                    "top_pools": top_pools or []
                }
            except Exception as e:
                status["database"] = {
                    "connected": True,
                    "error": str(e)
                }
        else:
            status["database"] = {
                "connected": False,
                "message": "Database connection not available"
            }
        
        # Add API usage stats
        usage_stats = api_tracker.get_usage_stats()
        status["api_usage"] = usage_stats
        
        return status
        
    except Exception as e:
        logger.error(f"Error getting scheduler status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get scheduler status: {str(e)}"
        )


@router.get("/api/usage")
async def get_api_usage():
    """
    Get CoinGecko API usage statistics with detailed breakdown.
    """
    from app.services.api_tracker import api_tracker
    
    try:
        usage_stats = api_tracker.get_usage_stats()
        return {
            "status": "ok",
            "data": usage_stats
        }
    except Exception as e:
        logger.error(f"Error getting API usage: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get API usage: {str(e)}"
        )


@router.get("/db/test")
async def test_database():
    """
    Test database connection and check if CoinGecko tables exist.
    Useful for debugging database storage issues.
    """
    if not db_connection.pool:
        raise HTTPException(
            status_code=503,
            detail="Database connection pool not initialized. Check DATABASE_URL configuration."
        )
    
    try:
        # Test connection
        test_result = db_connection.test_connection()
        if not test_result:
            raise HTTPException(
                status_code=503,
                detail="Database connection test failed"
            )
        
        # Check if tables exist
        tables_query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('pools', 'ohlcv_candles', 'technical_indicators')
            ORDER BY table_name
        """
        tables = db_connection.execute_query(tables_query, fetch_all=True)
        table_names = [t.get('table_name') for t in tables] if tables else []
        
        # Count records in each table
        table_stats = {}
        
        for table_name in ['pools', 'ohlcv_candles', 'technical_indicators']:
            exists = table_name in table_names
            count = 0
            
            if exists:
                try:
                    count_query = f"SELECT COUNT(*) as count FROM {table_name}"
                    result = db_connection.execute_query(count_query, fetch_one=True)
                    count = result.get('count', 0) if result else 0
                except Exception as e:
                    logger.warning(f"Could not count records in {table_name}: {e}")
            
            table_stats[table_name] = {
                "exists": exists,
                "record_count": count
            }
        
        return {
            "status": "ok",
            "message": "Database connection successful",
            "connection": {
                "pool_initialized": True,
                "connection_test": True
            },
            "tables": table_stats
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database test error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Database test failed: {str(e)}"
        )


@router.post("/db/reset-sequence")
async def reset_id_sequence():
    """
    Reset the ohlcv_candles ID sequence to continue from the current max ID.
    This ensures new inserts start from the correct number.
    """
    from app.utils.db_init import reset_sequence
    
    if not db_connection.pool:
        raise HTTPException(
            status_code=503,
            detail="Database connection not available"
        )
    
    try:
        # Get current max ID before reset
        max_id_query = "SELECT COALESCE(MAX(id), 0) as max_id FROM ohlcv_candles"
        max_result = db_connection.execute_query(max_id_query, fetch_one=True)
        max_id = max_result.get('max_id', 0) if max_result else 0
        
        # Reset sequence
        reset_sequence()
        
        # Get sequence value after reset
        seq_query = "SELECT last_value FROM ohlcv_candles_id_seq"
        seq_result = db_connection.execute_query(seq_query, fetch_one=True)
        next_id = seq_result.get('last_value', 1) if seq_result else 1
        
        return {
            "status": "ok",
            "message": "Sequence reset successfully",
            "data": {
                "max_existing_id": max_id,
                "next_id_will_be": next_id
            }
        }
    except Exception as e:
        logger.error(f"Error resetting sequence: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset sequence: {str(e)}"
        )


@router.post("/db/init")
async def init_database(force_recreate: bool = False):
    """
    Initialize CoinGecko database tables.
    
    Args:
        force_recreate: If True, drop all tables and recreate from scratch (DANGEROUS!)
    """
    from app.utils.db_init import init_coingecko_tables, drop_all_coingecko_tables
    
    if not db_connection.pool:
        raise HTTPException(
            status_code=503,
            detail="Database connection pool not initialized. Check DATABASE_URL configuration."
        )
    
    try:
        if force_recreate:
            logger.warning("Force recreate requested - dropping all CoinGecko tables!")
            if not drop_all_coingecko_tables():
                raise HTTPException(
                    status_code=500,
                    detail="Failed to drop existing tables"
                )
            logger.info("All CoinGecko tables dropped successfully")
        
        success = init_coingecko_tables(force_recreate=force_recreate)
        
        if success:
            return {
                "status": "ok",
                "message": f"CoinGecko tables initialized successfully",
                "data": {
                    "force_recreate": force_recreate
                }
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to initialize CoinGecko tables. Check logs for details."
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database initialization error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Database initialization failed: {str(e)}"
        )


@router.get("/pools")
async def get_monitored_pools(
    active_only: bool = Query(True, description="Return only active pools"),
    limit: Optional[int] = Query(None, ge=1, le=1000, description="Maximum number of pools to return")
):
    """
    Get list of pools being monitored by the scheduler.
    
    Args:
        active_only: If True, return only active pools (default: True)
        limit: Maximum number of pools to return
    """
    if not db_connection.pool:
        raise HTTPException(
            status_code=503,
            detail="Database connection not available"
        )
    
    try:
        query = """
            SELECT 
                p.id, p.pool_address, p.network, p.is_active, p.pool_name, 
                p.token_a_symbol, p.token_a_address, 
                p.token_b_symbol, p.token_b_address, 
                p.created_at, p.updated_at,
                COUNT(o.id) as candle_count
            FROM pools p
            LEFT JOIN ohlcv_candles o ON p.id = o.pool_id
        """
        
        conditions = []
        params = []
        
        if active_only:
            conditions.append("p.is_active = TRUE")
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " GROUP BY p.id ORDER BY p.created_at DESC"
        
        if limit:
            query += f" LIMIT {limit}"
        
        pools = db_connection.execute_query(query, tuple(params) if params else None, fetch_all=True)
        
        return {
            "status": "ok",
            "data": {
                "pools": pools or [],
                "count": len(pools) if pools else 0,
                "active_only": active_only
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching monitored pools: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch pools: {str(e)}"
        )


@router.post("/pools/{pool_address}")
async def add_pool_to_monitoring(
    pool_address: str,
    network: str = Query("movement", description="Network ID"),
    fetch_meta: bool = Query(True, description="Fetch token metadata from CoinGecko")
):
    """
    Add a pool to monitoring. The scheduler will automatically fetch data for it.
    
    Args:
        pool_address: Pool address to add
        network: Network ID (default: "movement")
        fetch_meta: If True, fetch token metadata from CoinGecko (default: True)
    """
    if not db_connection.pool:
        raise HTTPException(
            status_code=503,
            detail="Database connection not available"
        )
    
    # Validate pool_address
    if not pool_address or not pool_address.strip():
        raise HTTPException(
            status_code=400,
            detail="pool_address cannot be empty"
        )
    
    pool_address = pool_address.strip()
    
    try:
        # Insert or update pool
        query = """
            INSERT INTO pools (pool_address, network, is_active)
            VALUES (%s, %s, %s)
            ON CONFLICT (pool_address) 
            DO UPDATE SET is_active = TRUE, updated_at = NOW()
            RETURNING id, pool_address, network, is_active, 
                      token_a_symbol, token_a_address, token_b_symbol, token_b_address
        """
        result = db_connection.execute_query(
            query, 
            (pool_address, network, True), 
            fetch_one=True
        )
        
        if not result:
            raise HTTPException(
                status_code=500,
                detail="Failed to add pool to database"
            )
        
        # Add to scheduler if it's running
        from app.services.ohlcv_scheduler import ohlcv_scheduler
        ohlcv_scheduler.add_pool(pool_address, network)
        
        # Fetch token metadata if requested
        if fetch_meta:
            try:
                from app.services.coingecko import get_pool_ohlcv
                
                logger.info(f"Fetching token metadata for pool {pool_address[:20]}...")
                candles, meta_info = await get_pool_ohlcv(
                    pool_address=pool_address,
                    network=network,
                    timeframe="minute",
                    aggregate=1,
                    limit=1,
                    currency="usd",
                    token="quote"
                )
                
                if meta_info and meta_info.get('base') and meta_info.get('quote'):
                    base_symbol = meta_info['base'].get('symbol', '')
                    base_address = meta_info['base'].get('address', '')
                    quote_symbol = meta_info['quote'].get('symbol', '')
                    quote_address = meta_info['quote'].get('address', '')
                    
                    if base_symbol and quote_symbol:
                        update_query = """
                            UPDATE pools
                            SET 
                                token_a_symbol = %s, 
                                token_a_address = %s,
                                token_b_symbol = %s, 
                                token_b_address = %s,
                                pool_name = %s,
                                updated_at = NOW()
                            WHERE id = %s
                        """
                        pool_name = f"{base_symbol}/{quote_symbol}"
                        db_connection.execute_query(
                            update_query, 
                            (base_symbol, base_address, quote_symbol, quote_address, pool_name, result['id']), 
                            fetch_all=False
                        )
                        result['token_a_symbol'] = base_symbol
                        result['token_a_address'] = base_address
                        result['token_b_symbol'] = quote_symbol
                        result['token_b_address'] = quote_address
                        result['pool_name'] = pool_name
                        logger.info(f"Updated pool with tokens: {pool_name}")
                else:
                    logger.warning(f"No token metadata found for pool {pool_address[:20]}...")
                    
            except Exception as e:
                logger.warning(f"Could not fetch token metadata for pool {pool_address[:20]}...: {e}")
        
        return {
            "status": "ok",
            "message": f"Pool added to monitoring successfully",
            "data": {
                "pool": result
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding pool to monitoring: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to add pool: {str(e)}"
        )


@router.delete("/pools/{pool_address}")
async def remove_pool_from_monitoring(
    pool_address: str,
    network: str = Query("movement", description="Network ID"),
    delete_data: bool = Query(False, description="Also delete all candle data for this pool")
):
    """
    Remove a pool from monitoring (sets is_active = False).
    
    Args:
        pool_address: Pool address to remove
        network: Network ID (default: "movement")
        delete_data: If True, also delete all OHLCV and indicator data (default: False)
    """
    if not db_connection.pool:
        raise HTTPException(
            status_code=503,
            detail="Database connection not available"
        )
    
    try:
        if delete_data:
            # Delete all related data
            logger.warning(f"Deleting all data for pool {pool_address[:20]}...")
            
            # Get pool ID first
            id_query = "SELECT id FROM pools WHERE pool_address = %s AND network = %s"
            pool_result = db_connection.execute_query(id_query, (pool_address, network), fetch_one=True)
            
            if pool_result:
                pool_id = pool_result['id']
                
                # Delete indicators
                db_connection.execute_query(
                    "DELETE FROM technical_indicators WHERE pool_id = %s",
                    (pool_id,),
                    fetch_all=False
                )
                
                # Delete candles
                db_connection.execute_query(
                    "DELETE FROM ohlcv_candles WHERE pool_id = %s",
                    (pool_id,),
                    fetch_all=False
                )
                
                # Delete pool
                db_connection.execute_query(
                    "DELETE FROM pools WHERE id = %s",
                    (pool_id,),
                    fetch_all=False
                )
                
                logger.info(f"Deleted pool and all related data for {pool_address[:20]}...")
            
            result = {"pool_address": pool_address, "network": network, "deleted": True}
        else:
            # Just deactivate
            query = """
                UPDATE pools
                SET is_active = FALSE, updated_at = NOW()
                WHERE pool_address = %s AND network = %s
                RETURNING id, pool_address, network, is_active
            """
            result = db_connection.execute_query(query, (pool_address, network), fetch_one=True)
            
            if not result:
                raise HTTPException(
                    status_code=404,
                    detail="Pool not found"
                )
        
        # Remove from scheduler
        from app.services.ohlcv_scheduler import ohlcv_scheduler
        ohlcv_scheduler.remove_pool(pool_address, network)
        
        return {
            "status": "ok",
            "message": f"Pool {'deleted' if delete_data else 'deactivated'} successfully",
            "data": {
                "pool": result,
                "data_deleted": delete_data
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing pool from monitoring: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to remove pool: {str(e)}"
        )


@router.get("/candles")
async def get_candles(
    pool_address: str = Query(..., description="Pool address"),
    network: str = Query("movement", description="Network ID"),
    limit: int = Query(500, ge=1, le=5000, description="Maximum number of candles"),
    hours_back: Optional[int] = Query(None, ge=1, le=720, description="Only get candles from last N hours"),
    from_db: bool = Query(True, description="Fetch from database (True) or CoinGecko API (False)"),
    store: bool = Query(False, description="Store to DB if fetching from API")
):
    """
    Get OHLCV candles for a pool (1-minute data only).
    
    Args:
        pool_address: Pool address (required)
        network: Network ID (default: "movement")
        limit: Maximum number of candles (1-5000, default: 500)
        hours_back: Optional - only get candles from last N hours (1-720)
        from_db: If True, fetch from database; if False, fetch from CoinGecko API
        store: If True and from_db=False, store fetched data to database
    """
    if not pool_address or not pool_address.strip():
        raise HTTPException(
            status_code=400,
            detail="pool_address is required"
        )
    
    pool_address = pool_address.strip()
    
    try:
        if from_db:
            # Fetch from database
            if not db_connection.pool:
                raise HTTPException(
                    status_code=503,
                    detail="Database connection not available"
                )
            
            # Get pool ID
            pool_query = """
                SELECT id, pool_name, token_a_symbol, token_b_symbol 
                FROM pools 
                WHERE pool_address = %s AND network = %s
            """
            pool_result = db_connection.execute_query(
                pool_query, 
                (pool_address, network), 
                fetch_one=True
            )
            
            if not pool_result:
                raise HTTPException(
                    status_code=404,
                    detail=f"Pool not found in database. Add it first via POST /ohlcv/pools/{pool_address}"
                )
            
            pool_id = pool_result['id']
            
            # Build query
            candles_query = """
                SELECT timestamp, open_price, high_price, low_price, close_price, volume
                FROM ohlcv_candles
                WHERE pool_id = %s
            """
            params = [pool_id]
            
            if hours_back:
                candles_query += " AND timestamp >= NOW() - INTERVAL '%s hours'"
                params.append(hours_back)
            
            candles_query += " ORDER BY timestamp DESC LIMIT %s"
            params.append(limit)
            
            rows = db_connection.execute_query(candles_query, tuple(params), fetch_all=True)
            
            if not rows:
                return {
                    "status": "ok",
                    "message": "No candles found in database",
                    "data": {
                        "pool_address": pool_address,
                        "network": network,
                        "pool_name": pool_result.get('pool_name'),
                        "timeframe": "1m",
                        "candles": [],
                        "count": 0,
                        "source": "database"
                    }
                }
            
            # Convert to dict format
            candles = [
                {
                    "timestamp": int(row['timestamp'].timestamp()) if hasattr(row['timestamp'], 'timestamp') else row['timestamp'],
                    "open": float(row['open_price']),
                    "high": float(row['high_price']),
                    "low": float(row['low_price']),
                    "close": float(row['close_price']),
                    "volume": float(row['volume'])
                }
                for row in rows
            ]
            
            # Reverse to get chronological order
            candles.reverse()
            
            return {
                "status": "ok",
                "data": {
                    "pool_address": pool_address,
                    "network": network,
                    "pool_name": pool_result.get('pool_name'),
                    "pair": f"{pool_result.get('token_a_symbol', '?')}/{pool_result.get('token_b_symbol', '?')}",
                    "timeframe": "1m",
                    "candles": candles,
                    "count": len(candles),
                    "source": "database"
                }
            }
        else:
            # Fetch from CoinGecko API
            candles = await ohlcv_service.get_candles(
                pool_address=pool_address,
                network=network,
                timeframe="1m",
                limit=limit,
                hours_back=hours_back
            )
            
            # Optionally store to database
            if store and candles:
                try:
                    await ohlcv_service._store_candles_to_db(
                        pool_address=pool_address,
                        network=network,
                        candles=candles
                    )
                    logger.info(f"Stored {len(candles)} candles for pool {pool_address[:20]}...")
                except Exception as e:
                    logger.warning(f"Failed to store candles: {e}")
            
            # Limit results
            if limit and len(candles) > limit:
                candles = candles[-limit:]
            
            return {
                "status": "ok",
                "data": {
                    "pool_address": pool_address,
                    "network": network,
                    "timeframe": "1m",
                    "candles": candles,
                    "count": len(candles),
                    "source": "coingecko_api",
                    "stored_to_db": store
                }
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching OHLCV candles: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch candles: {str(e)}"
        )


@router.get("/candles/by-pool")
async def get_candles_by_pool(
    pool_address: str = Query(..., description="Pool address"),
    network: str = Query("movement", description="Network ID"),
    limit: int = Query(500, ge=1, le=5000, description="Maximum number of candles"),
    hours_back: Optional[int] = Query(None, ge=1, le=720, description="Only get candles from last N hours")
):
    """
    Convenience endpoint - get OHLCV candles by pool address from database.
    Same as GET /candles with from_db=True.
    """
    return await get_candles(
        pool_address=pool_address,
        network=network,
        limit=limit,
        hours_back=hours_back,
        from_db=True,
        store=False
    )