"""
OHLCV Service - CoinGecko Integration
Unified service for fetching and formatting OHLCV data from CoinGecko pools.
"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from app.config import settings
from app.utils.logger import logger
from app.services.coingecko import get_pool_ohlcv
from app.utils.database import db_connection


class OHLCVService:
    """
    Service for fetching OHLCV data from CoinGecko.
    CoinGecko provides pre-aggregated candles, so no collection/aggregation needed.
    """
    
    def __init__(self):
        self.cache: Dict[str, Dict] = {}
        self.cache_ttl = settings.OHLCV_CACHE_TTL_SECONDS
    
    async def get_candles(
        self,
        pool_address: str,
        network: str = "movement",
        timeframe: str = "1m",  # Only 1-minute data
        limit: int = 500,
        hours_back: Optional[int] = None
    ) -> List[Dict]:
        """
        Get OHLCV candles for a pool. Only fetches 1-minute candles.
        
        Args:
            pool_address: Pool address on CoinGecko
            network: Network ID (default: "movement")
            timeframe: Always "1m" (1-minute candles only)
            limit: Maximum number of candles (default: 500, max: 1000)
            hours_back: Optional - only get candles from last N hours
        
        Returns:
            List of candle dictionaries with keys: timestamp, open, high, low, close, volume
        """
        # Force 1-minute timeframe (only 1-minute candles are supported)
        if timeframe != "1m":
            logger.debug(f"Timeframe '{timeframe}' requested but only 1-minute candles are supported, using 1m")
        timeframe = "1m"
        timeframe_type = "minute"
        aggregate = 1
        
        cache_key = f"{pool_address}_{network}_1m_{limit}"
        
        # Check cache
        if cache_key in self.cache:
            cached_time = self.cache[cache_key].get("timestamp", 0)
            if datetime.now().timestamp() - cached_time < self.cache_ttl:
                return self.cache[cache_key].get("candles", [])
        
        # Calculate limit based on hours_back
        if hours_back:
            if timeframe_type == "minute":
                calculated_limit = min(1000, hours_back * 60 // aggregate)
            elif timeframe_type == "hour":
                calculated_limit = min(1000, hours_back // aggregate)
            else:  # day
                calculated_limit = min(1000, hours_back // (aggregate * 24))
            limit = min(limit, calculated_limit) if limit else calculated_limit
        
        try:
            candles, _ = await get_pool_ohlcv(
                pool_address=pool_address,
                network=network,
                timeframe=timeframe_type,
                aggregate=aggregate,
                limit=limit,
                currency="usd",
                token="quote"
            )
            
            # Note: Storage is handled by the background scheduler
            # No need to store here - scheduler fetches and stores every minute
            
            # Cache the result
            self.cache[cache_key] = {
                "candles": candles,
                "timestamp": datetime.now().timestamp()
            }
            
            return candles
            
        except Exception as e:
            logger.error(f"Error fetching OHLCV candles: {e}", exc_info=True)
            return []
    
    async def get_price_summary(
        self,
        pool_address: str,
        timeframe: str = '1m',  # Only 1-minute data
        candles_count: int = 100,
        network: str = "movement"
    ) -> Optional[Dict]:
        """
        Get a summary of price trends from OHLCV data.
        Useful for LLM context.
        
        Returns:
            Dict with current_price, price_change_24h, high_24h, low_24h, trend, volatility
        """
        candles = await self.get_candles(
            pool_address=pool_address,
            network=network,
            timeframe=timeframe,
            limit=candles_count,
            hours_back=24
        )
        
        if not candles or len(candles) < 2:
            return None
        
        # Calculate summary statistics
        prices = [float(c.get('close', 0)) for c in candles]
        current_price = prices[-1] if prices else 0
        oldest_price = prices[0] if prices else current_price
        
        # Price change percentage
        price_change_24h = ((current_price - oldest_price) / oldest_price * 100) if oldest_price > 0 else 0
        
        # High and low
        high_24h = max(prices) if prices else current_price
        low_24h = min(prices) if prices else current_price
        
        # Trend (simple: compare first half vs second half average)
        mid_point = len(prices) // 2
        if mid_point > 0 and len(prices) > mid_point:
            first_half_avg = sum(prices[:mid_point]) / mid_point
            second_half_avg = sum(prices[mid_point:]) / (len(prices) - mid_point)
            
            if second_half_avg > first_half_avg * 1.01:  # 1% threshold
                trend = 'up'
            elif second_half_avg < first_half_avg * 0.99:
                trend = 'down'
            else:
                trend = 'sideways'
        else:
            trend = 'sideways'
        
        # Volatility (standard deviation)
        if prices:
            mean_price = sum(prices) / len(prices)
            variance = sum((p - mean_price) ** 2 for p in prices) / len(prices)
            volatility = variance ** 0.5
        else:
            volatility = 0
        
        return {
            'current_price': current_price,
            'price_change_24h': round(price_change_24h, 2),
            'high_24h': high_24h,
            'low_24h': low_24h,
            'trend': trend,
            'volatility': round(volatility, 4),
            'candles_count': len(candles)
        }
    
    async def format_for_llm(
        self,
        pool_address: str,
        network: str = "movement"
    ) -> str:
        """
        Format OHLCV data as a string for LLM prompt.
        
        Returns:
            Formatted string with price history and trends
        """
        if not pool_address:
            return "No pool address provided for OHLCV data."
        
        # Get price summary (using 1-minute data)
        summary = await self.get_price_summary(pool_address, timeframe='1m', candles_count=100, network=network)
        
        if not summary:
            return "Insufficient historical data (need at least 2 candles)."
        
        # Get recent candles for context (1-minute data)
        recent_candles = await self.get_candles(
            pool_address=pool_address,
            network=network,
            timeframe='1m',
            limit=20,
            hours_back=2
        )
        
        # Format as readable text
        lines = [
            f"Price History Summary (from CoinGecko pool):",
            f"- Current Price: ${summary['current_price']:.6f}",
            f"- 24h Change: {summary['price_change_24h']:+.2f}%",
            f"- 24h High: ${summary['high_24h']:.6f}",
            f"- 24h Low: ${summary['low_24h']:.6f}",
            f"- Trend: {summary['trend'].upper()}",
            f"- Volatility: {summary['volatility']:.6f}",
            f"- Data Points: {summary['candles_count']} candles",
        ]
        
        if recent_candles:
            lines.append("\nRecent Price Action (last 2 hours, 1-minute candles):")
            for candle in recent_candles[-10:]:  # Last 10 candles
                ts = candle.get('timestamp')
                if isinstance(ts, (int, float)):
                    ts = datetime.fromtimestamp(ts)
                elif isinstance(ts, str):
                    ts = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                else:
                    ts = datetime.now()
                
                time_str = ts.strftime('%H:%M')
                lines.append(
                    f"  {time_str}: O=${candle.get('open', 0):.6f} "
                    f"H=${candle.get('high', 0):.6f} "
                    f"L=${candle.get('low', 0):.6f} "
                    f"C=${candle.get('close', 0):.6f}"
                )
        
        return "\n".join(lines)
    
    async def _store_candles_to_db(
        self,
        pool_address: str,
        network: str,
        candles: List[Dict]
    ) -> None:
        """
        Store OHLCV candles to the database using the CoinGecko schema.
        
        Args:
            pool_address: CoinGecko pool address
            network: Network ID
            candles: List of candle dictionaries (1-minute candles)
        """
        if not db_connection.pool:
            logger.warning("Database connection not available, skipping OHLCV storage. Check DATABASE_URL configuration.")
            return
        
        try:
            # Get or create pool entry
            pool_id = await self._get_or_create_pool(
                pool_address=pool_address,
                network=network
            )
            
            if not pool_id:
                logger.warning(f"Could not get/create pool for {pool_address[:20]}...")
                return
            
            # Get pool_name from pools table (fetch once before loop)
            pool_name = None
            if db_connection.pool:
                try:
                    pool_query = "SELECT pool_name FROM pools WHERE id = %s"
                    pool_result = db_connection.execute_query(pool_query, (pool_id,), fetch_one=True)
                    if pool_result:
                        pool_name = pool_result.get('pool_name')
                except Exception as e:
                    logger.debug(f"Could not fetch pool_name for pool {pool_address[:20]}...: {e}")
            
            # Insert candles (using ON CONFLICT to avoid duplicates)
            stored_count = 0
            for candle in candles:
                timestamp = candle.get('timestamp')
                if not timestamp:
                    continue
                
                # Convert timestamp to datetime
                if isinstance(timestamp, (int, float)):
                    candle_dt = datetime.fromtimestamp(timestamp)
                elif isinstance(timestamp, str):
                    candle_dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                else:
                    continue
                
                # Insert candle with ON CONFLICT DO NOTHING to handle duplicates
                query = """
                    INSERT INTO ohlcv_candles (
                        pool_id, pool_name, timestamp,
                        open_price, high_price, low_price, close_price, volume
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (pool_id, timestamp) DO UPDATE SET pool_name = EXCLUDED.pool_name
                """
                
                params = (
                    str(pool_id),
                    pool_name,
                    candle_dt,
                    float(candle.get('open', 0)),
                    float(candle.get('high', 0)),
                    float(candle.get('low', 0)),
                    float(candle.get('close', 0)),
                    float(candle.get('volume', 0))
                )
                
                # Use fetch_all=False to get rowcount (1 if inserted, 0 if conflict)
                result = db_connection.execute_query(query, params, fetch_all=False)
                if result and result > 0:
                    stored_count += 1
            
            if stored_count > 0:
                logger.info(f"Stored {stored_count}/{len(candles)} OHLCV candles to database for pool {pool_address[:20]}...")
            else:
                logger.warning(f"No new candles stored (all {len(candles)} may be duplicates) for pool {pool_address[:20]}...")
                
        except Exception as e:
            logger.error(f"Error storing OHLCV candles to database: {e}", exc_info=True)
    
    async def _get_or_create_pool(
        self,
        pool_address: str,
        network: str
    ) -> Optional[str]:
        """
        Get or create a pool entry in the pools table.
        
        Args:
            pool_address: CoinGecko pool address
            network: Network ID
        
        Returns:
            Pool UUID as string, or None if error
        """
        if not db_connection.pool:
            return None
        
        try:
            # First, try to get existing pool
            query = """
                SELECT id FROM pools
                WHERE pool_address = %s AND network = %s
                LIMIT 1
            """
            result = db_connection.execute_query(query, (pool_address, network), fetch_one=True)
            
            if result and result.get('id'):
                return str(result['id'])
            
            # Create new pool entry
            insert_query = """
                INSERT INTO pools (
                    pool_address, network, is_active
                ) VALUES (
                    %s, %s, %s
                )
                ON CONFLICT (pool_address) 
                DO UPDATE SET is_active = TRUE, updated_at = NOW()
                RETURNING id
            """
            
            params = (
                pool_address,
                network,
                True  # is_active
            )
            
            result = db_connection.execute_query(insert_query, params, fetch_one=True)
            
            if result and result.get('id'):
                logger.info(f"Created pool entry for {pool_address[:20]}... on {network}")
                return str(result['id'])
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting/creating pool: {e}", exc_info=True)
            return None


# Global service instance
ohlcv_service = OHLCVService()

