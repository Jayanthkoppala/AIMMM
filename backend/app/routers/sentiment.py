"""
Sentiment Analysis API endpoints
"""
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import Optional
from app.models.agent import SentimentAnalysis, TokenSentiment
from app.services import sentiment, sentiment_scheduler
from app.utils.logger import logger
from app.utils.database import db_connection

router = APIRouter(prefix="/sentiment", tags=["sentiment"])


@router.get("/analyze", response_model=SentimentAnalysis)
async def analyze_sentiment(
    token_a: str = Query(..., description="Token A address"),
    token_b: str = Query(..., description="Token B address"),
    token_a_symbol: Optional[str] = Query(None, description="Token A symbol (optional, for better analysis)"),
    token_b_symbol: Optional[str] = Query(None, description="Token B symbol (optional, for better analysis)"),
    timeframe: str = Query("24h", description="Time period for analysis (e.g., '24h', '7d')"),
    pool_address: Optional[str] = Query(None, description="Pool address to fetch token symbols from database")
):
    """
    Analyze sentiment for a token pair.
    
    If pool_address is provided, token symbols will be fetched from the database.
    Otherwise, use provided token_a_symbol and token_b_symbol, or fall back to address prefixes.
    """
    try:
        # Try to get token symbols from database if pool_address is provided
        if pool_address and db_connection.pool:
            try:
                query = """
                    SELECT token_a_symbol, token_b_symbol, token_a_address, token_b_address
                    FROM pools
                    WHERE pool_address = %s AND network = 'movement'
                    LIMIT 1
                """
                pool_info = db_connection.execute_query(
                    query,
                    (pool_address,),
                    fetch_one=True
                )
                if pool_info:
                    # Match addresses to determine which is token_a and token_b
                    if pool_info.get('token_a_address') == token_a:
                        token_a_symbol = token_a_symbol or pool_info.get('token_a_symbol')
                        token_b_symbol = token_b_symbol or pool_info.get('token_b_symbol')
                    elif pool_info.get('token_b_address') == token_a:
                        token_a_symbol = token_a_symbol or pool_info.get('token_b_symbol')
                        token_b_symbol = token_b_symbol or pool_info.get('token_a_symbol')
                    elif pool_info.get('token_a_address') == token_b:
                        token_a_symbol = token_a_symbol or pool_info.get('token_b_symbol')
                        token_b_symbol = token_b_symbol or pool_info.get('token_a_symbol')
                    elif pool_info.get('token_b_address') == token_b:
                        token_a_symbol = token_a_symbol or pool_info.get('token_a_symbol')
                        token_b_symbol = token_b_symbol or pool_info.get('token_b_symbol')
            except Exception as e:
                logger.debug(f"Could not fetch token symbols from database: {e}")
        
        # Perform sentiment analysis
        sentiment_result = await sentiment.sentiment_analyzer.analyze_token_pair_sentiment(
            token_a_address=token_a,
            token_b_address=token_b,
            token_a_symbol=token_a_symbol,
            token_b_symbol=token_b_symbol,
            timeframe=timeframe
        )
        
        # Convert to response model
        return SentimentAnalysis(
            token_a=TokenSentiment(
                token_symbol=sentiment_result['token_a'].get('token_symbol', 'A'),
                token_address=sentiment_result['token_a'].get('token_address', token_a),
                sentiment_score=sentiment_result['token_a'].get('sentiment_score', 0.0),
                sentiment_label=sentiment_result['token_a'].get('sentiment_label', 'neutral'),
                confidence=sentiment_result['token_a'].get('confidence', 0.5),
                key_factors=sentiment_result['token_a'].get('key_factors', []),
                social_volume=sentiment_result['token_a'].get('social_volume', 0),
                mentions_24h=sentiment_result['token_a'].get('mentions_24h', 0),
                dominant_emotion=sentiment_result['token_a'].get('dominant_emotion', 'neutral')
            ),
            token_b=TokenSentiment(
                token_symbol=sentiment_result['token_b'].get('token_symbol', 'B'),
                token_address=sentiment_result['token_b'].get('token_address', token_b),
                sentiment_score=sentiment_result['token_b'].get('sentiment_score', 0.0),
                sentiment_label=sentiment_result['token_b'].get('sentiment_label', 'neutral'),
                confidence=sentiment_result['token_b'].get('confidence', 0.5),
                key_factors=sentiment_result['token_b'].get('key_factors', []),
                social_volume=sentiment_result['token_b'].get('social_volume', 0),
                mentions_24h=sentiment_result['token_b'].get('mentions_24h', 0),
                dominant_emotion=sentiment_result['token_b'].get('dominant_emotion', 'neutral')
            ),
            timeframe=sentiment_result.get('timeframe', timeframe),
            timestamp=sentiment_result.get('timestamp', '')
        )
        
    except Exception as e:
        logger.error(f"Error in sentiment analysis endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze sentiment: {str(e)}"
        )


@router.post("/scheduler/trigger")
async def trigger_sentiment_analysis(background_tasks: BackgroundTasks):
    """
    Manually trigger sentiment analysis for all active pools.
    This bypasses the 24-hour cache and forces a fresh analysis.
    """
    try:
        logger.info("Manual sentiment analysis trigger requested")
        background_tasks.add_task(sentiment_scheduler.sentiment_scheduler._analyze_all_pools)
        return {
            "status": "ok",
            "message": "Sentiment analysis triggered. Check logs for progress."
        }
    except Exception as e:
        logger.error(f"Error triggering sentiment analysis: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to trigger sentiment analysis: {str(e)}"
        )

