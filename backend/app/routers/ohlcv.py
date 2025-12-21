"""
OHLCV Data Collection API endpoints.
"""
from fastapi import APIRouter, HTTPException
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
from app.services.ohlcv_collector import ohlcv_collector
from app.utils.logger import logger
from app.utils.database import db_connection


router = APIRouter(prefix="/ohlcv", tags=["ohlcv"])


class TokenPairRegister(BaseModel):
    token_a_address: str
    token_b_address: str
    switchboard_feed_id: str
    token_a_symbol: Optional[str] = None
    token_b_symbol: Optional[str] = None


class TokenPairResponse(BaseModel):
    id: str
    token_a_address: str
    token_b_address: str
    switchboard_feed_id: str
    is_active: bool
    created_at: str


@router.post("/register", response_model=TokenPairResponse)
async def register_token_pair(pair: TokenPairRegister):
    """
    Register a token pair for OHLCV data collection.
    """
    try:
        pair_id = await ohlcv_collector.register_token_pair(
            token_a_address=pair.token_a_address,
            token_b_address=pair.token_b_address,
            switchboard_feed_id=pair.switchboard_feed_id,
            token_a_symbol=pair.token_a_symbol,
            token_b_symbol=pair.token_b_symbol
        )
        
        if not pair_id:
            raise HTTPException(status_code=500, detail="Failed to register token pair")
        
        # Fetch the created pair
        query = """
            SELECT id, token_a_address, token_b_address, switchboard_feed_id, is_active, created_at
            FROM token_pairs
            WHERE id = %s
        """
        result = db_connection.execute_query(query, params=(pair_id,), fetch_one=True)
        
        if not result:
            raise HTTPException(status_code=404, detail="Token pair not found after creation")
        
        return TokenPairResponse(
            id=str(result['id']),
            token_a_address=result['token_a_address'],
            token_b_address=result['token_b_address'],
            switchboard_feed_id=result['switchboard_feed_id'],
            is_active=result['is_active'],
            created_at=str(result['created_at'])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering token pair: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pairs", response_model=List[TokenPairResponse])
async def list_token_pairs():
    """List all registered token pairs."""
    try:
        pairs = await ohlcv_collector.get_active_token_pairs()
        
        result = []
        for pair in pairs:
            result.append(TokenPairResponse(
                id=str(pair['id']),
                token_a_address=pair['token_a_address'],
                token_b_address=pair['token_b_address'],
                switchboard_feed_id=pair['switchboard_feed_id'],
                is_active=True,
                created_at=str(pair.get('created_at', datetime.utcnow()))
            ))
        
        return result
        
    except Exception as e:
        logger.error(f"Error listing token pairs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start")
async def start_collection():
    """Start OHLCV data collection."""
    try:
        await ohlcv_collector.start()
        return {"status": "started", "message": "OHLCV collection started"}
    except Exception as e:
        logger.error(f"Error starting collection: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_collection():
    """Stop OHLCV data collection."""
    try:
        await ohlcv_collector.stop()
        return {"status": "stopped", "message": "OHLCV collection stopped"}
    except Exception as e:
        logger.error(f"Error stopping collection: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_collection_status():
    """Get OHLCV collection status."""
    return {
        "is_running": ohlcv_collector.is_running,
        "poll_interval_seconds": ohlcv_collector.poll_interval
    }


@router.get("/candles/{token_pair_id}")
async def get_candles(
    token_pair_id: str,
    timeframe: str = "1m",
    limit: int = 100
):
    """
    Get OHLCV candles for a token pair.
    
    Args:
        token_pair_id: UUID of the token pair
        timeframe: '1m', '5m', '15m', '1h', '4h', '1d'
        limit: Number of candles to return (default: 100)
    """
    try:
        query = """
            SELECT timestamp, open_price, high_price, low_price, close_price, volume, trade_count
            FROM ohlcv_candles
            WHERE token_pair_id = %s AND timeframe = %s
            ORDER BY timestamp DESC
            LIMIT %s
        """
        candles = db_connection.execute_query(
            query,
            params=(token_pair_id, timeframe, limit),
            fetch_all=True
        )
        
        return {
            "token_pair_id": token_pair_id,
            "timeframe": timeframe,
            "candles": candles or []
        }
        
    except Exception as e:
        logger.error(f"Error fetching candles: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

