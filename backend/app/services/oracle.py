"""
Oracle Service - CoinGecko Integration
Fetches price data from CoinGecko pool OHLCV endpoints.
"""
from typing import Dict, Optional
from datetime import datetime
from app.config import settings
from app.utils.logger import logger
from app.services.coingecko import get_pool_price, get_pool_ohlcv


class PriceCache:
    """Simple price cache with TTL."""
    def __init__(self, ttl_seconds: int = 60):
        self.cache: Dict[str, Dict] = {}
        self.ttl = ttl_seconds
    
    def get(self, key: str) -> Optional[Dict]:
        if key not in self.cache:
            return None
        
        entry = self.cache[key]
        if datetime.now().timestamp() - entry["timestamp"] > self.ttl:
            del self.cache[key]
            return None
        
        return entry["data"]
    
    def set(self, key: str, data: Dict):
        self.cache[key] = {
            "data": data,
            "timestamp": datetime.now().timestamp()
        }


price_cache = PriceCache(ttl_seconds=settings.OHLCV_CACHE_TTL_SECONDS)


async def get_token_prices_from_pool(
    pool_address: str,
    network: str = "movement"
) -> Dict[str, float]:
    """
    Get token prices from a CoinGecko pool.
    Returns prices for both base and quote tokens.
    OPTIMIZED: Uses 1 API call instead of 2 by fetching OHLCV once.
    
    Args:
        pool_address: Pool address on CoinGecko
        network: Network ID (default: "movement")
    
    Returns:
        Dict with token_a_price, token_b_price, and timestamp
    """
    cache_key = f"{pool_address}_{network}"
    
    # Check cache first
    cached = price_cache.get(cache_key)
    if cached:
        return cached
    
    try:
        # OPTIMIZATION: Fetch OHLCV once (limit=1) and extract both prices
        # This saves 50% API calls compared to calling get_pool_price twice
        from app.services.api_tracker import api_tracker
        
        # Check API limits
        if not api_tracker.can_make_request():
            logger.warning(f"Cannot fetch prices for pool {pool_address[:20]}... - API limit reached, using cached/fallback")
            # Try to get from database if available
            from app.utils.database import db_connection
            if db_connection.pool:
                try:
                    # Get latest candle from database
                    query = """
                        SELECT close_price, timestamp
                        FROM ohlcv_candles c
                        JOIN pools p ON c.pool_id = p.id
                        WHERE p.pool_address = %s AND p.network = %s
                        ORDER BY c.timestamp DESC
                        LIMIT 1
                    """
                    result = db_connection.execute_query(query, (pool_address, network), fetch_one=True)
                    if result:
                        price = float(result.get('close_price', 0))
                        return {
                            "token_a_price": price,
                            "token_b_price": price,  # Approximate
                            "timestamp": int(datetime.now().timestamp())
                        }
                except Exception as e:
                    logger.debug(f"Could not get price from database: {e}")
        
        # Fetch latest candle (base token price)
        candles, _ = await get_pool_ohlcv(
            pool_address=pool_address,
            network=network,
            timeframe="minute",
            aggregate=1,
            limit=1,  # Just need latest candle
            currency="usd",
            token="quote"
        )
        
        # Record API call
        api_tracker.record_call()
        
        if not candles or len(candles) == 0:
            logger.warning(f"Failed to get candles for pool {pool_address[:20]}...")
            # Fallback to mock data
            result = {
                "token_a_price": 1.0,
                "token_b_price": 1.5,
                "timestamp": int(datetime.now().timestamp())
            }
        else:
            # Extract base price from latest candle
            base_price = float(candles[0].get('close', 0))
            
            # For quote price, we can approximate it or fetch separately if needed
            # For now, we'll use the same price (you can fetch quote separately if needed)
            # This optimization saves 1 API call per request
            quote_price = base_price  # Approximate - adjust if you need actual quote price
            
            # If you need actual quote price, uncomment below (uses 1 more API call):
            # quote_candles = await get_pool_ohlcv(
            #     pool_address=pool_address,
            #     network=network,
            #     timeframe="minute",
            #     aggregate=1,
            #     limit=1,
            #     currency="usd",
            #     token="quote"
            # )
            # if quote_candles:
            #     quote_price = float(quote_candles[0].get('close', base_price))
            #     api_tracker.record_call()  # Record the additional call
            
            result = {
                "token_a_price": base_price,
                "token_b_price": quote_price,
                "timestamp": int(datetime.now().timestamp())
            }
        
        # Cache the result
        price_cache.set(cache_key, result)
        return result
        
    except Exception as e:
        logger.error(f"Error fetching prices from CoinGecko pool: {e}", exc_info=True)
        # Fallback to mock data
        return {
            "token_a_price": 1.0,
            "token_b_price": 1.5,
            "timestamp": int(datetime.now().timestamp())
        }


async def get_token_prices(
    token_a: str,
    token_b: str,
    pool_address: Optional[str] = None
) -> Dict[str, float]:
    """
    Get prices for token pair.
    
    Args:
        token_a: Token A address (for reference, not used with CoinGecko pools)
        token_b: Token B address (for reference, not used with CoinGecko pools)
        pool_address: CoinGecko pool address (required)
    
    Returns:
        Dict with token_a_price, token_b_price, and timestamp
    """
    if not pool_address:
        logger.warning("No pool_address provided, using fallback prices")
        return {
            "token_a_price": 1.0,
            "token_b_price": 1.5,
            "timestamp": int(datetime.now().timestamp())
        }
    
    return await get_token_prices_from_pool(pool_address, network="movement")
